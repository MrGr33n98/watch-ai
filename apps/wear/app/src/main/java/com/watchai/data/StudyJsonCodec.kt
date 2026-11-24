package com.watchai.data

import com.watchai.domain.QuestionDetail
import com.watchai.domain.SessionSummary
import com.watchai.domain.StudySession
import org.json.JSONArray
import org.json.JSONObject

object StudyJsonCodec {
    fun decodeSessionList(value: String): List<SessionSummary> {
        val items = JSONObject(value).getJSONArray("items")
        require(items.length() <= 20)
        return (0 until items.length()).map { parseSessionSummary(items.getJSONObject(it)) }
    }

    fun decodeSession(value: String): StudySession = parseStudySession(JSONObject(value))

    fun decodeQuestion(value: String): QuestionDetail = parseQuestionDetail(JSONObject(value))

    fun encodeSessionList(items: List<SessionSummary>): String {
        val array = JSONArray()
        items.forEach { summary -> array.put(summary.toJson()) }
        return JSONObject().put("items", array).put("next_cursor", JSONObject.NULL).toString()
    }

    fun encodeSession(session: StudySession): String {
        val questions = JSONArray()
        session.questions.sorted().forEach { card ->
            questions.put(
                JSONObject()
                    .put("id", card.id)
                    .put("ordinal", card.ordinal)
                    .put("status", card.status.name.lowercase())
                    .put("title", card.title ?: JSONObject.NULL)
                    .put("result_preview", card.resultPreview ?: JSONObject.NULL),
            )
        }
        return session.summary.toJson().put("questions", questions).toString()
    }

    fun encodeQuestion(question: QuestionDetail): String {
        val steps = JSONArray()
        question.steps.sortedBy { it.ordinal }.forEach { step ->
            steps.put(
                JSONObject()
                    .put("ordinal", step.ordinal)
                    .put("kind", step.kind)
                    .put("title", step.title)
                    .put("plain_text", step.plainText)
                    .put("latex", step.latex ?: JSONObject.NULL)
                    .put("render_url", step.renderUrl ?: JSONObject.NULL)
                    .put("alt_text", step.altText ?: JSONObject.NULL)
                    .put("verified", step.verified),
            )
        }
        return JSONObject()
            .put("id", question.card.id)
            .put("ordinal", question.card.ordinal)
            .put("status", question.card.status.name.lowercase())
            .put("title", question.card.title ?: JSONObject.NULL)
            .put("result_preview", question.card.resultPreview ?: JSONObject.NULL)
            .put("statement", question.statement)
            .put("verified", question.verified)
            .put("verification_status", question.verificationStatus)
            .put("final_answer", question.finalAnswer ?: JSONObject.NULL)
            .put("units", question.units ?: JSONObject.NULL)
            .put("steps", steps)
            .toString()
    }

    private fun SessionSummary.toJson(): JSONObject = JSONObject()
        .put("id", id)
        .put("status", status.name.lowercase())
        .put("received_count", receivedCount)
        .put("expected_count", expectedCount)
        .put("created_at", createdAt)
}
