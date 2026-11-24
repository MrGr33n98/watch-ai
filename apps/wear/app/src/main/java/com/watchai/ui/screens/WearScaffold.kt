package com.watchai.ui.screens

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.Dp
import androidx.wear.compose.foundation.lazy.TransformingLazyColumn
import androidx.wear.compose.foundation.lazy.TransformingLazyColumnItemScope
import androidx.wear.compose.foundation.lazy.TransformingLazyColumnScope
import androidx.wear.compose.foundation.lazy.rememberTransformingLazyColumnState
import androidx.wear.compose.material3.AppScaffold
import androidx.wear.compose.material3.ButtonDefaults
import androidx.wear.compose.material3.ScreenScaffold
import androidx.wear.compose.material3.lazy.TransformationSpec
import androidx.wear.compose.material3.lazy.rememberTransformationSpec
import androidx.wear.compose.material3.lazy.transformedHeight
import com.watchai.ui.theme.WatchAiTheme

/** App root used by the Activity, Wear previews, and Compose UI tests. */
@Composable
internal fun WatchAiWearRoot(content: @Composable () -> Unit) {
    WatchAiTheme {
        AppScaffold { content() }
    }
}

@Composable
internal fun WearScreenScaffold(
    modifier: Modifier = Modifier,
    content: TransformingLazyColumnScope.(TransformationSpec) -> Unit,
) {
    val scrollState = rememberTransformingLazyColumnState()
    val transformationSpec = rememberTransformationSpec()
    ScreenScaffold(scrollState = scrollState) { contentPadding ->
        TransformingLazyColumn(
            modifier = modifier.fillMaxSize(),
            state = scrollState,
            contentPadding = contentPadding,
        ) {
            content(transformationSpec)
        }
    }
}

/** Applies the default Wear list touch spacing and curved-screen transformation. */
@Composable
internal fun TransformingLazyColumnItemScope.wearListItemModifier(
    transformationSpec: TransformationSpec,
    minimumVerticalPadding: Dp = ButtonDefaults.minimumVerticalListContentPadding,
): Modifier = Modifier
    .transformedHeight(this, transformationSpec)
    .minimumVerticalContentPadding(minimumVerticalPadding)
    .fillMaxWidth()
