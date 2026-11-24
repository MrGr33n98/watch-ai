package com.watchai.application

import android.content.Context
import android.os.Build
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.watchai.BuildConfig
import com.watchai.data.AtomicSessionFileCache
import com.watchai.data.OfflineSessionCache
import com.watchai.data.StudyJsonCodec
import com.watchai.data.WatchApi
import com.watchai.data.WatchApiClient
import com.watchai.data.WatchApiFailure
import com.watchai.domain.QuestionDetail
import com.watchai.domain.QuestionStatus
import com.watchai.domain.SessionStatus
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
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
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

interface WatchPreferencesStore {
    fun getEndpoint(): String
    fun setEndpoint(value: String)
    fun getLastSessionId(): String?
    fun setLastSessionId(value: String?)
    fun getLastQuestionOrdinal(): Int?
    fun setLastQuestionOrdinal(value: Int?)
    fun getLastStepIndex(): Int
    fun setLastStepIndex(value: Int)
    fun clearNavigation()
}

internal class SharedPreferencesWatchStore(context: Context) : WatchPreferencesStore {
    private val preferences =
        context.applicationContext.getSharedPreferences(ENDPOINT_PREFS, Context.MODE_PRIVATE)

    override fun getEndpoint(): String =
        preferences.getString(KEY_ENDPOINT, BuildConfig.DEFAULT_API_BASE_URL) ?: ""

    override fun setEndpoint(value: String) {
        preferences.edit().putString(KEY_ENDPOINT, value.trim()).apply()
    }

    override fun getLastSessionId(): String? = preferences.getString(KEY_LAST_SESSION_ID, null)

    override fun setLastSessionId(value: String?) {
        preferences.edit().putString(KEY_LAST_SESSION_ID, value).apply()
    }

    override fun getLastQuestionOrdinal(): Int? {
        val stored = preferences.getInt(KEY_LAST_QUESTION_ORDINAL, 0)
        return stored.takeIf { it in 1..4 }
    }

    override fun setLastQuestionOrdinal(value: Int?) {
        val editor = preferences.edit()
        if (value == null) editor.remove(KEY_LAST_QUESTION_ORDINAL) else editor.putInt(KEY_LAST_QUESTION_ORDINAL, value)
        editor.apply()
    }

    override fun getLastStepIndex(): Int = preferences.getInt(KEY_LAST_STEP_INDEX, 0).coerceAtLeast(0)

    override fun setLastStepIndex(value: Int) {
        preferences.edit().putInt(KEY_LAST_STEP_INDEX, value.coerceAtLeast(0)).apply()
    }

    override fun clearNavigation() {
        preferences.edit()
            .remove(KEY_LAST_SESSION_ID)
            .remove(KEY_LAST_QUESTION_ORDINAL)
            .remove(KEY_LAST_STEP_INDEX)
            .apply()
    }

    private companion object {
        const val ENDPOINT_PREFS = "watch_ai_endpoint"
        const val KEY_ENDPOINT = "base_url"
        const val KEY_LAST_SESSION_ID = "last_session_id"
        const val KEY_LAST_QUESTION_ORDINAL = "last_question_ordinal"
        const val KEY_LAST_STEP_INDEX = "last_step_index"
    }
}

class WatchController {
    constructor(context: Context) : this(
        preferences = SharedPreferencesWatchStore(context),
        credentialStore = AndroidKeystoreCredentialStore(context),
        cache = AtomicSessionFileCache(context),
    )

    internal constructor(
        preferences: WatchPreferencesStore,
        credentialStore: CredentialStore,
        cache: OfflineSessionCache,
        apiFactory: (String) -> WatchApi = { endpoint -> WatchApiClient(endpoint) },
        mainDispatcher: CoroutineDispatcher = Dispatchers.Main.immediate,
        ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
        pollIntervalsMillis: List<Long> = listOf(15_000L, 30_000L, 60_000L),
        deviceNameProvider: () -> String = {
            val manufacturer = Build.MANUFACTURER ?: "Wear"
            val model = Build.MODEL ?: "Watch"
            "$manufacturer $model".trim()
        },
    ) {
        this.preferences = preferences
        this.credentialStore = credentialStore
        this.cache = cache
        this.apiFactory = apiFactory
        this.ioDispatcher = ioDispatcher
        this.pollIntervalsMillis = pollIntervalsMillis
        this.deviceNameProvider = deviceNameProvider
        this.scope = CoroutineScope(SupervisorJob() + mainDispatcher)
        this.state = WatchUiState(endpoint = preferences.getEndpoint())
    }

