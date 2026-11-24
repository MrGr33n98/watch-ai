package com.watchai.application

import android.content.Context
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.watchai.data.AtomicSessionFileCache
import com.watchai.data.OfflineSessionCache
import com.watchai.data.StudyJsonCodec
import com.watchai.data.WatchApi
import com.watchai.data.WatchApiClient
import com.watchai.data.WatchApiFailure
import com.watchai.domain.QuestionDetail
import com.watchai.domain.SessionSummary
import com.watchai.domain.StudySession
import com.watchai.security.AndroidKeystoreCredentialStore
import com.watchai.security.CredentialStore
import com.watchai.security.DeviceCredential
import com.watchai.ui.screens.PairingScreen
import com.watchai.ui.screens.QuestionListScreen
import com.watchai.ui.screens.QuestionStepsScreen
import com.watchai.ui.screens.SessionListScreen
import com.watchai.ui.screens.WatchAiWearRoot
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class WatchDestination { PAIRING, SESSIONS, QUESTIONS, QUESTION }

data class WatchUiState(
    val destination: WatchDestination = WatchDestination.PAIRING,
    val endpoint: String = "",
    val pairingCode: String = "",
    val sessions: List<SessionSummary> = emptyList(),
    val activeSession: StudySession? = null,
    val activeQuestion: QuestionDetail? = null,
    val stepIndex: Int = 0,
    val loading: Boolean = false,
    val offline: Boolean = false,
    val errorMessage: String? = null,
)

