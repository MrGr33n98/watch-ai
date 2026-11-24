# language: pt
Funcionalidade: Watch AI — estudo matemático no Galaxy Watch4
  Como estudante utilizando imagens JPG
  Quero receber resoluções verificáveis em etapas no relógio
  Para estudar cálculos e fórmulas com segurança

  Contexto:
    Dado que um remetente autorizado iniciou uma sessão nova
    E que o relógio está pareado e autenticado

  Cenário: Receber quatro fotografias JPG e apresentar quatro questões
    Quando envio quatro arquivos JPG válidos como documentos via WhatsApp
    E confirmo o término do lote
    Então a sessão deve conter quatro questões na ordem de recebimento
    E o relógio deve listar Q1, Q2, Q3 e Q4

  Cenário: Duplicação de eventos do WhatsApp
    Quando o WAHA enviar duas vezes o webhook da mesma fotografia
    Então apenas uma questão deve ser criada para essa mensagem
    E o modelo de visão não deve ser invocado duas vezes para ela

  Cenário: Enunciado ambíguo
    Quando envio JPG com expoentes ilegíveis
    Então a questão deve ficar com estado "needs_review"
    E não deve existir resposta numérica marcada como verificada

  Cenário: Lei de Fourier
    Quando o problema informa k=1,2 W/(m K), A=10 m², deltaT=40 K, L=0,20 m
    Então a solução verificada deve ser 2400 W
    E as etapas devem mostrar fórmula, substituição, cálculo e unidade

  Cenário: Utilização offline
    Dado que já sincronizei uma sessão resolvida
    Quando o Watch4 perde conexão à internet
    Então ainda consigo ler as etapas da sessão salva
    E vejo indicação de modo offline

  Cenário: Proteger sessão de outro usuário
    Quando um relógio não autorizado tenta consultar uma sessão alheia
    Então o servidor não deve fornecer enunciado, imagens ou soluções

  Cenário: Remover sessão e mídias
    Dado que existe uma sessão resolvida
    Quando solicito a remoção da sessão
    Então o servidor deve impedir leitura subsequente dos dados
    E deve agendar expurgo dos JPGs e caches relacionados