    private val preferences: WatchPreferencesStore
    private val credentialStore: CredentialStore
    private val cache: OfflineSessionCache
    private val apiFactory: (String) -> WatchApi
    private val ioDispatcher: CoroutineDispatcher
    private val pollIntervalsMillis: List<Long>
    private val deviceNameProvider: () -> String
    private val scope: CoroutineScope
    private var pollingJob: Job? = null
    private var foregroundActive: Boolean = true

    var state by mutableStateOf(WatchUiState())
        private set

    fun start() {
        if (credentialStore.read() == null) {
            state = state.copy(destination = WatchDestination.PAIRING)
            return
        }
        val restoredSessionId = preferences.getLastSessionId()
        val restoredOrdinal = preferences.getLastQuestionOrdinal()
        val restoredStep = preferences.getLastStepIndex()
        if (restoredSessionId != null && restoredOrdinal != null) {
            openQuestion(restoredSessionId, restoredOrdinal, initialStepIndex = restoredStep)
        } else if (restoredSessionId != null) {
            openSession(restoredSessionId)
        } else {
            state = state.copy(destination = WatchDestination.SESSIONS)
            loadSessions()
        }
    }

    fun setForegroundActive(active: Boolean) {
        foregroundActive = active
        if (!active) {
            cancelPolling()
        } else {
            schedulePollingIfNeeded()
        }
    }

    fun setEndpoint(value: String) {
        state = state.copy(endpoint = value, errorMessage = null)
        preferences.setEndpoint(value)
    }

    fun setPairingCode(value: String) {
        state = state.copy(
            pairingCode = normalizeCodeInput(value),
            errorMessage = null,
        )
    }

    fun showPairing() {
        cancelPolling()
        state = state.copy(destination = WatchDestination.PAIRING, errorMessage = null)
    }

