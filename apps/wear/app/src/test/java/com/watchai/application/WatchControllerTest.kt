package com.watchai.application

import com.watchai.data.OfflineSessionCache
import com.watchai.data.PairingCredential
import com.watchai.data.StudyJsonCodec
import com.watchai.data.WatchApi
import com.watchai.data.WatchApiFailure
import com.watchai.domain.QuestionCard
import com.watchai.domain.QuestionDetail
import com.watchai.domain.QuestionStatus
import com.watchai.domain.SessionStatus
import com.watchai.domain.SessionSummary
import com.watchai.domain.SolutionStep
import com.watchai.domain.StudySession
import com.watchai.security.CredentialStore
import com.watchai.security.DeviceCredential
import java.io.IOException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class WatchControllerTest {

    @Test
    fun `pair normalizes code saves credential and loads sessions`() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val prefs = InMemoryPreferences("https://watch.example.test")
        val creds = InMemoryCredentialStore()
        val cache = InMemoryCache()
        val api = FakeWatchApi(
            sessionsQueue = ArrayDeque(
                listOf(
                    listOf(SessionSummary(SESSION_ID, SessionStatus.READY, 1, 1, "2026-11-24T10:00:00Z")),
                ),
            ),
        )
        val controller = WatchController(
            preferences = prefs,
            credentialStore = creds,
            cache = cache,
            apiFactory = { api },
            mainDispatcher = dispatcher,
            ioDispatcher = dispatcher,
            pollIntervalsMillis = emptyList(),
            deviceNameProvider = { "Galaxy Watch4" },
        )

        controller.start()
        assertEquals(WatchDestination.PAIRING, controller.state.destination)

        controller.setPairingCode("a7k9-m2p4")
        controller.pair()
        advanceUntilIdle()

        assertEquals("A7K9M2P4", api.lastPairingCode)
        assertEquals(WatchDestination.SESSIONS, controller.state.destination)
        assertEquals(1, controller.state.sessions.size)
        assertEquals("device-1", creds.read()?.deviceId)
        controller.close()
    }

    @Test
    fun `active session polling updates state and stops once terminal`() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val prefs = InMemoryPreferences("https://watch.example.test")
        val creds = InMemoryCredentialStore(
            DeviceCredential("device-1", "a".repeat(40), Long.MAX_VALUE),
        )
        val cache = InMemoryCache()
        val api = FakeWatchApi(
            sessionsQueue = ArrayDeque(
                listOf(
                    listOf(SessionSummary(SESSION_ID, SessionStatus.PROCESSING, 1, 1, "2026-11-24T10:00:00Z")),
                    listOf(SessionSummary(SESSION_ID, SessionStatus.READY, 1, 1, "2026-11-24T10:00:00Z")),
                ),
            ),
        )
        val controller = WatchController(
            preferences = prefs,
            credentialStore = creds,
            cache = cache,
            apiFactory = { api },
            mainDispatcher = dispatcher,
            ioDispatcher = dispatcher,
            pollIntervalsMillis = listOf(100L, 200L),
            deviceNameProvider = { "Galaxy Watch4" },
        )

        controller.start()
        runCurrent()
        assertEquals(SessionStatus.PROCESSING, controller.state.sessions.single().status)
        assertEquals(1, api.listSessionsCalls)

        advanceTimeBy(150L)
        runCurrent()
        assertEquals(SessionStatus.READY, controller.state.sessions.single().status)
        assertEquals(2, api.listSessionsCalls)

        advanceTimeBy(1_000L)
        runCurrent()
        assertEquals(2, api.listSessionsCalls)
        controller.close()
    }

    @Test
    fun `reopening offline restores last question and step from cache`() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val prefs = InMemoryPreferences("https://watch.example.test").apply {
            setLastSessionId(SESSION_ID)
            setLastQuestionOrdinal(1)
            setLastStepIndex(1)
        }
        val creds = InMemoryCredentialStore(
            DeviceCredential("device-1", "a".repeat(40), Long.MAX_VALUE),
        )
        val detail = QuestionDetail(
            card = QuestionCard("q1", 1, QuestionStatus.READY, "Equação"),
            statement = "Resolva 2x + 4 = 10.",
            verified = true,
            verificationStatus = "verified",
            finalAnswer = "x = 3",
            units = null,
            steps = listOf(
                SolutionStep(1, "statement", "Enunciado", "Resolva 2x + 4 = 10.", verified = false),
                SolutionStep(2, "result", "Resultado", "x = 3", verified = true),
            ),
        )
        val cache = InMemoryCache().apply {
            writeQuestion(SESSION_ID, 1, StudyJsonCodec.encodeQuestion(detail))
        }
        val api = FakeWatchApi(failWith = WatchApiFailure.Network(IOException("offline")))
        val controller = WatchController(
            preferences = prefs,
            credentialStore = creds,
            cache = cache,
            apiFactory = { api },
            mainDispatcher = dispatcher,
            ioDispatcher = dispatcher,
            pollIntervalsMillis = emptyList(),
            deviceNameProvider = { "Galaxy Watch4" },
        )

        controller.start()
        advanceUntilIdle()

        assertEquals(WatchDestination.QUESTION, controller.state.destination)
        assertTrue(controller.state.offline)
        assertEquals(1, controller.state.stepIndex)
        assertEquals("x = 3", controller.state.activeQuestion?.finalAnswer)
        controller.close()
    }

    @Test
    fun `unauthorized error revokes local state and returns to pairing`() = runTest {
        val dispatcher = StandardTestDispatcher(testScheduler)
        val prefs = InMemoryPreferences("https://watch.example.test").apply {
            setLastSessionId(SESSION_ID)
        }
        val creds = InMemoryCredentialStore(
            DeviceCredential("device-1", "a".repeat(40), Long.MAX_VALUE),
        )
        val cache = InMemoryCache().apply {
            writeSessionList(StudyJsonCodec.encodeSessionList(emptyList()))
        }
        val api = FakeWatchApi(failWith = WatchApiFailure.Unauthorized())
        val controller = WatchController(
            preferences = prefs,
            credentialStore = creds,
            cache = cache,
            apiFactory = { api },
            mainDispatcher = dispatcher,
            ioDispatcher = dispatcher,
            pollIntervalsMillis = emptyList(),
            deviceNameProvider = { "Galaxy Watch4" },
        )

        controller.start()
        advanceUntilIdle()

        assertEquals(WatchDestination.PAIRING, controller.state.destination)
        assertNull(creds.read())
        assertNull(prefs.getLastSessionId())
        assertNull(cache.readSessionList())
        assertFalse(controller.state.errorMessage.isNullOrBlank())
        controller.close()
    }

    private companion object {
        const val SESSION_ID = "00000000-0000-4000-8000-000000000001"
    }
}

