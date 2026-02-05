# 🐛 PROBLEMAS IDENTIFICADOS - PRODUTOS

**Data:** 09/01/2026  
**Status:** Crítico - Dados não sendo salvos corretamente

---

## ❌ PROBLEMA 1: Campo `origem` nunca é salvo

### Onde deveria estar:
1. **Criação de produto** (linha ~1968 de notas_entrada_routes.py)
2. **Reativação de produto** (linha ~1877 de notas_entrada_routes.py)
3. **Atualização manual** (produtos_routes.py - PUT /produtos/{id})

### Código atual (ERRADO):
```python
# Criação de produto:
novo_produto = Produto(
    ncm=item.ncm,
    cfop=item.cfop,
    cest=item.cest if hasattr(item, 'cest') else None,
    # ❌ FALTA: origem
)

# Reativação:
produto_existente.ncm = item.ncm
produto_existente.cfop = item.cfop
# ❌ FALTA: produto_existente.origem = ???
```

### Impacto:
- Produtos criados/reativados ficam com `origem = None`
- Emissão de NF-e falha (campo obrigatório)
- Usuário preenche manualmente mas não salva

---

## ❌ PROBLEMA 2: Campo `controlar_estoque` não existe

### Frontend envia:
```json
{
  "controlar_estoque": true  // ❌ Campo errado
}
```

### Backend espera:
```python
controle_lote = Column(Boolean, default=False)  // ✅ Campo correto
```

### Resultado:
- Checkbox "Controlar Estoque" não salva
- Produto fica com `controle_lote = False`
- Não permite criar lotes na entrada

---

## ❌ PROBLEMA 3: Frontend não envia `origem` ao editar

### Dados enviados no PUT:
```json
{
  "codigo": "024047.1",
  "nome": "...",
  "ncm": "23099090",
  "origem": null,  // ❌ Sempre null
  "cest": null,
  "cfop": null
}
```

### Possíveis causas:
1. Select de `origem` não vinculado ao state
2. Valor não sendo capturado do formulário
3. Valor zerado antes de enviar

---

## ❌ PROBLEMA 4: Tela branca ao clicar nos boxes

### Sintoma:
Ao clicar em checkboxes de seleção de produtos na página Produtos.jsx

### Possíveis causas:
1. Erro de JavaScript não capturado
2. State inconsistente
3. Callback de seleção quebrado
4. Departamentos retornando 404 (visto nos logs)

### Log do erro:
```
INFO: 127.0.0.1:53379 - "GET /departamentos HTTP/1.1" 404 Not Found
```

---

## ❌ PROBLEMA 5: Dados salvos não persistem após reload

### Sintoma:
1. Usuário preenche: SKU, Categoria, Marca, Departamento
2. Clica em "Atualizar"
3. Backend recebe e salva (confirmado no log)
4. Ao voltar à tela, campos estão vazios

### Log mostra (Backend):
```
DEBUG ATUALIZAR PRODUTO #8
Dados recebidos: {'categoria_id': 1, 'marca_id': None, 'departamento_id': 1, ...}
Atualizando categoria_id = 1
Atualizando marca_id = None  // ❌ Deveria ter valor
Atualizando departamento_id = 1
```

### Possíveis causas:
1. Frontend não está lendo resposta corretamente
2. Cache desatualizado
3. Endpoint GET retornando dados antigos
4. Selects não preenchendo com IDs, mas com objetos

---

## 🔍 INVESTIGAÇÕES NECESSÁRIAS

### 1. Verificar schema do modelo Produto
```sql
PRAGMA table_info(produtos);
```
Confirmar se campos existem:
- `origem` VARCHAR(1)
- `controle_lote` BOOLEAN
- `categoria_id` INTEGER
- `marca_id` INTEGER
- `departamento_id` INTEGER

### 2. Verificar endpoint GET /produtos/{id}
Confirmar se retorna:
```json
{
  "id": 8,
  "origem": "0",  // Deve ter valor
  "categoria_id": 1,
  "marca_id": 2,
  "departamento_id": 3
}
```

### 3. Verificar formulário frontend
- Select de `origem` está vinculado?
- `onChange` está atualizando state?
- State está sendo enviado no PUT?

### 4. Verificar endpoint /departamentos
Por que retorna 404?
- Rota existe?
- Nome correto é `/produtos/departamentos`?

---

## ✅ SOLUÇÕES NECESSÁRIAS

### 1. Adicionar `origem` em 3 lugares:
1. Criar produto (notas_entrada_routes.py ~1968)
2. Reativar produto (notas_entrada_routes.py ~1877)
3. Atualizar produto (produtos_routes.py)

### 2. Corrigir nome do campo:
- Frontend: mudar `controlar_estoque` para `controle_lote`
- Ou Backend: aceitar ambos os nomes (alias)

### 3. Debugar formulário frontend:
- Adicionar `console.log` nos onChange
- Verificar se valores estão no state antes do submit
- Confirmar se PUT está enviando os dados

### 4. Corrigir rota de departamentos:
- Verificar se é `/departamentos` ou `/produtos/departamentos`
- Adicionar rota se não existir

---

## 📝 ARQUIVOS PARA CORRIGIR

1. `backend/app/notas_entrada_routes.py` (linhas 1877, 1968)
2. `backend/app/produtos_routes.py` (endpoint PUT /produtos/{id})
3. `frontend/src/pages/ProdutoForm.jsx` (ou equivalente)
4. `frontend/src/pages/Produtos.jsx` (checkbox seleção)
5. `backend/app/produtos_routes.py` (rota /departamentos?)

---

**Prioridade:** 🔴 CRÍTICA  
**Impacto:** Dados perdidos, NF-e não emite, UX ruim  
**Tempo estimado de correção:** 3-4 horas
