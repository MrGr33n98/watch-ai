package com.watchai.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class DeviceCredential(
    val deviceId: String,
    val accessToken: String,
    val expiresAtEpochMillis: Long,
)

interface CredentialStore {
    fun save(credential: DeviceCredential)
    fun read(nowEpochMillis: Long = System.currentTimeMillis()): DeviceCredential?
    fun clear()
}

object CredentialExpiry {
    fun isExpired(expiresAtMillis: Long, nowMillis: Long): Boolean = expiresAtMillis <= nowMillis
}

class AndroidKeystoreCredentialStore(
    context: Context,
    preferencesName: String = "watch_credentials",
) : CredentialStore {
    private val preferences = context.applicationContext.getSharedPreferences(preferencesName, Context.MODE_PRIVATE)

    @Synchronized
    override fun save(credential: DeviceCredential) {
        require(credential.accessToken.isNotBlank()) { "Access token is required" }
        require(!CredentialExpiry.isExpired(credential.expiresAtEpochMillis, System.currentTimeMillis())) {
            "Expired credentials cannot be stored"
        }
        val payload = JSONObject()
            .put("device_id", credential.deviceId)
            .put("access_token", credential.accessToken)
            .put("expires_at", credential.expiresAtEpochMillis)
            .toString()
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val ciphertext = cipher.doFinal(payload.toByteArray(Charsets.UTF_8))
        preferences.edit()
            .putString(KEY_IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString(KEY_VALUE, Base64.encodeToString(ciphertext, Base64.NO_WRAP))
            .apply()
    }

    @Synchronized
    override fun read(nowEpochMillis: Long): DeviceCredential? {
        val ivText = preferences.getString(KEY_IV, null) ?: return null
        val valueText = preferences.getString(KEY_VALUE, null) ?: return clearAndReturnNull()
        return try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                GCMParameterSpec(GCM_TAG_BITS, Base64.decode(ivText, Base64.NO_WRAP)),
            )
            val payload = JSONObject(
                cipher.doFinal(Base64.decode(valueText, Base64.NO_WRAP)).toString(Charsets.UTF_8),
            )
            val credential = DeviceCredential(
                deviceId = payload.getString("device_id"),
                accessToken = payload.getString("access_token"),
                expiresAtEpochMillis = payload.getLong("expires_at"),
            )
            if (credential.accessToken.isBlank() ||
                CredentialExpiry.isExpired(credential.expiresAtEpochMillis, nowEpochMillis)
            ) {
                clearAndReturnNull()
            } else {
                credential
            }
        } catch (_: Exception) {
            clearAndReturnNull()
        }
    }

    @Synchronized
    override fun clear() {
        preferences.edit().clear().apply()
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        if (keyStore.containsAlias(KEY_ALIAS)) keyStore.deleteEntry(KEY_ALIAS)
    }

    private fun clearAndReturnNull(): DeviceCredential? {
        clear()
        return null
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "watch-ai-device-token-v1"
        const val KEY_IV = "credential_iv"
        const val KEY_VALUE = "credential_ciphertext"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_TAG_BITS = 128
    }
}
