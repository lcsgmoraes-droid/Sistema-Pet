# Testes de Domínio - VendaService

## 📋 Visão Geral

Testes puros de domínio para o `VendaService`, focados em **regras de negócio** e **eventos de domínio**, **SEM** usar FastAPI, rotas ou banco de dados real.

## 🎯 Objetivos

✅ Testar lógica de negócio isoladamente  
✅ Validar emissão de eventos de domínio  
✅ Garantir transações atômicas  
✅ Verificar regras de validação  
✅ Testes rápidos (< 1 segundo)  
✅ Alta legibilidade e manutenibilidade  

## 📁 Estrutura

```
backend/tests/domain/
├── __init__.py                      # Inicialização do módulo
├── conftest.py                      # Fixtures e mocks reutilizáveis
├── test_venda_service.py            # Testes de casos felizes
├── test_venda_regras_negocio.py     # Testes de regras de negócio
└── test_venda_eventos.py            # Testes de eventos de domínio
```

## 🧪 Categorias de Testes

### 1. Casos Felizes (`test_venda_service.py`)

Testa os fluxos principais do sistema:

- ✅ **Criar venda simples**: 1 item, sem entrega
- ✅ **Criar venda com múltiplos itens**: Cálculo correto de totais
- ✅ **Criar venda com taxa de entrega**: Entrega incluída no total
- ✅ **Finalizar venda com dinheiro**: Pagamento completo
- ✅ **Finalizar venda com pagamento parcial**: Status `baixa_parcial`
- ✅ **Cancelar venda aberta**: Estorno de estoque
- ✅ **Cancelar venda finalizada**: Estorno completo

### 2. Regras de Negócio (`test_venda_regras_negocio.py`)

Valida restrições e validações:

#### Criação de Venda:
- ❌ Não criar venda sem itens
- ❌ Rollback em caso de erro

#### Finalização de Venda:
- ❌ Não finalizar sem caixa aberto
- ❌ Não finalizar venda inexistente
- ❌ Não finalizar venda já finalizada
- ❌ Não finalizar venda cancelada
- ❌ Não finalizar sem pagamentos
- ❌ Não pagar venda já totalmente paga
- ❌ Crédito requer cliente vinculado
- ❌ Crédito insuficiente impede pagamento

#### Cancelamento de Venda:
- ❌ Não cancelar venda inexistente
- ❌ Não cancelar venda já cancelada
- ❌ Rollback em caso de erro

#### Segurança:
- 🔒 Usuário só pode finalizar suas próprias vendas
- 🔒 Usuário só pode cancelar suas próprias vendas

### 3. Eventos de Domínio (`test_venda_eventos.py`)

Valida emissão e processamento de eventos:

#### VendaCriada:
- 📢 Evento emitido com dados corretos
- 📢 Metadados incluídos (taxa, subtotal)
- 📢 Emitido APÓS commit
- ⚠️ Erro em evento não aborta criação

#### VendaFinalizada:
- 📢 Evento emitido ao finalizar
- 📢 Lista de formas de pagamento incluída

#### VendaCancelada:
- 📢 Evento emitido ao cancelar
- 📢 Metadados de estornos incluídos
- ⚠️ Erro em evento não aborta cancelamento

#### Handlers:
- 🔌 Handler pode ser registrado e chamado
- 🔌 Erro em handler não impede outros handlers
- 🔌 Múltiplos handlers executados em ordem

## 🏃 Como Executar

### Executar todos os testes de domínio:

```bash
cd backend
pytest tests/domain/ -v
```

### Executar categoria específica:

```bash
# Casos felizes
pytest tests/domain/test_venda_service.py -v

# Regras de negócio
pytest tests/domain/test_venda_regras_negocio.py -v

# Eventos
pytest tests/domain/test_venda_eventos.py -v
```

### Executar teste específico:

```bash
pytest tests/domain/test_venda_service.py::TestCriarVenda::test_criar_venda_simples_sucesso -v
```

### Com cobertura:

```bash
pytest tests/domain/ --cov=app.vendas.service --cov-report=html
```

