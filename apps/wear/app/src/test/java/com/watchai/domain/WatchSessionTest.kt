package com.watchai.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WatchSessionTest {
    @Test
    fun `question cards keep Q1 through Q4 in ordinal order`() {
        val cards = (4 downTo 1).map { ordinal ->
            QuestionCard(id = "q$ordinal", ordinal = ordinal, status = QuestionStatus.READY)
        }

        assertEquals(listOf("Q1", "Q2", "Q3", "Q4"), cards.sorted().map { it.label })
    }

    @Test
    fun `unverified result cannot be presented as verified`() {
        val presentation = QuestionPresentation(
            card = QuestionCard("q1", 1, QuestionStatus.NEEDS_REVIEW),
            verified = false,
            finalAnswer = null,
        )

        assertFalse(presentation.canShowVerifiedAnswer)
        assertTrue(presentation.requiresReview)
    }

    @Test
    fun `review status suppresses an answer even if the verified flag is inconsistent`() {
        val presentation = QuestionPresentation(
            card = QuestionCard("q1", 1, QuestionStatus.NEEDS_REVIEW),
            verified = true,
            finalAnswer = "42",
        )

        assertFalse(presentation.canShowVerifiedAnswer)
        assertTrue(presentation.requiresReview)
    }
}
