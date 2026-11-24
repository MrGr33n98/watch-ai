package com.watchai.ui

import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.performClick
import com.watchai.domain.QuestionCard
import com.watchai.domain.QuestionStatus
import com.watchai.domain.SessionStatus
import com.watchai.domain.SessionSummary
import com.watchai.domain.StudySession
import com.watchai.ui.screens.QuestionListScreen
import com.watchai.ui.screens.SessionListScreen
import com.watchai.ui.screens.WatchAiWearRoot
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class SessionListScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun `shows four questions in ordinal order and opens selected session`() {
        var selectedSession: String? = null
        val session = StudySession(
            summary = SessionSummary("session-1", SessionStatus.READY, 4, 4, "2026-11-23T18:00:00Z"),
            questions = (4 downTo 1).map { ordinal ->
                QuestionCard("q$ordinal", ordinal, QuestionStatus.READY, "Questão $ordinal", "Resposta")
            },
        )

        composeRule.setContent {
            WatchAiWearRoot {
                SessionListScreen(
                    sessions = listOf(session.summary),
                    loading = false,
                    offline = false,
                    onOpenSession = { selectedSession = it },
                    onPairDevice = {},
                )
            }
        }

        composeRule.scrollToDisplayed(hasText("4/4 exercícios"))
        composeRule.scrollToDisplayed(hasText("Pronta"))
        composeRule.scrollToDisplayed(hasContentDescription("Abrir sessão, 4 de 4 exercícios"))
            .performClick()
        composeRule.runOnIdle { assertEquals("session-1", selectedSession) }
    }

    @Test
    fun `session deletion requires explicit confirmation`() {
        val sessionId = "00000000-0000-4000-8000-000000000001"
        var deletedSession: String? = null
        val session = SessionSummary(
            sessionId,
            SessionStatus.READY,
            4,
            4,
            "2026-11-23T18:00:00Z",
        )

        composeRule.setContent {
            WatchAiWearRoot {
                SessionListScreen(
                    sessions = listOf(session),
                    loading = false,
                    offline = false,
                    onOpenSession = {},
                    onDeleteSession = { deletedSession = it },
                    onPairDevice = {},
                )
            }
        }

        composeRule.scrollToDisplayed(hasText("Excluir sessão")).performClick()
        composeRule.scrollToDisplayed(hasText("Confirmar exclusão")).performClick()
        composeRule.runOnIdle { assertEquals(sessionId, deletedSession) }
    }

    @Test
    fun `question list renders Q1 to Q4 in arrival order`() {
        val session = StudySession(
            summary = SessionSummary("session-1", SessionStatus.READY, 4, 4, "2026-11-23T18:00:00Z"),
            questions = (4 downTo 1).map { ordinal ->
                QuestionCard("q$ordinal", ordinal, QuestionStatus.READY, "Questão $ordinal", "Resposta")
            },
        )

        composeRule.setContent {
            WatchAiWearRoot { QuestionListScreen(session, offline = false, onOpenQuestion = {}) }
        }

        listOf("Q1", "Q2", "Q3", "Q4").forEach {
            composeRule.scrollToDisplayed(hasText(it))
        }
    }

    @Test
    fun `shows loading empty offline and review states explicitly`() {
        composeRule.setContent {
            WatchAiWearRoot {
                SessionListScreen(
                    sessions = emptyList(),
                    loading = false,
                    offline = true,
                    onOpenSession = {},
                    onPairDevice = {},
                )
            }
        }

        composeRule.scrollToDisplayed(hasText("Offline · dados sincronizados"))
        composeRule.scrollToDisplayed(hasText("Nenhuma sessão sincronizada"))
        composeRule.scrollToDisplayed(hasText("Parear relógio"))
    }

    @Test
    fun `shows processing ready partial and review session states`() {
        val sessions = listOf(
            SessionSummary("processing", SessionStatus.PROCESSING, 4, 4, "2026-11-23T18:00:00Z"),
            SessionSummary("ready", SessionStatus.READY, 4, 4, "2026-11-23T18:00:00Z"),
            SessionSummary("partial", SessionStatus.PARTIAL, 2, 4, "2026-11-23T18:00:00Z"),
            SessionSummary("review", SessionStatus.NEEDS_REVIEW, 4, 4, "2026-11-23T18:00:00Z"),
        )

        composeRule.setContent {
            WatchAiWearRoot {
                SessionListScreen(
                    sessions = sessions,
                    loading = false,
                    offline = false,
                    onOpenSession = {},
                    onPairDevice = {},
                )
            }
        }

        listOf("Processando", "Pronta", "Parcial", "Precisa de revisão").forEach {
            composeRule.scrollToDisplayed(hasText(it))
        }
    }
}
