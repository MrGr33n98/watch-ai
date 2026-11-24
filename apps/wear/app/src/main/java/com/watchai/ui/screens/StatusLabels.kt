package com.watchai.ui.screens

import com.watchai.domain.QuestionStatus
import com.watchai.domain.SessionStatus

internal fun SessionStatus.labelPt(): String = when (this) {
    SessionStatus.CREATED -> "Criada"
    SessionStatus.COLLECTING -> "Recebendo imagens"
    SessionStatus.QUEUED -> "Na fila"
    SessionStatus.PROCESSING -> "Processando"
    SessionStatus.READY -> "Pronta"
    SessionStatus.PARTIAL -> "Parcial"
    SessionStatus.NEEDS_REVIEW -> "Precisa de revisão"
    SessionStatus.FAILED -> "Falhou"
    SessionStatus.CANCELLED -> "Cancelada"
    SessionStatus.EXPIRED -> "Expirada"
}

internal fun QuestionStatus.labelPt(): String = when (this) {
    QuestionStatus.UPLOADED -> "Recebida"
    QuestionStatus.VALIDATING -> "Validando imagem"
    QuestionStatus.INTERPRETING -> "Lendo exercício"
    QuestionStatus.SOLVING -> "Calculando"
    QuestionStatus.READY -> "Pronta"
    QuestionStatus.NEEDS_REVIEW -> "Precisa de revisão"
    QuestionStatus.FAILED -> "Falhou"
}
