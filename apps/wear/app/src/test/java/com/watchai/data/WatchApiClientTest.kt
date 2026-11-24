package com.watchai.data

import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class WatchApiClientTest {
    private lateinit var server: MockWebServer
    private lateinit var api: WatchApiClient

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        api = WatchApiClient(
            server.url("/").toString(),
            allowHttpForTests = true,
            connectTimeoutMillis = 300,
            readTimeoutMillis = 300,
        )
    }

    @After
    fun tearDown() {
        server.close()
    }

    @Test
    fun `lists session summaries from the versioned endpoint`() = runBlocking {
        server.enqueue(
            response(
                body = """{"items":[{"id":"s1","status":"ready","received_count":4,"expected_count":4,"created_at":"2026-11-23T18:00:00Z"}],"next_cursor":null}""",
            ),
        )

        val result = api.listSessions(accessToken = "test-token")

        assertEquals("s1", result.single().id)
        val request = server.takeRequest()
        assertEquals("Bearer test-token", request.headers["Authorization"])
        assertEquals("/v1/sessions", request.url.encodedPath)
        assertEquals("limit=10", request.url.encodedQuery)
    }

    @Test
    fun `maps unauthorized response without exposing response body`() = runBlocking {
        server.enqueue(response(code = 401, body = "sensitive detail"))

        val error = runCatching { api.listSessions(accessToken = "expired") }.exceptionOrNull()

        assertTrue(error is WatchApiFailure.Unauthorized)
        assertNull(error?.message?.takeIf { it.contains("sensitive detail") })
    }

    @Test
    fun `maps malformed response to a safe contract error`() = runBlocking {
        server.enqueue(response(body = "not-json"))

        val error = runCatching { api.listSessions(accessToken = "test-token") }.exceptionOrNull()

        assertTrue(error is WatchApiFailure.MalformedResponse)
    }

    @Test
    fun `maps a timed out response to a recoverable timeout`() = runBlocking {
        server.enqueue(
            MockResponse.Builder()
                .body("delayed response")
                .bodyDelay(1, java.util.concurrent.TimeUnit.SECONDS)
                .build(),
        )

        val error = runCatching { api.listSessions(accessToken = "test-token") }.exceptionOrNull()

        assertTrue(error is WatchApiFailure.Timeout)
    }

    @Test
    fun `pairing exchanges the temporary code and posts no provider credential`() = runBlocking {
        server.enqueue(
            response(
                code = 201,
                body = """{"device_id":"00000000-0000-4000-8000-000000000001","access_token":"opaque-watch-token-12345678901234567890","token_type":"Bearer","scope":"sessions:read","expires_at":"2026-11-24T18:00:00Z"}""",
            ),
        )

        val paired = api.pair("12345678", "Galaxy Watch4")

        assertEquals("opaque-watch-token-12345678901234567890", paired.accessToken)
        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/v1/device-pairings", request.url.encodedPath)
        val requestBody = requireNotNull(request.body).utf8()
        assertTrue(requestBody.contains("12345678"))
        assertTrue(!requestBody.contains("sk-or-"))
    }

    @Test
    fun `revocation sends bearer credential to the device revoke route`() = runBlocking {
        server.enqueue(response(code = 204))

        api.revokeDevice("opaque-watch-token")

        val request = server.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("/v1/devices/me", request.url.encodedPath)
        assertEquals("Bearer opaque-watch-token", request.headers["Authorization"])
    }

    @Test
    fun `session deletion sends bearer credential to the owner scoped route`() = runBlocking {
        val sessionId = "00000000-0000-4000-8000-000000000001"
        server.enqueue(response(code = 204))

        api.deleteSession("opaque-watch-token", sessionId)

        val request = server.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("/v1/sessions/$sessionId", request.url.encodedPath)
        assertEquals("Bearer opaque-watch-token", request.headers["Authorization"])
    }

    private fun response(code: Int = 200, body: String = "") =
        MockResponse(code = code, body = body)
}
