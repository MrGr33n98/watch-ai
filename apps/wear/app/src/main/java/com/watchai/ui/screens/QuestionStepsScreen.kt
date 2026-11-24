package com.watchai.ui.screens

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.wear.compose.material3.ListHeader
import androidx.wear.compose.material3.ListHeaderDefaults
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.SurfaceTransformation
import androidx.wear.compose.material3.Text
import androidx.wear.compose.material3.lazy.TransformationSpec
import androidx.wear.compose.material3.lazy.transformedHeight
import com.watchai.domain.QuestionDetail
import com.watchai.domain.QuestionPresentation

@Composable
fun QuestionStepsScreen(
    detail: QuestionDetail,
    stepIndex: Int,
    offline: Boolean,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit,
) {
    val presentation = QuestionPresentation(detail.card, detail.verified, detail.finalAnswer)
    val verifiedAnswer = detail.finalAnswer.takeIf { presentation.canShowVerifiedAnswer }
    val safeIndex = stepIndex.coerceIn(0, (detail.steps.size - 1).coerceAtLeast(0))
    val currentStep = detail.steps.getOrNull(safeIndex)
    WearScreenScaffold { transformationSpec ->
        item(key = "question-header", contentType = "header") {
            ListHeader(
                modifier = Modifier
                    .fillMaxWidth()
                    .transformedHeight(this, transformationSpec)
                    .minimumVerticalContentPadding(ListHeaderDefaults.minimumTopListContentPadding),
                transformation = SurfaceTransformation(transformationSpec),
            ) {
                Text(detail.card.label, style = MaterialTheme.typography.titleMedium)
            }
        }
        detail.card.title?.let { title ->
            item(key = "question-title", contentType = "text") {
                WearTextItem(title, transformationSpec, this)
            }
        }
        if (offline) {
            item(key = "offline", contentType = "status") {
                WearTextItem("Offline · conteúdo salvo", transformationSpec, this, MaterialTheme.colorScheme.primary)
            }
        }
        if (presentation.requiresReview) {
            item(key = "review", contentType = "warning") {
                WearTextItem(
                    "Precisa de revisão",
                    transformationSpec,
                    this,
                    MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.titleSmall,
                )
            }
            item(key = "unverified", contentType = "status") {
                WearTextItem("Resultado não verificado", transformationSpec, this, MaterialTheme.colorScheme.error)
            }
        }
        item(key = "statement-heading", contentType = "heading") {
            WearTextItem("Problema", transformationSpec, this, style = MaterialTheme.typography.titleSmall)
        }
        item(key = "statement", contentType = "statement") {
            WearTextItem(detail.statement, transformationSpec, this, style = MaterialTheme.typography.bodyLarge)
        }

        if (currentStep != null) {
            item(key = "step-count", contentType = "status") {
                WearTextItem(
                    "Passo ${safeIndex + 1} de ${detail.steps.size}",
                    transformationSpec,
                    this,
                    color = MaterialTheme.colorScheme.secondary,
                )
            }
            item(key = "step-title", contentType = "heading") {
                WearTextItem(currentStep.title, transformationSpec, this, style = MaterialTheme.typography.titleSmall)
            }
            item(key = "step-content", contentType = "math") {
                WearTextItem(
                    currentStep.plainText,
                    transformationSpec,
                    this,
                    style = MaterialTheme.typography.bodyLarge,
                    accessibilityText = currentStep.altText ?: currentStep.plainText,
                )
            }
            item(key = "step-verification", contentType = "status") {
                val stepStatus = if (currentStep.verified) "Etapa verificada" else "Etapa não verificada"
                WearTextItem(
                    stepStatus,
                    transformationSpec,
                    this,
                    color = if (currentStep.verified) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
            }
        } else {
            item(key = "steps-empty", contentType = "warning") {
                WearTextItem("Etapas indisponíveis", transformationSpec, this, MaterialTheme.colorScheme.error)
            }
        }

        verifiedAnswer?.let { answer ->
            item(key = "result-heading", contentType = "heading") {
                val resultLabel = if (detail.verified) "Resultado verificado" else "Resultado não verificado"
                WearTextItem(
                    resultLabel,
                    transformationSpec,
                    this,
                    color = if (detail.verified) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.titleSmall,
                )
            }
            item(key = "result", contentType = "result") {
                WearTextItem(
                    if (detail.units.isNullOrBlank()) answer else "$answer ${detail.units}",
                    transformationSpec,
                    this,
                    style = MaterialTheme.typography.titleLarge,
                )
            }
        }

        item(key = "previous", contentType = "action") {
            WearActionButton(
                "Passo anterior",
                "Passo anterior",
                transformationSpec,
                this,
                onPrevious,
                enabled = safeIndex > 0,
            )
        }
        item(key = "next", contentType = "action") {
            WearActionButton(
                "Próximo passo",
                "Próximo passo",
                transformationSpec,
                this,
                onNext,
                enabled = safeIndex < detail.steps.lastIndex,
            )
        }
        item(key = "back", contentType = "action") {
            WearActionButton("Questões", "Voltar para questões", transformationSpec, this, onBack)
        }
    }
}
