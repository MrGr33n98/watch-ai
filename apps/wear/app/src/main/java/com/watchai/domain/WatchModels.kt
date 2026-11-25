package com.watchai.domain

enum class SessionStatus {
    CREATED, COLLECTING, QUEUED, PROCESSING, READY, PARTIAL, NEEDS_REVIEW, FAILED, CANCELLED, EXPIRED;

    companion object {
        fun fromApi(value: String): SessionStatus =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: NEEDS_REVIEW
    }
}

enum class QuestionStatus {
    UPLOADED, VALIDATING, INTERPRETING, SOLVING, READY, NEEDS_REVIEW, FAILED;

    companion object {
        fun fromApi(value: String): QuestionStatus =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: NEEDS_REVIEW
    }
}

data class QuestionCard(
    val id: String,
    val ordinal: Int,
    val status: QuestionStatus,
    val title: String? = null,
    val resultPreview: String? = null,
) : Comparable<QuestionCard> {
    val label: String get() = "Q$ordinal"

    override fun compareTo(other: QuestionCard): Int = ordinal.compareTo(other.ordinal)
}

data class SessionSummary(
    val id: String,
    val status: SessionStatus,
    val receivedCount: Int,
    val expectedCount: Int,
    val createdAt: String,
)

data class StudySession(
    val summary: SessionSummary,
    val questions: List<QuestionCard>,
)

data class SolutionStep(
    val ordinal: Int,
    val kind: String,
    val title: String,
    val plainText: String,
    val latex: String? = null,
    val renderUrl: String? = null,
    val altText: String? = null,
    val verified: Boolean,
)

data class QuestionDetail(
    val card: QuestionCard,
    val statement: String,
    val verified: Boolean,
    val verificationStatus: String,
    val finalAnswer: String?,
    val units: String?,
    val steps: List<SolutionStep>,
)

data class QuestionPresentation(
    val card: QuestionCard,
    val verified: Boolean,
    val finalAnswer: String?,
) {
    val canShowVerifiedAnswer: Boolean
        get() = verified && card.status != QuestionStatus.NEEDS_REVIEW && !finalAnswer.isNullOrBlank()
    val requiresReview: Boolean get() = card.status == QuestionStatus.NEEDS_REVIEW || !verified
}

fun StudySession.orderedQuestions(): List<QuestionCard> = questions.sorted()
