package com.watchai.ui.screens

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.wear.compose.foundation.lazy.TransformingLazyColumnItemScope
import androidx.wear.compose.material3.Button
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.SurfaceTransformation
import androidx.wear.compose.material3.Text
import androidx.wear.compose.material3.lazy.TransformationSpec

@Composable
internal fun WearTextItem(
    text: String,
    transformationSpec: TransformationSpec,
    itemScope: TransformingLazyColumnItemScope,
    color: Color = MaterialTheme.colorScheme.onSurface,
    textAlign: TextAlign = TextAlign.Center,
    style: androidx.compose.ui.text.TextStyle = MaterialTheme.typography.bodyMedium,
    accessibilityText: String = text,
) {
    Text(
        text = text,
        modifier = itemScope.wearListItemModifier(transformationSpec)
            .semantics { contentDescription = accessibilityText },
        style = style,
        color = color,
        textAlign = textAlign,
    )
}

@Composable
internal fun WearActionButton(
    label: String,
    description: String,
    transformationSpec: TransformationSpec,
    itemScope: TransformingLazyColumnItemScope,
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = itemScope.wearListItemModifier(transformationSpec)
            .semantics { contentDescription = description },
        transformation = SurfaceTransformation(transformationSpec),
        label = { Text(label) },
    )
}
