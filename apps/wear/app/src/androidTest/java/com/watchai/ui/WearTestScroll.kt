package com.watchai.ui

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.ComposeContentTestRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipe
import kotlin.math.max
import kotlin.math.min

/** Scrolls a Wear [androidx.wear.compose.foundation.lazy.TransformingLazyColumn] until [matcher] is visible. */
internal fun ComposeContentTestRule.scrollToDisplayed(matcher: SemanticsMatcher): SemanticsNodeInteraction {
    if (isWellVisible(matcher)) {
        return onNode(matcher).assertIsDisplayed()
    }
    repeat(12) {
        swipeList(downwards = true)
        if (isWellVisible(matcher)) {
            return onNode(matcher).assertIsDisplayed()
        }
    }
    repeat(16) {
        swipeList(downwards = false)
        if (isWellVisible(matcher)) {
            return onNode(matcher).assertIsDisplayed()
        }
    }
    return onNode(matcher).assertIsDisplayed()
}

private fun ComposeContentTestRule.swipeList(downwards: Boolean) {
    onNodeWithTag("wear-screen-list").performTouchInput {
        val delta = height * 0.18f
        val startY = if (downwards) centerY + delta else centerY - delta
        val endY = if (downwards) centerY - delta else centerY + delta
        swipe(start = Offset(centerX, startY), end = Offset(centerX, endY), durationMillis = 220L)
    }
    waitForIdle()
}

private fun ComposeContentTestRule.isWellVisible(matcher: SemanticsMatcher): Boolean {
    val nodes = onAllNodes(matcher).fetchSemanticsNodes()
    if (nodes.size != 1) return false
    val displayed = runCatching { onNode(matcher).assertIsDisplayed() }.isSuccess
    if (!displayed) return false
    val listBounds = onNodeWithTag("wear-screen-list").fetchSemanticsNode().boundsInRoot
    val nodeBounds = nodes.single().boundsInRoot
    if (nodeBounds.height <= 0f) return false
    val visibleHeight = min(nodeBounds.bottom, listBounds.bottom) - max(nodeBounds.top, listBounds.top)
    return visibleHeight >= min(nodeBounds.height * 0.5f, listBounds.height * 0.5f)
}
