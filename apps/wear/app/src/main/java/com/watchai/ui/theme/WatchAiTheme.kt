package com.watchai.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.wear.compose.material3.ColorScheme
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.dynamicColorScheme

@Composable
fun WatchAiTheme(content: @Composable () -> Unit) {
    val colorScheme = dynamicColorScheme(LocalContext.current) ?: ColorScheme()
    MaterialTheme(colorScheme = colorScheme, content = content)
}