class WatchController internal constructor(
    context: Context,
    private val credentialStore: CredentialStore = AndroidKeystoreCredentialStore(context),
    private val cache: OfflineSessionCache = AtomicSessionFileCache(context),
    private val apiFactory: (String) -> WatchApi = { endpoint -> WatchApiClient(endpoint) },
) {
    private val preferences = context.applicationContext.getSharedPreferences(ENDPOINT_PREFS, Context.MODE_PRIVATE)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    var state by mutableStateOf(WatchUiState(endpoint = preferences.getString(KEY_ENDPOINT, "") ?: ""))
        private set

    fun start() {
        if (credentialStore.read() == null) {
            state = state.copy(destination = WatchDestination.PAIRING)
        } else {
            state = state.copy(destination = WatchDestination.SESSIONS)
            loadSessions()
        }
    }

    fun setEndpoint(value: String) {
        state = state.copy(endpoint = value, errorMessage = null)
        preferences.edit().putString(KEY_ENDPOINT, value.trim()).apply()
    }

    fun setPairingCode(value: String) {
        state = state.copy(
            pairingCode = value.filter { it.isLetterOrDigit() || it == '-' || it == '_' }.take(12),
            errorMessage = null,
        )
    }

    fun showPairing() {
        state = state.copy(destination = WatchDestination.PAIRING, errorMessage = null)
    }

    fun pair() {
        val endpoint = state.endpoint.trim()
        val code = state.pairingCode.trim()
        if (!endpoint.startsWith("https://", ignoreCase = true) || code.length !in 6..12) {
            state = state.copy(errorMessage = "Informe um endereço HTTPS e um código válido.")
            return
        }
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                val oldCredential = credentialStore.read()
                val api = apiFactory(endpoint)
                val paired = api.pair(code, "${Build.MANUFACTURER} ${Build.MODEL}".take(120))
                require(paired.scope == READ_SCOPE && paired.accessToken.length >= MIN_TOKEN_LENGTH) {
                    "Resposta de pareamento inválida"
                }
                if (oldCredential != null && oldCredential.deviceId != paired.deviceId) {
                    withContext(Dispatchers.IO) { cache.clear() }
                }
                credentialStore.save(
                    DeviceCredential(
                        deviceId = paired.deviceId,
                        accessToken = paired.accessToken,
                        expiresAtEpochMillis = paired.expiresAtEpochMillis,
                    ),
                )
                state = state.copy(pairingCode = "", loading = false, destination = WatchDestination.SESSIONS)
                loadSessions()
            } catch (failure: Exception) {
                state = state.copy(loading = false, errorMessage = safeMessage(failure))
            }
        }
    }

    fun loadSessions() {
        val credential = credentialStore.read()
        if (credential == null) {
            state = state.copy(destination = WatchDestination.PAIRING, loading = false)
            return
        }
        state = state.copy(loading = true, offline = false, errorMessage = null)
        scope.launch {
            try {
                val result = apiFactory(state.endpoint.trim()).listSessions(credential.accessToken)
                withContext(Dispatchers.IO) { runCatching { cache.writeSessionList(StudyJsonCodec.encodeSessionList(result)) } }
                state = state.copy(
                    destination = WatchDestination.SESSIONS,
                    sessions = result,
                    loading = false,
                    offline = false,
                    errorMessage = null,
                )
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    invalidateDevice()
                    state = state.copy(
                        destination = WatchDestination.PAIRING,
                        sessions = emptyList(),
                        activeSession = null,
                        activeQuestion = null,
                        loading = false,
                        errorMessage = "Pareamento expirado. Vincule o relógio novamente.",
                    )
                    return@launch
                }
                val cached = if (failure.isConnectivityFailure()) {
                    withContext(Dispatchers.IO) {
                        runCatching { cache.readSessionList()?.let(StudyJsonCodec::decodeSessionList) }.getOrNull()
                    }
                } else null
                state = if (cached != null) {
                    state.copy(
                        destination = WatchDestination.SESSIONS,
                        sessions = cached,
                        loading = false,
                        offline = true,
                        errorMessage = null,
                    )
                } else {
                    state.copy(loading = false, offline = false, errorMessage = safeMessage(failure))
                }
            }
        }
    }

    fun openSession(sessionId: String) {
        val credential = credentialStore.read() ?: return requirePairing()
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                val session = apiFactory(state.endpoint.trim()).getSession(credential.accessToken, sessionId)
                withContext(Dispatchers.IO) { runCatching { cache.writeSession(sessionId, StudyJsonCodec.encodeSession(session)) } }
                state = state.copy(
                    destination = WatchDestination.QUESTIONS,
                    activeSession = session,
                    activeQuestion = null,
                    stepIndex = 0,
                    loading = false,
                    offline = false,
                    errorMessage = null,
                )
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    handleUnauthorized()
                    return@launch
                }
                val cached = if (failure.isConnectivityFailure()) {
                    withContext(Dispatchers.IO) {
                        runCatching { cache.readSession(sessionId)?.let(StudyJsonCodec::decodeSession) }.getOrNull()
                    }
                } else null
                if (cached != null) {
                    state = state.copy(
                        destination = WatchDestination.QUESTIONS,
                        activeSession = cached,
                        activeQuestion = null,
                        stepIndex = 0,
                        loading = false,
                        offline = true,
                        errorMessage = null,
                    )
                } else {
                    state = state.copy(loading = false, errorMessage = safeMessage(failure))
                }
            }
        }
    }

    fun openQuestion(sessionId: String, ordinal: Int) {
        val credential = credentialStore.read() ?: return requirePairing()
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                val detail = apiFactory(state.endpoint.trim()).getQuestion(credential.accessToken, sessionId, ordinal)
                withContext(Dispatchers.IO) {
                    runCatching { cache.writeQuestion(sessionId, ordinal, StudyJsonCodec.encodeQuestion(detail)) }
                }
                state = state.copy(
                    destination = WatchDestination.QUESTION,
                    activeQuestion = detail,
                    stepIndex = 0,
                    loading = false,
                    offline = false,
                    errorMessage = null,
                )
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    handleUnauthorized()
                    return@launch
                }
                val cached = if (failure.isConnectivityFailure()) {
                    withContext(Dispatchers.IO) {
                        runCatching {
                            cache.readQuestion(sessionId, ordinal)?.let(StudyJsonCodec::decodeQuestion)
                        }.getOrNull()
                    }
                } else null
                if (cached != null) {
                    state = state.copy(
                        destination = WatchDestination.QUESTION,
                        activeQuestion = cached,
                        stepIndex = 0,
                        loading = false,
                        offline = true,
                        errorMessage = null,
                    )
                } else {
                    state = state.copy(loading = false, errorMessage = safeMessage(failure))
                }
            }
        }
    }

    fun previousStep() {
        state = state.copy(stepIndex = (state.stepIndex - 1).coerceAtLeast(0))
    }

    fun nextStep() {
        val lastIndex = (state.activeQuestion?.steps?.lastIndex ?: 0).coerceAtLeast(0)
        state = state.copy(stepIndex = (state.stepIndex + 1).coerceAtMost(lastIndex))
    }

    fun backToQuestions() {
        state = state.copy(destination = WatchDestination.QUESTIONS, activeQuestion = null, stepIndex = 0)
    }

    fun backToSessions() {
        state = state.copy(destination = WatchDestination.SESSIONS, activeQuestion = null, activeSession = null)
    }

    fun deleteSession(sessionId: String) {
        val credential = credentialStore.read() ?: return requirePairing()
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                apiFactory(state.endpoint.trim()).deleteSession(credential.accessToken, sessionId)
                val remainingSessions = state.sessions.filterNot { it.id == sessionId }
                withContext(Dispatchers.IO) {
                    runCatching {
                        cache.deleteSession(sessionId)
                        cache.writeSessionList(StudyJsonCodec.encodeSessionList(remainingSessions))
                    }.onFailure { cache.clear() }
                }
                val activeSession = state.activeSession?.takeUnless { it.summary.id == sessionId }
                state = state.copy(
                    destination = WatchDestination.SESSIONS,
                    sessions = remainingSessions,
                    activeSession = activeSession,
                    activeQuestion = null,
                    loading = false,
                    offline = false,
                    errorMessage = null,
                )
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    handleUnauthorized()
                } else {
                    state = state.copy(loading = false, errorMessage = safeMessage(failure))
                }
            }
        }
    }

    fun revokeDevice() {
        val credential = credentialStore.read() ?: return requirePairing()
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                apiFactory(state.endpoint.trim()).revokeDevice(credential.accessToken)
                credentialStore.clear()
                withContext(Dispatchers.IO) { cache.clear() }
                state = WatchUiState(
                    destination = WatchDestination.PAIRING,
                    endpoint = state.endpoint,
                    errorMessage = "Relógio desvinculado.",
                )
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    handleUnauthorized()
                } else {
                    state = state.copy(loading = false, errorMessage = safeMessage(failure))
                }
            }
        }
    }

    fun close() = scope.cancel()

    private suspend fun handleUnauthorized() {
        invalidateDevice()
        state = state.copy(
            destination = WatchDestination.PAIRING,
            sessions = emptyList(),
            activeSession = null,
            activeQuestion = null,
            loading = false,
            offline = false,
            errorMessage = "Pareamento revogado ou expirado. Vincule o relógio novamente.",
        )
    }

    private suspend fun invalidateDevice() {
        credentialStore.clear()
        withContext(Dispatchers.IO) { cache.clear() }
    }

    private fun requirePairing() {
        state = state.copy(destination = WatchDestination.PAIRING, errorMessage = "Vincule o relógio para continuar.")
    }

    private fun isAuthorizationFailure(error: Exception): Boolean =
        error is WatchApiFailure.Unauthorized || error is WatchApiFailure.Forbidden

    private fun Exception.isConnectivityFailure(): Boolean =
        this is WatchApiFailure.Network || this is WatchApiFailure.Timeout

    private fun safeMessage(error: Exception): String =
        (error as? WatchApiFailure)?.message ?: "Não foi possível concluir. Verifique os dados e tente novamente."

    private companion object {
        const val ENDPOINT_PREFS = "watch_ai_endpoint"
        const val KEY_ENDPOINT = "base_url"
        const val READ_SCOPE = "sessions:read"
        const val MIN_TOKEN_LENGTH = 32
    }
}

