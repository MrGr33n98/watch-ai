package com.watchai.data

import com.watchai.domain.QuestionDetail
import com.watchai.domain.SessionSummary
import com.watchai.domain.StudySession
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URI
import java.net.URL
import java.time.Instant

class WatchApiClient internal constructor(
    baseUrl: String,
    private val allowHttpForTests: Boolean = false,
    private val connectTimeoutMillis: Int = DEFAULT_TIMEOUT_MILLIS,
    private val readTimeoutMillis: Int = DEFAULT_TIMEOUT_MILLIS,
) : WatchApi {
    private val base: URI = validateBaseUrl(baseUrl, allowHttpForTests)

    init {
        require(connectTimeoutMillis in 100..30_000)
        require(readTimeoutMillis in 100..30_000)
    }

    override suspend fun pair(pairingCode: String, deviceName: String): PairingCredential {
        require(pairingCode.length in 6..12)
        require(deviceName.isNotBlank() && deviceName.length <= 120)
        val body = JSONObject()
            .put("pairing_code", pairingCode)
            .put("device_name", deviceName.trim())
        val response = request("POST", "/v1/device-pairings", body = body.toString())
        return try {
            val json = JSONObject(response)
            PairingCredential(
                deviceId = json.requiredString("device_id"),
                accessToken = json.requiredString("access_token"),
                scope = json.requiredString("scope"),
                expiresAtEpochMillis = Instant.parse(json.requiredString("expires_at")).toEpochMilli(),
            )
        } catch (error: Exception) {
            if (error is WatchApiFailure) throw error
            throw WatchApiFailure.MalformedResponse()
        }
    }

    override suspend fun listSessions(accessToken: String): List<SessionSummary> {
        val response = request("GET", "/v1/sessions?limit=10", accessToken)
        return try {
            val items = JSONObject(response).getJSONArray("items")
            require(items.length() <= 20) { "Too many sessions in response" }
            (0 until items.length()).map { parseSessionSummary(items.getJSONObject(it)) }
        } catch (error: Exception) {
            if (error is WatchApiFailure) throw error
            throw WatchApiFailure.MalformedResponse()
        }
    }

    override suspend fun getSession(accessToken: String, sessionId: String): StudySession {
        requireUuid(sessionId)
        val response = request("GET", "/v1/sessions/$sessionId", accessToken)
        return parseSafely(response, ::parseStudySession)
    }

    override suspend fun getQuestion(accessToken: String, sessionId: String, ordinal: Int): QuestionDetail {
        requireUuid(sessionId)
        require(ordinal >= 1) { "Question ordinal must be positive" }
        val response = request("GET", "/v1/sessions/$sessionId/questions/$ordinal", accessToken)
        return parseSafely(response, ::parseQuestionDetail)
    }

    override suspend fun deleteSession(accessToken: String, sessionId: String) {
        requireUuid(sessionId)
        request("DELETE", "/v1/sessions/$sessionId", accessToken, allowEmpty = true)
    }

    override suspend fun revokeDevice(accessToken: String) {
        request("DELETE", "/v1/devices/me", accessToken, allowEmpty = true)
    }

    private suspend fun request(
        method: String,
        path: String,
        accessToken: String? = null,
        body: String? = null,
        allowEmpty: Boolean = false,
    ): String = withContext(Dispatchers.IO) {
        var connection: HttpURLConnection? = null
        try {
            val target = URL(base.toString().trimEnd('/') + path)
            connection = (target.openConnection() as HttpURLConnection).apply {
                requestMethod = method
                instanceFollowRedirects = false
                useCaches = false
                connectTimeout = connectTimeoutMillis
                readTimeout = readTimeoutMillis
                setRequestProperty("Accept", "application/json")
                accessToken?.let { setRequestProperty("Authorization", "Bearer $it") }
                if (body != null) {
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json; charset=utf-8")
                }
            }
            if (body != null) {
                connection.outputStream.use { output -> output.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val statusCode = connection.responseCode
            if (statusCode !in 200..299) throw mapHttpFailure(statusCode)
            if (allowEmpty && statusCode == HttpURLConnection.HTTP_NO_CONTENT) return@withContext ""
            val stream = connection.inputStream
            val payload = stream.use { readBounded(it) }.toString(Charsets.UTF_8)
            if (payload.isBlank() && !allowEmpty) throw WatchApiFailure.MalformedResponse()
            payload
        } catch (failure: WatchApiFailure) {
            throw failure
        } catch (_: SocketTimeoutException) {
            throw WatchApiFailure.Timeout()
        } catch (failure: IOException) {
            throw WatchApiFailure.Network(failure)
        } catch (_: Exception) {
            throw WatchApiFailure.Network(IOException("Request failed"))
        } finally {
            connection?.disconnect()
        }
    }

    private fun readBounded(input: InputStream): ByteArray {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        var total = 0
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            total += count
            if (total > MAX_RESPONSE_BYTES) throw WatchApiFailure.ResponseTooLarge()
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }

    private fun mapHttpFailure(statusCode: Int): WatchApiFailure = when (statusCode) {
        401 -> WatchApiFailure.Unauthorized()
        403 -> WatchApiFailure.Forbidden()
        404 -> WatchApiFailure.NotFound()
        429 -> WatchApiFailure.RateLimited()
        in 500..599 -> WatchApiFailure.Server()
        else -> WatchApiFailure.Http(statusCode)
    }

    private fun <T> parseSafely(body: String, parser: (JSONObject) -> T): T = try {
        parser(JSONObject(body))
    } catch (error: Exception) {
        if (error is WatchApiFailure) throw error
        throw WatchApiFailure.MalformedResponse()
    }

    private fun requireUuid(value: String) {
        val normalized = runCatching { java.util.UUID.fromString(value).toString() }
            .getOrElse { throw IllegalArgumentException("Session identifier must be a UUID", it) }
        require(value.equals(normalized, ignoreCase = true))
    }

    companion object {
        const val DEFAULT_TIMEOUT_MILLIS = 8_000
        const val MAX_RESPONSE_BYTES = 1024 * 1024

        private fun validateBaseUrl(value: String, allowHttpForTests: Boolean): URI {
            val uri = runCatching { URI(value) }.getOrElse { throw WatchApiFailure.InsecureEndpoint() }
            val acceptedScheme = uri.scheme.equals("https", ignoreCase = true) ||
                (allowHttpForTests && uri.scheme.equals("http", ignoreCase = true))
            if (!acceptedScheme || uri.host.isNullOrBlank() || uri.userInfo != null ||
                uri.query != null || uri.fragment != null
            ) {
                throw WatchApiFailure.InsecureEndpoint()
            }
            return uri
        }
    }
}
