package com.watchai.data

import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import mockwebserver3.SocketPolicy
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
        server.shutdown()
    }

    @Test
    fun `lists session summaries from the versioned endpoint`() = runBlocking {
        server.enqueue(
            MockResponse().setBody(
                """{"items":[{"id":"s1","status":"ready","received_count":4,"expected_count":4,"created_at":"2026-11-23T18:00:00Z"}],"next_cursor":null}""",
            ),
        )

        val result = api.listSessions(accessToken = "test-token")

        assertEquals("s1", result.single().id)
        val request = server.takeRequest()
        assertEquals("Bearer test-token", request.getHeader("Authorization"))
        assertEquals("/v1/sessions?limit=10", request.path)
    }

    @Test
    fun `maps unauthorized response without exposing response body`() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(401).setBody("sensitive detail"))

        val error = runCatching { api.listSessions(accessToken = "expired") }.exceptionOrNull()

        assertTrue(error is WatchApiFailure.Unauthorized)
        assertNull(error?.message?.takeIf { it.contains("sensitive detail") })
    }

    @Test
    fun `maps malformed response to a safe contract error`() = runBlocking {
        server.enqueue(MockResponse().setBody("not-json"))

        val error = runCatching { api.listSessions(accessToken = "test-token") }.exceptionOrNull()

        assertTrue(error is WatchApiFailure.MalformedResponse)
    }

    @Test
    fun `maps a timed out response to a recoverable timeout`() = runBlocking {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))

        val error = runCatching { api.listSessions(accessToken = "test-token") }.exceptionOrNull()

        assertTrue(error is WatchApiFailure.Timeout)
    }

    @Test
    fun `pairing exchanges the temporary code and posts no provider credential`() = runBlocking {
        server.enqueue(
            MockResponse().setResponseCode(201).setBody(
                """{"device_id":"00000000-0000-4000-8000-000000000001","access_token":"opaque-watch-token-12345678901234567890","token_type":"Bearer","scope":"sessions:read","expires_at":"2026-11-24T18:00:00Z"}""",
            ),
        )

        val paired = api.pair("12345678", "Galaxy Watch4")

        assertEquals("opaque-watch-token-12345678901234567890", paired.accessToken)
        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/v1/device-pairings", request.path)
        val requestBody = request.body.readUtf8()
        assertTrue(requestBody.contains("12345678"))
        assertTrue(!requestBody.contains("sk-or-"))
    }

    @Test
    fun `revocation sends bearer credential to the device revoke route`() = runBlocking {
        server.enqueue(MockResponse().setResponseCode(204))

        api.revokeDevice("opaque-watch-token")

        val request = server.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("/v1/devices/me", request.path)
        assertEquals("Bearer opaque-watch-token", request.getHeader("Authorization"))
    }

    @Test
    fun `session deletion sends bearer credential to the owner scoped route`() = runBlocking {
        val sessionId = "00000000-0000-4000-8000-000000000001"
        server.enqueue(MockResponse().setResponseCode(204))

        api.deleteSession("opaque-watch-token", sessionId)

        val request = server.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("/v1/sessions/$sessionId", request.path)
        assertEquals("Bearer opaque-watch-token", request.getHeader("Authorization"))
    }
}
