package com.watchai.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.wear.compose.foundation.lazy.items
import androidx.wear.compose.material3.Button
import androidx.wear.compose.material3.ListHeader
import androidx.wear.compose.material3.ListHeaderDefaults
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.SurfaceTransformation
import androidx.wear.compose.material3.Text
import androidx.wear.compose.material3.lazy.transformedHeight
import com.watchai.domain.SessionSummary

@Composable
fun SessionListScreen(
    sessions: List<SessionSummary>,
    loading: Boolean,
    offline: Boolean,
    onOpenSession: (String) -> Unit,
    onPairDevice: () -> Unit,
    onDeleteSession: (String) -> Unit = {},
    onRevokeDevice: () -> Unit = {},
    onRetry: () -> Unit = {},
    errorMessage: String? = null,
) {
    var pendingDeletionId by remember { mutableStateOf<String?>(null) }
    WearScreenScaffold { transformationSpec ->
        item(key = "sessions-header", contentType = "header") {
            ListHeader(
                modifier = Modifier
                    .fillMaxWidth()
                    .transformedHeight(this, transformationSpec)
                    .minimumVerticalContentPadding(ListHeaderDefaults.minimumTopListContentPadding),
                transformation = SurfaceTransformation(transformationSpec),
            ) {
                Text("Watch AI · Sessões", style = androidx.wear.compose.material3.MaterialTheme.typography.titleMedium)
            }
        }
        if (offline) {
            item(key = "offline", contentType = "message") {
                WearTextItem("Offline · dados sincronizados", transformationSpec, this, MaterialTheme.colorScheme.primary)
            }
        }
        if (loading) {
            item(key = "loading", contentType = "message") {
                WearTextItem("Carregando sessões…", transformationSpec, this)
            }
        }
        if (errorMessage != null) {
            item(key = "error", contentType = "message") {
                WearTextItem(errorMessage, transformationSpec, this, MaterialTheme.colorScheme.error)
            }
            item(key = "retry", contentType = "action") {
                WearActionButton("Tentar novamente", "Tentar novamente", transformationSpec, this, onRetry)
            }
        }
        if (!loading && sessions.isEmpty()) {
            item(key = "empty", contentType = "message") {
                WearTextItem("Nenhuma sessão sincronizada", transformationSpec, this)
            }
            item(key = "pair", contentType = "action") {
                WearActionButton("Parear relógio", "Parear relógio", transformationSpec, this, onPairDevice)
            }
        }
        items(sessions, key = { it.id }, contentType = { "session" }) { session ->
            val itemScope = this
            Column(modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { onOpenSession(session.id) },
                    modifier = itemScope.wearListItemModifier(transformationSpec)
                        .semantics {
                            contentDescription =
                                "Abrir sessão, ${session.receivedCount} de ${session.expectedCount} exercícios"
                        },
                    transformation = SurfaceTransformation(transformationSpec),
                    label = { Text("${session.receivedCount}/${session.expectedCount} exercícios") },
                    secondaryLabel = { Text(session.status.labelPt()) },
                )
                if (!offline) {
                    if (pendingDeletionId == session.id) {
                        WearTextItem(
                            "Excluir soluções e dados desta sessão?",
                            transformationSpec,
                            itemScope,
                        )
                        WearActionButton(
                            "Confirmar exclusão",
                            "Confirmar exclusão da sessão",
                            transformationSpec,
                            itemScope,
                            onClick = {
                                onDeleteSession(session.id)
                                pendingDeletionId = null
                            },
                        )
                        WearActionButton(
                            "Cancelar",
                            "Cancelar exclusão da sessão",
                            transformationSpec,
                            itemScope,
                            onClick = { pendingDeletionId = null },
                        )
                    } else {
                        WearActionButton(
                            "Excluir sessão",
                            "Pedir confirmação para excluir sessão com ${session.receivedCount} exercícios",
                            transformationSpec,
                            itemScope,
                            onClick = { pendingDeletionId = session.id },
                        )
                    }
                }
            }
        }
        if (sessions.isNotEmpty()) {
            item(key = "revoke", contentType = "action") {
                WearActionButton("Revogar dispositivo", "Revogar dispositivo", transformationSpec, this, onRevokeDevice)
            }
        }
    }
}
