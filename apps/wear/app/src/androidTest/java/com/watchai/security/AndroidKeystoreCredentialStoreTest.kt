package com.watchai.security

import androidx.test.core.app.ApplicationProvider
import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidKeystoreCredentialStoreTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val store = AndroidKeystoreCredentialStore(context, "credential_store_test")

    @Test
    fun `credential round trips encrypted and expires`() {
        val credential = DeviceCredential("device-1", "opaque-test-token", System.currentTimeMillis() + 60_000)

        store.save(credential)

        assertEquals(credential, store.read())
        assertNull(store.read(nowEpochMillis = credential.expiresAtEpochMillis))
    }

    @Test
    fun `clear removes stored credential and key`() {
        store.save(DeviceCredential("device-1", "opaque-test-token", System.currentTimeMillis() + 60_000))

        store.clear()

        assertNull(store.read())
    }
}
