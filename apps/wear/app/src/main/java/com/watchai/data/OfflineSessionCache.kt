package com.watchai.data

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.io.IOException
import java.util.UUID

interface OfflineSessionCache {
    fun readSessionList(): String?
    fun writeSessionList(json: String)
    fun readSession(sessionId: String): String?
    fun writeSession(sessionId: String, json: String)
    fun readQuestion(sessionId: String, ordinal: Int): String?
    fun writeQuestion(sessionId: String, ordinal: Int, json: String)
    fun deleteSession(sessionId: String)
    fun clear()
}

class AtomicSessionFileCache(context: Context) : OfflineSessionCache {
    private val root = File(context.applicationContext.noBackupFilesDir, "watch-ai-offline-v1")

    init {
        if (!root.exists() && !root.mkdirs()) throw IOException("Cannot create private cache directory")
        root.setReadable(false, false)
        root.setWritable(false, false)
        root.setExecutable(false, false)
        root.setReadable(true, true)
        root.setWritable(true, true)
        root.setExecutable(true, true)
    }

    override fun readSessionList(): String? = read(File(root, "sessions.json"))

    override fun writeSessionList(json: String) = write(File(root, "sessions.json"), json)

    override fun readSession(sessionId: String): String? = read(sessionFile(sessionId))

    override fun writeSession(sessionId: String, json: String) = write(sessionFile(sessionId), json)

    override fun readQuestion(sessionId: String, ordinal: Int): String? = read(questionFile(sessionId, ordinal))

    override fun writeQuestion(sessionId: String, ordinal: Int, json: String) =
        write(questionFile(sessionId, ordinal), json)

    override fun deleteSession(sessionId: String) {
        val normalizedId = normalizeUuid(sessionId)
        AtomicFile(File(root, "session_$normalizedId.json")).delete()
        (1..4).forEach { ordinal ->
            AtomicFile(File(root, "question_${normalizedId}_$ordinal.json")).delete()
        }
        val cachedSessions = readSessionList() ?: return
        runCatching {
            val remaining = StudyJsonCodec.decodeSessionList(cachedSessions)
                .filterNot { it.id.equals(normalizedId, ignoreCase = true) }
            writeSessionList(StudyJsonCodec.encodeSessionList(remaining))
        }.onFailure {
            AtomicFile(File(root, "sessions.json")).delete()
        }
    }

    override fun clear() {
        root.listFiles()?.forEach { file ->
            if (file.isFile) AtomicFile(file).delete()
        }
    }

    private fun sessionFile(sessionId: String): File {
        val normalizedId = normalizeUuid(sessionId)
        return File(root, "session_$normalizedId.json")
    }

    private fun questionFile(sessionId: String, ordinal: Int): File {
        require(ordinal in 1..4) { "Question ordinal must be between one and four" }
        val normalizedId = normalizeUuid(sessionId)
        return File(root, "question_${normalizedId}_$ordinal.json")
    }

    private fun read(file: File): String? {
        val atomic = AtomicFile(file)
        return try {
            if (!file.exists()) return null
            if (file.length() > MAX_ENTRY_BYTES) {
                atomic.delete()
                return null
            }
            atomic.readFully().toString(Charsets.UTF_8)
        } catch (_: IOException) {
            atomic.delete()
            null
        }
    }

    private fun write(file: File, value: String) {
        val bytes = value.toByteArray(Charsets.UTF_8)
        require(bytes.size <= MAX_ENTRY_BYTES) { "Cached response exceeds the one MiB limit" }
        val atomic = AtomicFile(file)
        val stream = atomic.startWrite()
        try {
            stream.write(bytes)
            atomic.finishWrite(stream)
        } catch (error: Exception) {
            atomic.failWrite(stream)
            throw error
        }
    }

    private fun normalizeUuid(value: String): String {
        val normalized = runCatching { UUID.fromString(value).toString() }
            .getOrElse { throw IllegalArgumentException("Session identifier must be a UUID", it) }
        require(value.equals(normalized, ignoreCase = true)) { "Session identifier must be canonical" }
        return normalized
    }

    private companion object {
        const val MAX_ENTRY_BYTES = 1024 * 1024
    }
}
