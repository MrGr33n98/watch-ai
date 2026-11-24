package com.watchai.ui.screens

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.wear.compose.foundation.lazy.TransformingLazyColumnItemScope
import androidx.wear.compose.material3.Button
import androidx.wear.compose.material3.ListHeader
import androidx.wear.compose.material3.ListHeaderDefaults
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.SurfaceTransformation
import androidx.wear.compose.material3.Text
import androidx.wear.compose.material3.lazy.TransformationSpec
import androidx.wear.compose.material3.lazy.transformedHeight
import com.watchai.domain.QuestionCard
import com.watchai.domain.StudySession
import com.watchai.domain.orderedQuestions

@Composable
fun QuestionListScreen(
    session: StudySession,
    offline: Boolean,
    onOpenQuestion: (Int) -> Unit,
    onBack: () -> Unit = {},
    loading: Boolean = false,
    errorMessage: String? = null,
    onRetry: () -> Unit = {},
) {
    WearScreenScaffold { transformationSpec ->
        item(key = "questions-header", contentType = "header") {
            ListHeader(
                modifier = Modifier
                    .fillMaxWidth()
                    .transformedHeight(this, transformationSpec)
                    .minimumVerticalContentPadding(ListHeaderDefaults.minimumTopListContentPadding),
                transformation = SurfaceTransformation(transformationSpec),
            ) {
                Text("Exercícios · ${session.questions.size}", style = MaterialTheme.typography.titleMedium)
            }
        }
        if (offline) {
            item(key = "offline", contentType = "status") {
                WearTextItem("Offline · conteúdo salvo", transformationSpec, this, MaterialTheme.colorScheme.primary)
            }
        }
        if (loading) {
            item(key = "loading", contentType = "status") {
                WearTextItem("Carregando exercício…", transformationSpec, this)
            }
        }
        if (errorMessage != null) {
            item(key = "error", contentType = "error") {
                WearTextItem(errorMessage, transformationSpec, this, MaterialTheme.colorScheme.error)
            }
            item(key = "retry", contentType = "action") {
                WearActionButton("Tentar novamente", "Tentar novamente", transformationSpec, this, onRetry)
            }
        }
        session.orderedQuestions().forEach { question ->
            item(key = question.id, contentType = "question") {
                QuestionButton(question, transformationSpec, this) { onOpenQuestion(question.ordinal) }
            }
        }
        item(key = "back", contentType = "action") {
            WearActionButton("Voltar", "Voltar para sessões", transformationSpec, this, onBack)
        }
    }
}

@Composable
private fun QuestionButton(
    question: QuestionCard,
    transformationSpec: TransformationSpec,
    itemScope: TransformingLazyColumnItemScope,
    onOpen: () -> Unit,
) {
    val status = question.status.labelPt()
    Button(
        onClick = onOpen,
        modifier = itemScope.wearListItemModifier(transformationSpec).semantics {
            contentDescription = listOfNotNull(question.label, question.title ?: status, question.resultPreview)
                .joinToString(", ")
        },
        transformation = SurfaceTransformation(transformationSpec),
        label = { Text(question.label) },
        secondaryLabel = { Text(question.title ?: status) },
    )
}
