package com.watchai.data

import com.watchai.domain.QuestionCard
import com.watchai.domain.QuestionDetail
import com.watchai.domain.QuestionStatus
import com.watchai.domain.SessionStatus
import com.watchai.domain.SessionSummary
import com.watchai.domain.SolutionStep
import com.watchai.domain.StudySession

data class PairingCredential(
    val deviceId: String,
    val accessToken: String,
    val scope: String,
    val expiresAtEpochMillis: Long,
)

interface WatchApi {
    suspend fun pair(pairingCode: String, deviceName: String): PairingCredential
    suspend fun listSessions(accessToken: String): List<SessionSummary>
    suspend fun getSession(accessToken: String, sessionId: String): StudySession
    suspend fun getQuestion(accessToken: String, sessionId: String, ordinal: Int): QuestionDetail
    suspend fun deleteSession(accessToken: String, sessionId: String)
    suspend fun revokeDevice(accessToken: String)
}

sealed class WatchApiFailure(message: String, cause: Throwable? = null) : Exception(message, cause) {
    class Unauthorized : WatchApiFailure("O pareamento expirou. Pareie o relógio novamente.")
    class Forbidden : WatchApiFailure("Este relógio não tem acesso a esses dados.")
    class NotFound : WatchApiFailure("A sessão solicitada não está disponível.")
    class RateLimited : WatchApiFailure("Muitas tentativas. Aguarde e tente novamente.")
    class Server : WatchApiFailure("O serviço está indisponível no momento.")
    class Network(cause: Throwable) : WatchApiFailure("Não foi possível conectar. Verifique a rede.", cause)
    class Timeout : WatchApiFailure("A conexão demorou. Tente novamente.")
    class MalformedResponse : WatchApiFailure("A resposta do serviço não pôde ser lida.")
    class InsecureEndpoint : WatchApiFailure("O endereço do serviço precisa usar HTTPS.")
    class ResponseTooLarge : WatchApiFailure("A resposta excede o limite permitido.")
    class Http(status: Int) : WatchApiFailure("O serviço retornou HTTP $status.")
}

internal fun parseSessionSummary(json: org.json.JSONObject): SessionSummary = SessionSummary(
    id = json.requiredString("id"),
    status = SessionStatus.fromApi(json.requiredString("status")),
    receivedCount = json.requiredInt("received_count"),
    expectedCount = json.requiredInt("expected_count"),
    createdAt = json.requiredString("created_at"),
)

internal fun parseQuestionCard(json: org.json.JSONObject): QuestionCard = QuestionCard(
    id = json.requiredString("id"),
    ordinal = json.requiredInt("ordinal"),
    status = QuestionStatus.fromApi(json.requiredString("status")),
    title = json.nullableString("title"),
    resultPreview = json.nullableString("result_preview"),
)

internal fun parseStudySession(json: org.json.JSONObject): StudySession {
    val questionsJson = json.getJSONArray("questions")
    require(questionsJson.length() <= 4) { "Session contains more than four questions" }
    val questions = (0 until questionsJson.length())
        .map { parseQuestionCard(questionsJson.getJSONObject(it)) }
        .sortedBy { it.ordinal }
    require(questions.map { it.ordinal }.distinct().size == questions.size) {
        "Session contains duplicate question ordinals"
    }
    return StudySession(parseSessionSummary(json), questions)
}

internal fun parseQuestionDetail(json: org.json.JSONObject): QuestionDetail {
    val card = parseQuestionCard(json)
    val stepsJson = json.getJSONArray("steps")
    require(stepsJson.length() <= MAX_STEPS) { "Question contains too many solution steps" }
    val steps = (0 until stepsJson.length()).map { index ->
        val step = stepsJson.getJSONObject(index)
        SolutionStep(
            ordinal = step.requiredInt("ordinal"),
            kind = step.requiredString("kind"),
            title = step.requiredString("title"),
            plainText = step.requiredString("plain_text"),
            latex = step.nullableString("latex"),
            renderUrl = step.nullableString("render_url"),
            altText = step.nullableString("alt_text"),
            verified = step.requiredBoolean("verified"),
        )
    }.sortedBy { it.ordinal }
    require(steps.map { it.ordinal }.distinct().size == steps.size) { "Question contains duplicate step ordinals" }
    return QuestionDetail(
        card = card,
        statement = json.requiredString("statement"),
        verified = json.requiredBoolean("verified"),
        verificationStatus = json.nullableString("verification_status") ?: "inconclusive",
        finalAnswer = json.nullableString("final_answer"),
        units = json.nullableString("units"),
        steps = steps,
    )
}

internal fun org.json.JSONObject.requiredString(name: String): String {
    val value = opt(name)
    require(value is String && value.isNotBlank()) { "Missing or invalid $name" }
    return value
}

internal fun org.json.JSONObject.nullableString(name: String): String? {
    if (!has(name) || isNull(name)) return null
    val value = opt(name)
    require(value is String) { "Invalid $name" }
    return value
}

internal fun org.json.JSONObject.requiredInt(name: String): Int {
    val value = opt(name)
    require(value is Number && value.toDouble() == value.toInt().toDouble()) { "Missing or invalid $name" }
    return value.toInt()
}

internal fun org.json.JSONObject.requiredBoolean(name: String): Boolean {
    val value = opt(name)
    require(value is Boolean) { "Missing or invalid $name" }
    return value
}

private const val MAX_STEPS = 20