## 🛠️ Fixtures Disponíveis (conftest.py)

### Mocks de Serviços:
- `mock_db_session`: Mock do SQLAlchemy Session
- `mock_estoque_service`: Mock do EstoqueService
- `mock_caixa_service`: Mock do CaixaService
- `mock_contas_receber_service`: Mock do ContasReceberService
- `mock_event_dispatcher`: Mock do EventDispatcher

### Dados Fake:
- `fake_venda_data`: Payload para criar venda
- `fake_venda_model`: Mock de modelo Venda
- `fake_cliente_model`: Mock de modelo Cliente
- `fake_pagamentos`: Lista de pagamentos

### Helpers:
- `assert_evento_publicado`: Helper para validar eventos

## 📊 Exemplos de Uso

### Teste Simples:

```python
def test_criar_venda_simples(
    mock_db_session,
    mock_event_dispatcher,
    fake_venda_data
):
    # ACT
    resultado = VendaService.criar_venda(
        payload=fake_venda_data,
        user_id=1,
        db=mock_db_session
    )
    
    # ASSERT
    assert resultado['status'] == 'aberta'
    assert len(mock_event_dispatcher.eventos_publicados) == 1
```

### Validar Evento:

```python
def test_evento_venda_criada(mock_event_dispatcher):
    # ... criar venda ...
    
    evento = mock_event_dispatcher.eventos_publicados[0]
    assert isinstance(evento, VendaCriada)
    assert evento.venda_id == 100
    assert evento.total == 100.0
```

### Validar Erro:

```python
def test_nao_criar_venda_sem_itens(mock_db_session):
    payload = {'cliente_id': 1, 'itens': []}
    
    with pytest.raises(HTTPException) as exc:
        VendaService.criar_venda(
            payload=payload,
            user_id=1,
            db=mock_db_session
        )
    
    assert exc.value.status_code == 400
```

## ✅ Checklist de Qualidade

- [x] Testes não acessam banco real
- [x] Testes não usam FastAPI/TestClient
- [x] Testes não dependem de servidor rodando
- [x] Testes são independentes (podem rodar em qualquer ordem)
- [x] Testes são rápidos (< 1s cada)
- [x] Mocks isolam dependências externas
- [x] Eventos de domínio validados
- [x] Regras de negócio cobertas
- [x] Casos de erro validados
- [x] Segurança validada

## 🎓 Princípios Aplicados

### DDD (Domain-Driven Design):
- ✅ Testes focados em lógica de domínio
- ✅ Eventos de domínio validados
- ✅ Regras de negócio isoladas

### Clean Architecture:
- ✅ Independência de frameworks
- ✅ Independência de infraestrutura
- ✅ Testabilidade

### SOLID:
- ✅ **S**ingle Responsibility: Cada teste valida 1 coisa
- ✅ **D**ependency Inversion: Depende de abstrações (mocks)

## 📈 Próximos Passos

1. Adicionar testes de integração (com banco real)
2. Adicionar testes de performance
3. Adicionar testes de carga
4. Cobertura de código > 90%

## 📝 Notas Importantes

> ⚠️ **Estes são TESTES DE DOMÍNIO**  
> Não testam infraestrutura, rotas HTTP ou banco de dados.  
> Para testes de integração completos, criar pasta `tests/integration/`.

> 💡 **Eventos não abortam operações**  
> Erros ao emitir eventos são logados mas não abortam a transação principal.

> 🔒 **Isolamento de usuário**  
> Todos os testes validam que um usuário só acessa seus próprios dados.

## 🤝 Contribuindo

Para adicionar novos testes:

1. Identifique a categoria (caso feliz, regra ou evento)
2. Use as fixtures do `conftest.py`
3. Siga o padrão AAA (Arrange, Act, Assert)
4. Documente o cenário e expectativa
5. Execute `pytest` para validar

---

**Autor**: Sistema Pet Shop - Refatoração DDD  
**Data**: 23/01/2026  
**Versão**: 1.0.0
