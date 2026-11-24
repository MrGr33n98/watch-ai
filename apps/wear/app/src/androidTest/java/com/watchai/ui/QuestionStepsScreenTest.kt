package com.watchai.ui

import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertDoesNotExist
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.fetchSemanticsNode
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.requiredSize
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.watchai.domain.QuestionCard
import com.watchai.domain.QuestionDetail
import com.watchai.domain.QuestionStatus
import com.watchai.domain.SolutionStep
import com.watchai.ui.screens.QuestionStepsScreen
import com.watchai.ui.screens.WatchAiWearRoot
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class QuestionStepsScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun `navigates forward and backward through named solution steps`() {
        var currentIndex by mutableIntStateOf(0)
        val detail = QuestionDetail(
            card = QuestionCard("q1", 1, QuestionStatus.READY),
            statement = "Calcule 2 + 2.",
            verified = true,
            verificationStatus = "verified",
            finalAnswer = "4",
            units = null,
            steps = listOf(
                SolutionStep(1, "statement", "Enunciado", "Calcule 2 + 2.", verified = true),
                SolutionStep(2, "formula", "Fórmula", "2 + 2 = 4", verified = true),
            ),
        )

        composeRule.setContent {
            WatchAiWearRoot {
                QuestionStepsScreen(
                    detail = detail,
                    stepIndex = currentIndex,
                    offline = false,
                    onPrevious = { currentIndex -= 1 },
                    onNext = { currentIndex += 1 },
                    onBack = {},
                )
            }
        }

        composeRule.onNodeWithText("Enunciado").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("Passo 1 de 2").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Próximo passo").performScrollTo().performClick()
        composeRule.onNodeWithText("Passo 2 de 2").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("Fórmula").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Passo anterior").performScrollTo().performClick()
        composeRule.onNodeWithText("Enunciado").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun `review response never labels its answer as verified`() {
        val review = QuestionDetail(
            card = QuestionCard("q2", 2, QuestionStatus.NEEDS_REVIEW),
            statement = "Símbolo ilegível.",
            verified = false,
            verificationStatus = "inconclusive",
            finalAnswer = null,
            units = null,
            steps = emptyList(),
        )

        composeRule.setContent {
            WatchAiWearRoot {
                QuestionStepsScreen(review, 0, offline = false, onPrevious = {}, onNext = {}, onBack = {})
            }
        }

        composeRule.onNodeWithText("Precisa de revisão").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("Resultado não verificado").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun `review status suppresses a contradictory final answer`() {
        val inconsistent = QuestionDetail(
            card = QuestionCard("q2", 2, QuestionStatus.NEEDS_REVIEW),
            statement = "A imagem está ambígua.",
            verified = true,
            verificationStatus = "verified",
            finalAnswer = "42",
            units = null,
            steps = emptyList(),
        )

        composeRule.setContent {
            WatchAiWearRoot {
                QuestionStepsScreen(inconsistent, 0, offline = false, onPrevious = {}, onNext = {}, onBack = {})
            }
        }

        composeRule.onNodeWithText("Precisa de revisão").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("42").assertDoesNotExist()
    }

    @Test
    fun `solution statements and navigation expose accessible labels and state`() {
        val detail = sampleQuestion()
        composeRule.setContent {
            WatchAiWearRoot {
                QuestionStepsScreen(detail, 0, offline = false, onPrevious = {}, onNext = {}, onBack = {})
            }
        }

        composeRule.onNodeWithContentDescription("Calcule 2 + 2.").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Passo anterior").performScrollTo().assertIsNotEnabled()
        composeRule.onNodeWithContentDescription("Próximo passo").performScrollTo().assertIsEnabled()
    }

    @Test
    fun `cached solution announces offline status`() {
        composeRule.setContent {
            WatchAiWearRoot {
                QuestionStepsScreen(sampleQuestion(), 0, offline = true, onPrevious = {}, onNext = {}, onBack = {})
            }
        }

        composeRule.onNodeWithText("Offline · conteúdo salvo").performScrollTo().assertIsDisplayed()
    }

    @Test
    fun `question steps fit representative 40mm round display at 1_3 text scale`() {
        assertRoundDisplayFits(180.dp, 1.3f)
    }

    @Test
    fun `question steps fit representative 40mm round display at 1_5 text scale`() {
        assertRoundDisplayFits(180.dp, 1.5f)
    }

    @Test
    fun `question steps fit representative 44mm round display at 1_3 text scale`() {
        assertRoundDisplayFits(200.dp, 1.3f)
    }

    @Test
    fun `question steps fit representative 44mm round display at 1_5 text scale`() {
        assertRoundDisplayFits(200.dp, 1.5f)
    }

    private fun assertRoundDisplayFits(displayDiameter: Dp, fontScale: Float) {
        composeRule.setContent {
            CompositionLocalProvider(LocalDensity provides Density(density = 1f, fontScale = fontScale)) {
                Box(
                    modifier = Modifier
                        .requiredSize(displayDiameter)
                        .clip(CircleShape)
                        .testTag("round-display"),
                ) {
                    WatchAiWearRoot {
                        QuestionStepsScreen(
                            sampleQuestion(),
                            stepIndex = 0,
                            offline = false,
                            onPrevious = {},
                            onNext = {},
                            onBack = {},
                        )
                    }
                }
            }
        }

        composeRule.onNodeWithContentDescription("Problema").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithContentDescription("Próximo passo").performScrollTo().assertIsDisplayed()
        val displayBounds = composeRule.onNodeWithTag("round-display").fetchSemanticsNode().boundsInRoot
        val controlBounds = composeRule
            .onNodeWithContentDescription("Próximo passo")
            .fetchSemanticsNode()
            .boundsInRoot
        assertTrue("Navigation control clipped at $displayDiameter/$fontScale", controlBounds.left >= displayBounds.left)
        assertTrue("Navigation control clipped at $displayDiameter/$fontScale", controlBounds.right <= displayBounds.right)
    }

    private fun sampleQuestion() = QuestionDetail(
        card = QuestionCard("q-layout", 1, QuestionStatus.READY),
        statement = "Calcule 2 + 2.",
        verified = true,
        verificationStatus = "verified",
        finalAnswer = "4",
        units = null,
        steps = listOf(
            SolutionStep(1, "statement", "Enunciado", "Calcule 2 + 2.", verified = true),
            SolutionStep(2, "formula", "Fórmula", "2 + 2 = 4", verified = true),
        ),
    )
}
