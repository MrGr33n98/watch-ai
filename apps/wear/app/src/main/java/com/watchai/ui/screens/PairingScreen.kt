package com.watchai.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.Alignment
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.wear.compose.material3.ListHeader
import androidx.wear.compose.material3.ListHeaderDefaults
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.SurfaceTransformation
import androidx.wear.compose.material3.Text
import androidx.wear.compose.material3.lazy.transformedHeight

@Composable
fun PairingScreen(
    endpoint: String,
    pairingCode: String,
    busy: Boolean,
    errorMessage: String?,
    onEndpointChange: (String) -> Unit,
    onPairingCodeChange: (String) -> Unit,
    onPair: () -> Unit,
) {
    WearScreenScaffold { transformationSpec ->
        item(key = "pairing-header", contentType = "header") {
            ListHeader(
                modifier = Modifier
                    .fillMaxWidth()
                    .transformedHeight(this, transformationSpec)
                    .minimumVerticalContentPadding(ListHeaderDefaults.minimumTopListContentPadding),
                transformation = SurfaceTransformation(transformationSpec),
            ) {
                Text("Vincular relógio", style = MaterialTheme.typography.titleMedium)
            }
        }
        item(key = "pairing-instructions", contentType = "text") {
            WearTextItem(
                "Use o endereço HTTPS do serviço e o código temporário de pareamento.",
                transformationSpec,
                this,
            )
        }
        item(key = "endpoint-label", contentType = "label") {
            WearTextItem(
                "Endereço HTTPS",
                transformationSpec,
                this,
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.titleSmall,
                textAlign = androidx.compose.ui.text.style.TextAlign.Start,
            )
        }
        item(key = "endpoint-input", contentType = "input") {
            InputBox(
                value = endpoint,
                label = "Endereço HTTPS",
                placeholder = "https://seu-servidor",
                keyboardType = KeyboardType.Uri,
                itemScope = this,
                transformationSpec = transformationSpec,
                onValueChange = onEndpointChange,
            )
        }
        item(key = "code-label", contentType = "label") {
            WearTextItem(
                "Código temporário",
                transformationSpec,
                this,
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.titleSmall,
                textAlign = androidx.compose.ui.text.style.TextAlign.Start,
            )
        }
        item(key = "code-input", contentType = "input") {
            InputBox(
                value = pairingCode,
                label = "Código temporário",
                placeholder = "Ex: A7K9M2P4",
                keyboardType = KeyboardType.Ascii,
                itemScope = this,
                transformationSpec = transformationSpec,
            ) { input -> onPairingCodeChange(input.filter { it.isLetterOrDigit() || it == '-' || it == '_' }.take(12)) }
        }
        if (errorMessage != null) {
            item(key = "pairing-error", contentType = "error") {
                WearTextItem(errorMessage, transformationSpec, this, MaterialTheme.colorScheme.error)
            }
        }
        item(key = "pair-action", contentType = "action") {
            WearActionButton(
                label = if (busy) "Conectando…" else "Parear",
                description = "Parear relógio",
                transformationSpec = transformationSpec,
                itemScope = this,
                onClick = onPair,
                enabled = !busy && endpoint.startsWith("https://", ignoreCase = true) &&
                    pairingCode.replace("-", "").length in 6..12,
            )
        }
    }
}

@Composable
private fun InputBox(
    value: String,
    label: String,
    placeholder: String,
    keyboardType: KeyboardType,
    itemScope: androidx.wear.compose.foundation.lazy.TransformingLazyColumnItemScope,
    transformationSpec: androidx.wear.compose.material3.lazy.TransformationSpec,
    onValueChange: (String) -> Unit,
) {
    Box(
        modifier = Modifier
            .then(itemScope.wearListItemModifier(transformationSpec))
            .heightIn(min = 52.dp)
            .background(MaterialTheme.colorScheme.background)
            .border(1.dp, MaterialTheme.colorScheme.outline, MaterialTheme.shapes.large)
            .padding(horizontal = 10.dp, vertical = 12.dp),
        contentAlignment = Alignment.CenterStart,
    ) {
        if (value.isEmpty()) {
            Text(
                text = placeholder,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
            )
        }
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth().semantics { contentDescription = label },
            singleLine = true,
            keyboardOptions = KeyboardOptions(
                keyboardType = keyboardType,
                capitalization = KeyboardCapitalization.None,
                autoCorrectEnabled = false,
            ),
            cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
            textStyle = MaterialTheme.typography.bodyLarge.copy(color = MaterialTheme.colorScheme.onSurface),
        )
    }
}