private class InMemoryPreferences(initialEndpoint: String) : WatchPreferencesStore {
    private var endpoint: String = initialEndpoint
    private var lastSessionId: String? = null
    private var lastQuestionOrdinal: Int? = null
    private var lastStepIndex: Int = 0

    override fun getEndpoint(): String = endpoint
    override fun setEndpoint(value: String) {
        endpoint = value.trim()
    }
    override fun getLastSessionId(): String? = lastSessionId
    override fun setLastSessionId(value: String?) {
        lastSessionId = value
    }
    override fun getLastQuestionOrdinal(): Int? = lastQuestionOrdinal
    override fun setLastQuestionOrdinal(value: Int?) {
        lastQuestionOrdinal = value
    }
    override fun getLastStepIndex(): Int = lastStepIndex
    override fun setLastStepIndex(value: Int) {
        lastStepIndex = value
    }
    override fun clearNavigation() {
        lastSessionId = null
        lastQuestionOrdinal = null
        lastStepIndex = 0
    }
}

private class InMemoryCredentialStore(
    private var current: DeviceCredential? = null,
) : CredentialStore {
    override fun save(credential: DeviceCredential) {
        current = credential
    }
    override fun read(nowEpochMillis: Long): DeviceCredential? = current
    override fun clear() {
        current = null
    }
}

private class InMemoryCache : OfflineSessionCache {
    private var listJson: String? = null
    private val sessions = mutableMapOf<String, String>()
    private val questions = mutableMapOf<Pair<String, Int>, String>()

    override fun readSessionList(): String? = listJson
    override fun writeSessionList(json: String) {
        listJson = json
    }
    override fun readSession(sessionId: String): String? = sessions[sessionId]
    override fun writeSession(sessionId: String, json: String) {
        sessions[sessionId] = json
    }
    override fun readQuestion(sessionId: String, ordinal: Int): String? = questions[sessionId to ordinal]
    override fun writeQuestion(sessionId: String, ordinal: Int, json: String) {
        questions[sessionId to ordinal] = json
    }
    override fun deleteSession(sessionId: String) {
        sessions.remove(sessionId)
        (1..4).forEach { questions.remove(sessionId to it) }
    }
    override fun clear() {
        listJson = null
        sessions.clear()
        questions.clear()
    }
}

private class FakeWatchApi(
    private val sessionsQueue: ArrayDeque<List<SessionSummary>> = ArrayDeque(),
    private val failWith: Exception? = null,
) : WatchApi {
    var lastPairingCode: String? = null
    var listSessionsCalls: Int = 0

    override suspend fun pair(pairingCode: String, deviceName: String): PairingCredential {
        lastPairingCode = pairingCode
        return PairingCredential("device-1", "a".repeat(40), "sessions:read", Long.MAX_VALUE)
    }

    override suspend fun listSessions(accessToken: String): List<SessionSummary> {
        listSessionsCalls += 1
        failWith?.let { throw it }
        return if (sessionsQueue.size > 1) sessionsQueue.removeFirst() else sessionsQueue.firstOrNull().orEmpty()
    }

    override suspend fun getSession(accessToken: String, sessionId: String): StudySession {
        failWith?.let { throw it }
        return StudySession(
            SessionSummary(sessionId, SessionStatus.READY, 1, 1, "2026-11-24T10:00:00Z"),
            listOf(QuestionCard("q1", 1, QuestionStatus.READY, "Equação", "x = 3")),
        )
    }

    override suspend fun getQuestion(accessToken: String, sessionId: String, ordinal: Int): QuestionDetail {
        failWith?.let { throw it }
        return QuestionDetail(
            QuestionCard("q1", ordinal, QuestionStatus.READY, "Equação"),
            "Resolva 2x + 4 = 10.",
            true,
            "verified",
            "x = 3",
            null,
            emptyList(),
        )
    }

    override suspend fun deleteSession(accessToken: String, sessionId: String) {}
    override suspend fun revokeDevice(accessToken: String) {}
}