@androidx.compose.runtime.Composable
fun WatchAiApp(controller: WatchController) {
    val current = controller.state
    WatchAiWearRoot {
        when (current.destination) {
            WatchDestination.PAIRING -> PairingScreen(
                endpoint = current.endpoint,
                pairingCode = current.pairingCode,
                busy = current.loading,
                errorMessage = current.errorMessage,
                onEndpointChange = controller::setEndpoint,
                onPairingCodeChange = controller::setPairingCode,
                onPair = controller::pair,
            )
            WatchDestination.SESSIONS -> SessionListScreen(
                sessions = current.sessions,
                loading = current.loading,
                offline = current.offline,
                errorMessage = current.errorMessage,
                onOpenSession = controller::openSession,
                onDeleteSession = controller::deleteSession,
                onPairDevice = controller::showPairing,
                onRetry = controller::loadSessions,
                onRevokeDevice = controller::revokeDevice,
            )
            WatchDestination.QUESTIONS -> current.activeSession?.let { session ->
                QuestionListScreen(
                    session = session,
                    offline = current.offline,
                    onOpenQuestion = { ordinal -> controller.openQuestion(session.summary.id, ordinal) },
                    onBack = controller::backToSessions,
                    loading = current.loading,
                    errorMessage = current.errorMessage,
                )
            }
            WatchDestination.QUESTION -> current.activeQuestion?.let { detail ->
                QuestionStepsScreen(
                    detail = detail,
                    stepIndex = current.stepIndex,
                    offline = current.offline,
                    onPrevious = controller::previousStep,
                    onNext = controller::nextStep,
                    onBack = controller::backToQuestions,
                )
            }
        }
    }
}
