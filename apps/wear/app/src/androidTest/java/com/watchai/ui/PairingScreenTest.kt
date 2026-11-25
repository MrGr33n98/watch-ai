package com.watchai.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.performClick
import com.watchai.ui.screens.PairingScreen
import com.watchai.ui.screens.WatchAiWearRoot
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class PairingScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun `pairing fields and action have accessible names`() {
        var paired = false
        composeRule.setContent {
            WatchAiWearRoot {
                PairingScreen(
                    endpoint = "https://api.example.com",
                    pairingCode = "ABC123",
                    busy = false,
                    errorMessage = null,
                    onEndpointChange = {},
                    onPairingCodeChange = {},
                    onPair = { paired = true },
                )
            }
        }

        composeRule.scrollToDisplayed(hasContentDescription("Endereço HTTPS")).assertIsDisplayed()
        composeRule.scrollToDisplayed(hasContentDescription("Código temporário")).assertIsDisplayed()
        composeRule.scrollToDisplayed(hasContentDescription("Parear relógio"))
            .assertIsEnabled()
            .performClick()
        composeRule.runOnIdle { assertTrue(paired) }
    }
}
