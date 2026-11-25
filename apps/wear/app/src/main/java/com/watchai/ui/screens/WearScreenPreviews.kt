package com.watchai.ui.screens

import androidx.compose.runtime.Composable
import androidx.wear.compose.ui.tooling.preview.WearPreviewDevices
import androidx.wear.compose.ui.tooling.preview.WearPreviewFontScales
import com.watchai.domain.QuestionCard
import com.watchai.domain.QuestionDetail
import com.watchai.domain.QuestionStatus
import com.watchai.domain.SessionStatus
import com.watchai.domain.SessionSummary
import com.watchai.domain.SolutionStep
import com.watchai.domain.StudySession

private val previewSession = StudySession(
    summary = SessionSummary("preview-session", SessionStatus.READY, 4, 4, "2026-11-23T18:00:00Z"),
    questions = (1..4).map { ordinal ->
        QuestionCard("preview-q$ordinal", ordinal, QuestionStatus.READY, "Exercício $ordinal", "Resposta verificada")
    },
)

private val previewQuestion = QuestionDetail(
    card = QuestionCard("preview-q1", 1, QuestionStatus.READY, "Equação do primeiro grau"),
    statement = "Resolva 2x + 4 = 10.",
    verified = true,
    verificationStatus = "verified",
    finalAnswer = "x = 3",
    units = null,
    steps = listOf(
        SolutionStep(1, "formula", "Isolar a variável", "2x = 10 − 4", verified = true),
        SolutionStep(2, "calculation", "Calcular", "2x = 6; x = 6 ÷ 2", verified = true),
    ),
)

@WearPreviewDevices
@WearPreviewFontScales
@Composable
private fun SessionListScreenPreview() {
    WatchAiWearRoot {
        SessionListScreen(
            sessions = listOf(previewSession.summary),
            loading = false,
            offline = false,
            onOpenSession = {},
            onPairDevice = {},
        )
    }
}

@WearPreviewDevices
@WearPreviewFontScales
@Composable
private fun QuestionListScreenPreview() {
    WatchAiWearRoot { QuestionListScreen(previewSession, offline = false, onOpenQuestion = {}) }
}

@WearPreviewDevices
@WearPreviewFontScales
@Composable
private fun QuestionStepsScreenPreview() {
    WatchAiWearRoot {
        QuestionStepsScreen(
            detail = previewQuestion,
            stepIndex = 0,
            offline = false,
            onPrevious = {},
            onNext = {},
            onBack = {},
        )
    }
}

@WearPreviewDevices
@WearPreviewFontScales
@Composable
private fun PairingScreenPreview() {
    WatchAiWearRoot {
        PairingScreen(
            endpoint = "https://api.example.com",
            pairingCode = "ABC123",
            busy = false,
            errorMessage = null,
            onEndpointChange = {},
            onPairingCodeChange = {},
            onPair = {},
        )
    }
}
