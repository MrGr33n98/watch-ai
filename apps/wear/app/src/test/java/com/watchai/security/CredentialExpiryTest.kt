package com.watchai.security

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CredentialExpiryTest {
    @Test
    fun `credential expires at its exact expiry instant`() {
        assertTrue(CredentialExpiry.isExpired(expiresAtMillis = 1_000L, nowMillis = 1_000L))
        assertTrue(CredentialExpiry.isExpired(expiresAtMillis = 999L, nowMillis = 1_000L))
        assertFalse(CredentialExpiry.isExpired(expiresAtMillis = 1_001L, nowMillis = 1_000L))
    }
}
