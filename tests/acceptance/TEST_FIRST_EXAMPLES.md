# Test First Examples — não são testes executados

Escrever primeiro estes testes em arquivos reais após scaffolding; execução deve inicialmente falhar (RED).

## Python pytest — Domain (pseudocódigo adaptável)

```python
# apps/api/tests/unit/test_study_session.py
from app.domain.sessions.models import StudySession, TooManyQuestions

def test_only_four_questions_per_session():
    session = StudySession.new(expected_count=4)
    for n in range(4):
        session.attach_question(media_sha=f"sha{n}")
    assert [q.ordinal for q in session.questions] == [1, 2, 3, 4]
    with pytest.raises(TooManyQuestions):
        session.attach_question(media_sha="sha5")

# apps/api/tests/unit/test_verifier.py

def test_fourier_result_is_2400_w(verifier):
    result = verifier.fourier(k=1.2, area=10, delta_t=40, thickness=0.2)
    assert result.value == Decimal("2400")
    assert result.unit == "watt"
    assert result.verified is True
```

## Contrato WAHA (pseudocódigo)

```python
def test_duplicate_waha_event_is_idempotent(client, authorized_event, fake_vision):
    assert client.post('/internal/waha/events', json=authorized_event, headers=AUTH).status_code == 202
    assert client.post('/internal/waha/events', json=authorized_event, headers=AUTH).status_code == 202
    assert db.count('inbound_messages') == 1
    assert fake_vision.call_count <= 1
```

## Android Compose UI (pseudocódigo)

```kotlin
@Test fun questionListShowsFourItemsAndOpensStepOne() {
    composeRule.setContent { QuestionListScreen(fakeStateWithFourQuestions) }
    composeRule.onNodeWithText("Q1").assertExists().performClick()
    composeRule.onNodeWithText("Passo 1 de 4").assertExists()
}
```

## Regras dos testes

- Testes usam objetos fake; não disparar mensagem WhatsApp real em CI.
- Corrigir sintaxe e imports de acordo com layout gerado pelo agente.
- Proibido marcar `skip`/`xfail` para mascarar falha em requisito P0.
- Executar testes reais e coletar logs + hashes antes de mencionar sucesso.