    fun pair() {
        val endpoint = state.endpoint.trim()
        val code = normalizeCodeInput(state.pairingCode)
        val compactCode = code.replace("-", "")
        if (!endpoint.startsWith("https://", ignoreCase = true) || compactCode.length !in 6..12) {
            state = state.copy(errorMessage = "Informe um endereço HTTPS e um código válido.")
            return
        }
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                val oldCredential = credentialStore.read()
                val api = apiFactory(endpoint)
                val paired = api.pair(compactCode, deviceNameProvider().take(120))
                require(paired.scope == READ_SCOPE && paired.accessToken.length >= MIN_TOKEN_LENGTH) {
                    "Resposta de pareamento inválida"
                }
                if (oldCredential != null && oldCredential.deviceId != paired.deviceId) {
                    withContext(ioDispatcher) { cache.clear() }
                    preferences.clearNavigation()
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

    fun loadSessions(silent: Boolean = false) {
        val credential = credentialStore.read()
        if (credential == null) {
            cancelPolling()
            state = state.copy(destination = WatchDestination.PAIRING, loading = false)
            return
        }
        if (!silent) {
            state = state.copy(loading = true, offline = false, errorMessage = null)
        }
        scope.launch {
            try {
                val result = apiFactory(state.endpoint.trim()).listSessions(credential.accessToken)
                withContext(ioDispatcher) { runCatching { cache.writeSessionList(StudyJsonCodec.encodeSessionList(result)) } }
                state = state.copy(
                    destination = WatchDestination.SESSIONS,
                    sessions = result,
                    loading = false,
                    offline = false,
                    errorMessage = null,
                )
                schedulePollingIfNeeded()
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    handleUnauthorized()
                    return@launch
                }
                val cached = if (failure.isConnectivityFailure()) {
                    withContext(ioDispatcher) {
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
                cancelPolling()
            }
        }
    }

    fun openSession(sessionId: String, silent: Boolean = false) {
        val credential = credentialStore.read() ?: return requirePairing()
        preferences.setLastSessionId(sessionId)
        preferences.setLastQuestionOrdinal(null)
        preferences.setLastStepIndex(0)
        if (!silent) {
            state = state.copy(loading = true, errorMessage = null)
        }
        scope.launch {
            try {
                val session = apiFactory(state.endpoint.trim()).getSession(credential.accessToken, sessionId)
                withContext(ioDispatcher) { runCatching { cache.writeSession(sessionId, StudyJsonCodec.encodeSession(session)) } }
                state = state.copy(
                    destination = WatchDestination.QUESTIONS,
                    activeSession = session,
                    activeQuestion = null,
                    stepIndex = 0,
                    loading = false,
                    offline = false,
                    errorMessage = null,
                )
                schedulePollingIfNeeded()
            } catch (failure: Exception) {
                if (isAuthorizationFailure(failure)) {
                    handleUnauthorized()
                    return@launch
                }
                val cached = if (failure.isConnectivityFailure()) {
                    withContext(ioDispatcher) {
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
                cancelPolling()
            }
        }
    }

    fun openQuestion(sessionId: String, ordinal: Int, initialStepIndex: Int = 0) {
        val credential = credentialStore.read() ?: return requirePairing()
        cancelPolling()
        preferences.setLastSessionId(sessionId)
        preferences.setLastQuestionOrdinal(ordinal)
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                val detail = apiFactory(state.endpoint.trim()).getQuestion(credential.accessToken, sessionId, ordinal)
                withContext(ioDispatcher) {
                    runCatching { cache.writeQuestion(sessionId, ordinal, StudyJsonCodec.encodeQuestion(detail)) }
                }
                val boundedStep = initialStepIndex.coerceIn(0, (detail.steps.size - 1).coerceAtLeast(0))
                preferences.setLastStepIndex(boundedStep)
                state = state.copy(
                    destination = WatchDestination.QUESTION,
                    activeQuestion = detail,
                    stepIndex = boundedStep,
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
                    withContext(ioDispatcher) {
                        runCatching {
                            cache.readQuestion(sessionId, ordinal)?.let(StudyJsonCodec::decodeQuestion)
                        }.getOrNull()
                    }
                } else null
                if (cached != null) {
                    val boundedStep = initialStepIndex.coerceIn(0, (cached.steps.size - 1).coerceAtLeast(0))
                    preferences.setLastStepIndex(boundedStep)
                    state = state.copy(
                        destination = WatchDestination.QUESTION,
                        activeQuestion = cached,
                        stepIndex = boundedStep,
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
        val next = (state.stepIndex - 1).coerceAtLeast(0)
        preferences.setLastStepIndex(next)
        state = state.copy(stepIndex = next)
    }

    fun nextStep() {
        val lastIndex = (state.activeQuestion?.steps?.lastIndex ?: 0).coerceAtLeast(0)
        val next = (state.stepIndex + 1).coerceAtMost(lastIndex)
        preferences.setLastStepIndex(next)
        state = state.copy(stepIndex = next)
    }

    fun backToQuestions() {
        val sessionId = state.activeSession?.summary?.id ?: preferences.getLastSessionId()
        preferences.setLastQuestionOrdinal(null)
        preferences.setLastStepIndex(0)
        if (state.activeSession == null && sessionId != null) {
            openSession(sessionId)
            return
        }
        state = state.copy(destination = WatchDestination.QUESTIONS, activeQuestion = null, stepIndex = 0)
        schedulePollingIfNeeded()
    }

    fun backToSessions() {
        preferences.clearNavigation()
        state = state.copy(destination = WatchDestination.SESSIONS, activeQuestion = null, activeSession = null)
        if (state.sessions.isEmpty()) {
            loadSessions()
        } else {
            schedulePollingIfNeeded()
        }
    }

    fun deleteSession(sessionId: String) {
        val credential = credentialStore.read() ?: return requirePairing()
        cancelPolling()
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                apiFactory(state.endpoint.trim()).deleteSession(credential.accessToken, sessionId)
                val remainingSessions = state.sessions.filterNot { it.id == sessionId }
                withContext(ioDispatcher) {
                    runCatching {
                        cache.deleteSession(sessionId)
                        cache.writeSessionList(StudyJsonCodec.encodeSessionList(remainingSessions))
                    }.onFailure { cache.clear() }
                }
                if (preferences.getLastSessionId() == sessionId) {
                    preferences.clearNavigation()
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
                schedulePollingIfNeeded()
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
        cancelPolling()
        state = state.copy(loading = true, errorMessage = null)
        scope.launch {
            try {
                apiFactory(state.endpoint.trim()).revokeDevice(credential.accessToken)
                invalidateDevice()
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

    fun close() {
        cancelPolling()
        scope.cancel()
    }

    private fun schedulePollingIfNeeded() {
        if (!foregroundActive || state.offline || pollIntervalsMillis.isEmpty()) {
            cancelPolling()
            return
        }
        val shouldPoll = when (state.destination) {
            WatchDestination.SESSIONS -> state.sessions.any { it.status.isInProgress() }
            WatchDestination.QUESTIONS -> state.activeSession?.let { session ->
                session.summary.status.isInProgress() || session.questions.any { it.status.isInProgress() }
            } == true
            WatchDestination.PAIRING, WatchDestination.QUESTION -> false
        }
        if (!shouldPoll) {
            cancelPolling()
            return
        }
        if (pollingJob?.isActive == true) return
        pollingJob = scope.launch {
            var attempt = 0
            while (foregroundActive && !state.offline) {
                val delayMs = pollIntervalsMillis[attempt.coerceAtMost(pollIntervalsMillis.lastIndex)]
                delay(delayMs)
                if (!foregroundActive || state.offline) break
                attempt += 1
                when (state.destination) {
                    WatchDestination.SESSIONS -> refreshSessionsDuringPoll()
                    WatchDestination.QUESTIONS -> state.activeSession?.summary?.id?.let { refreshSessionDuringPoll(it) }
                    else -> break
                }
            }
        }
    }

    private suspend fun refreshSessionsDuringPoll() {
        val credential = credentialStore.read() ?: return
        runCatching {
            val result = apiFactory(state.endpoint.trim()).listSessions(credential.accessToken)
            withContext(ioDispatcher) { runCatching { cache.writeSessionList(StudyJsonCodec.encodeSessionList(result)) } }
            state = state.copy(sessions = result, offline = false, errorMessage = null)
            if (result.none { it.status.isInProgress() }) cancelPolling()
        }.onFailure { failure ->
            if (failure is Exception && isAuthorizationFailure(failure)) handleUnauthorized()
        }
    }

    private suspend fun refreshSessionDuringPoll(sessionId: String) {
        val credential = credentialStore.read() ?: return
        runCatching {
            val session = apiFactory(state.endpoint.trim()).getSession(credential.accessToken, sessionId)
            withContext(ioDispatcher) { runCatching { cache.writeSession(sessionId, StudyJsonCodec.encodeSession(session)) } }
            state = state.copy(activeSession = session, offline = false, errorMessage = null)
            val stillRunning = session.summary.status.isInProgress() ||
                session.questions.any { it.status.isInProgress() }
            if (!stillRunning) cancelPolling()
        }.onFailure { failure ->
            if (failure is Exception && isAuthorizationFailure(failure)) handleUnauthorized()
        }
    }

    private fun cancelPolling() {
        pollingJob?.cancel()
        pollingJob = null
    }

    private suspend fun handleUnauthorized() {
        cancelPolling()
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
        preferences.clearNavigation()
        withContext(ioDispatcher) { cache.clear() }
    }

    private fun requirePairing() {
        cancelPolling()
        state = state.copy(destination = WatchDestination.PAIRING, errorMessage = "Vincule o relógio para continuar.")
    }

    private fun SessionStatus.isInProgress(): Boolean =
        this == SessionStatus.CREATED ||
            this == SessionStatus.COLLECTING ||
            this == SessionStatus.QUEUED ||
            this == SessionStatus.PROCESSING

    private fun QuestionStatus.isInProgress(): Boolean =
        this == QuestionStatus.UPLOADED ||
            this == QuestionStatus.VALIDATING ||
            this == QuestionStatus.INTERPRETING ||
            this == QuestionStatus.SOLVING

    private fun normalizeCodeInput(value: String): String =
        value.filter { it.isLetterOrDigit() || it == '-' || it == '_' }.uppercase().take(12)

    private fun isAuthorizationFailure(error: Exception): Boolean =
        error is WatchApiFailure.Unauthorized || error is WatchApiFailure.Forbidden

    private fun Exception.isConnectivityFailure(): Boolean =
        this is WatchApiFailure.Network || this is WatchApiFailure.Timeout

    private fun safeMessage(error: Exception): String =
        (error as? WatchApiFailure)?.message ?: "Não foi possível concluir. Verifique os dados e tente novamente."

    private companion object {
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
                onRetry = { controller.loadSessions() },
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
                    onRetry = { controller.openSession(session.summary.id) },
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
