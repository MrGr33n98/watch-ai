package com.watchai.data

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.watchai.domain.SessionStatus
import com.watchai.domain.SessionSummary
import java.util.UUID
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class OfflineSessionCacheTest {
    private val cache = AtomicSessionFileCache(ApplicationProvider.getApplicationContext<Context>())
    private val sessionId = UUID.randomUUID().toString()

    @Test
    fun `cached sessions and questions can be read without network`() {
        cache.writeSessionList("""{"items":[]}""")
        cache.writeSession(sessionId, """{"id":"$sessionId"}""")
        cache.writeQuestion(sessionId, 1, """{"ordinal":1,"steps":[]}""")

        assertEquals("""{"items":[]}""", cache.readSessionList())
        assertEquals("""{"id":"$sessionId"}""", cache.readSession(sessionId))
        assertEquals("""{"ordinal":1,"steps":[]}""", cache.readQuestion(sessionId, 1))
        assertNull(cache.readQuestion(sessionId, 2))
    }

    @Test
    fun `cache miss is explicit and session deletion purges its questions`() {
        val otherSessionId = UUID.randomUUID().toString()
        cache.writeSessionList(
            StudyJsonCodec.encodeSessionList(
                listOf(
                    SessionSummary(sessionId, SessionStatus.READY, 1, 4, "2026-11-24T10:00:00Z"),
                    SessionSummary(otherSessionId, SessionStatus.COLLECTING, 2, 4, "2026-11-24T11:00:00Z"),
                ),
            ),
        )
        assertNull(cache.readSession(UUID.randomUUID().toString()))
        cache.writeSession(sessionId, "{}")
        cache.writeQuestion(sessionId, 4, "{}")

        cache.deleteSession(sessionId)

        assertNull(cache.readSession(sessionId))
        assertNull(cache.readQuestion(sessionId, 4))
        assertEquals(
            listOf(otherSessionId),
            StudyJsonCodec.decodeSessionList(cache.readSessionList()!!).map { it.id },
        )
    }

    @Test
    fun `cache validates identifiers ordinals and payload size`() {
        assertThrows(IllegalArgumentException::class.java) { cache.writeSession("../escape", "{}") }
        assertThrows(IllegalArgumentException::class.java) { cache.writeQuestion(sessionId, 0, "{}") }
        cache.writeQuestion(sessionId, 5, "{}")
        assertEquals("{}", cache.readQuestion(sessionId, 5))
        assertThrows(IllegalArgumentException::class.java) {
            cache.writeSession(sessionId, "x".repeat(2 * 1024 * 1024 + 1))
        }
    }
}
