# 🐾 Sistema de Classificação Inteligente de Rações

## 📋 Visão Geral

Sistema completo de análise e classificação automática de produtos de ração através de Inteligência Artificial. Extrai automaticamente características do produto baseado no nome, permitindo análises avançadas de margem, alertas de alergia e comparação por segmento.

## 🎯 Funcionalidades Principais

### 1. Auto-Classificação via IA
- **Porte do Animal**: Pequeno, Médio, Grande, Gigante, Todos
- **Fase/Público**: Filhote, Adulto, Senior, Gestante, Todos
- **Tratamento Especial**: Obesidade, Alergia, Sensível, Digestivo, Urinário, etc.
- **Sabor/Proteína**: Frango, Carne, Peixe, Cordeiro, etc.
- **Peso Embalagem**: Extração automática (15kg, 10.5kg, 500g, etc.)

### 2. Suporte a Múltiplas Classificações
Produtos com "Todas as raças" ou "Todos os portes" são classificados com array de valores, permitindo busca por qualquer critério.

### 3. Sistema de Alertas
Tela dedicada que lista rações sem classificação completa, permitindo:
- Visualizar completude de cada produto (% preenchido)
- Classificar individualmente com IA
- Classificar em lote (até 100 produtos)
- Identificar campos faltantes

### 4. Score de Confiança
Cada classificação retorna score de 0-100% indicando:
- **100%**: Todos os campos identificados
- **75-99%**: Quase completo
- **50-74%**: Incompleto
- **0-49%**: Muito incompleto

## 🗄️ Estrutura do Banco de Dados

### Novos Campos na Tabela `produtos`

```sql
ALTER TABLE produtos ADD COLUMN porte_animal JSONB;
ALTER TABLE produtos ADD COLUMN fase_publico JSONB;
ALTER TABLE produtos ADD COLUMN tipo_tratamento JSONB;
ALTER TABLE produtos ADD COLUMN sabor_proteina VARCHAR(100);
ALTER TABLE produtos ADD COLUMN auto_classificar_nome BOOLEAN DEFAULT TRUE;
```

### Exemplos de Dados

```json
{
  "porte_animal": ["Pequeno", "Médio"],
  "fase_publico": ["Adulto"],
  "tipo_tratamento": ["Obesidade", "Light"],
  "sabor_proteina": "Frango",
  "peso_embalagem": 15.0,
  "auto_classificar_nome": true
}
```

## 🔌 API Endpoints

### 1. Classificar Produto Individual

```http
POST /produtos/{produto_id}/classificar-ia?forcar=true
Authorization: Bearer {token}
```

**Resposta:**
```json
{
  "success": true,
  "produto_id": 123,
  "nome": "Ração Golden Cães Adultos Raças Pequenas Frango 15kg",
  "classificacao": {
    "porte_animal": ["Pequeno"],
    "fase_publico": ["Adulto"],
    "tipo_tratamento": null,
    "sabor_proteina": "Frango",
    "peso_embalagem": 15.0
  },
  "confianca": {
    "completo": true,
    "campos_faltantes": [],
    "score": 100.0
  },
  "campos_atualizados": ["porte_animal", "fase_publico", "sabor_proteina", "peso_embalagem"],
  "mensagem": "Classificação aplicada com sucesso. Score: 100.0%"
}
```

### 2. Classificar em Lote

```http
POST /produtos/classificar-lote?apenas_sem_classificacao=true
Authorization: Bearer {token}
```

**Request Body:**
```json
{
  "produto_ids": [123, 456, 789],  // Opcional, se omitido classifica todos
  "apenas_sem_classificacao": true
}
```

**Resposta:**
```json
{
  "success": true,
  "total_processados": 45,
  "sucessos": 42,
  "erros": 3,
  "detalhes_sucesso": [
    {
      "produto_id": 123,
      "nome": "Golden Adulto Pequeno Porte 15kg",
      "campos_atualizados": ["porte_animal", "fase_publico"],
      "score": 75.0
    }
  ],
  "detalhes_erros": []
}
```

### 3. Listar Alertas (Rações Incompletas)

```http
GET /produtos/racao/alertas?limite=50&offset=0
Authorization: Bearer {token}
```

**Resposta:**
```json
{
  "total": 23,
  "limite": 50,
  "offset": 0,
  "items": [
    {
      "id": 456,
      "codigo": "12345",
      "nome": "Ração Premium Carne",
      "classificacao_racao": "Premium",
      "categoria": "Rações Cães",
      "marca": "Golden",
      "campos_faltantes": ["porte_animal", "fase_publico", "peso_embalagem"],
      "completude": 25.0,
      "auto_classificar_ativo": true
    }
  ]
}
```

## 🤖 Lógica de Classificação

### Padrões Regex (Exemplos)

```python
PORTES = {
    "Pequeno": [r"\bmini\b", r"\bsmall\b", r"\braças pequenas\b"],
    "Médio": [r"\bmédio porte\b", r"\bmedium\b"],
    "Grande": [r"\bgrande porte\b", r"\blarge\b"],
    "Gigante": [r"\bgigante\b", r"\bgiant\b"],
    "Todos": [r"\btodas as raças\b", r"\ball breeds\b"]
}

FASES = {
    "Filhote": [r"\bfilhote\b", r"\bpuppy\b", r"\bjunior\b"],
    "Adulto": [r"\badulto\b", r"\badult\b"],
    "Senior": [r"\bsenior\b", r"\b\+7\b", r"\bidoso\b"]
}

SABORES = {
    "Frango": [r"\bfrango\b", r"\bchicken\b"],
    "Carne": [r"\bcarne\b", r"\bbeef\b"],
    "Peixe": [r"\bpeixe\b", r"\bfish\b", r"\bsalmão\b"]
}
```

### Extração de Peso

```python
# Padrão para kg
match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*kg', nome, re.IGNORECASE)
if match_kg:
    return float(match_kg.group(1).replace(',', '.'))

# Padrão para g (converte para kg)
match_g = re.search(r'(\d+(?:[.,]\d+)?)\s*g\b', nome, re.IGNORECASE)
if match_g:
    return float(match_g.group(1).replace(',', '.')) / 1000
```

## 🎨 Componentes Frontend

### 1. AlertasRacao.jsx
Tela completa com:
- **Stats Cards**: Total alertas, itens na página, completude média
- **Tabela**: Lista rações incompletas com badges de campos faltantes
- **Ações**: Botão "Classificar IA" por linha + "Classificar Todos"
- **Filtros**: Automático (só mostra incompletas)

**Rota**: `/ia/alertas-racao`

### 2. ClassificacaoRacaoIA.jsx
Componente reutilizável para exibir/classificar produto:
- **Header**: Status de completude com cores (verde/amarelo/vermelho)
- **Botão IA**: Classifica produto atual
- **Grid de Campos**: Mostra todos os campos classificados com badges coloridos
- **Tratamentos**: Seção especial para condições médicas

**Uso**:
```jsx
<ClassificacaoRacaoIA 
  produtoId={123}
  nomeProduto="Golden Adulto Pequeno Porte 15kg"
  onAtualizar={() => console.log('Classificação atualizada')}
/>
```

## 📊 Use Cases

### 1. Importação em Massa
```javascript
// Após importar produtos de fornecedor
const response = await API.post('/produtos/classificar-lote', null, {
  params: { apenas_sem_classificacao: true }
});
console.log(`${response.data.sucessos} produtos classificados!`);
```

### 2. Análise de Margem por Segmento
```sql
-- Produtos de porte pequeno com margem baixa
SELECT nome, preco_custo, preco_venda, 
       (preco_venda - preco_custo) / preco_venda * 100 as margem
FROM produtos
WHERE porte_animal @> '["Pequeno"]'
  AND (preco_venda - preco_custo) / preco_venda < 0.30
ORDER BY margem ASC;
```

### 3. Alerta de Alergia no PDV (Futuro)
```javascript
// Cliente tem cachorro com alergia a frango
const cliente = await API.get(`/clientes/${clienteId}`);
const pet = cliente.pets.find(p => p.id === petId);

if (pet.alergias.includes('frango')) {
  const produtosCarrinho = await getCarrinho();
  const alertas = produtosCarrinho.filter(p => 
    p.sabor_proteina?.toLowerCase().includes('frango')
  );
  
  if (alertas.length > 0) {
    mostrarAlerta('⚠️ Atenção: Produto contém frango. Pet tem alergia!');
  }
}
```

### 4. Comparação de Preços por Linha
```sql
-- Comparar rações similares (mesmo porte, fase e sabor)
SELECT marca.nome as marca, 
       produtos.nome, 
       peso_embalagem,
       preco_venda,
       ROUND(preco_venda / peso_embalagem, 2) as preco_por_kg
FROM produtos
INNER JOIN marcas ON produtos.marca_id = marcas.id
WHERE porte_animal @> '["Pequeno"]'
  AND fase_publico @> '["Adulto"]'
  AND sabor_proteina = 'Frango'
ORDER BY preco_por_kg ASC;
```

## 🔐 Permissões

- **produtos.editar**: Permissão necessária para acessar alertas e classificar
- **produtos.view**: Apenas visualizar classificações existentes

## 🚀 Funcionalidades Implementadas (Fases 4-7)

### ✅ Fase 4 - Dashboard de Análise Dinâmica (IMPLEMENTADO)
**Rota Frontend**: `/ia/analise-racoes`  
**Componente**: `DashboardAnaliseRacoes.jsx`

**Features:**
- ✅ **Tabela dinâmica interativa** tipo Excel com filtros multi-select visuais
- ✅ **Badges clicáveis** para selecionar/desmarcar filtros (porte, fase, sabor, marca, peso, linha)
- ✅ **Visualização com cores condicionais** em todas as colunas numéricas:
  - 🟢 Verde: Valores melhores (menor custo, maior margem/lucro)
  - 🟡 Amarelo: Valores intermediários
  - 🔴 Vermelho: Valores piores (maior custo, menor margem/lucro)
- ✅ **Identificação automática dos melhores produtos**:
  - 💰 MENOR CUSTO (melhor preço de compra)
  - ⭐ MELHOR MARGEM % (maior percentual de lucro)
  - 🎯 MELHOR ROI (melhor retorno sobre investimento)
  - 💵 MAIOR LUCRO $ (maior lucro absoluto)
- ✅ **Cards de resumo** mostrando os melhores valores encontrados
- ✅ **Barras de progresso inline** para visualização de margem
- ✅ **Ordenação clicável** por qualquer coluna (nome, custo, venda, margem, ROI, etc.)
- ✅ **Destaque visual** em linhas dos melhores produtos (fundo amarelo)
- ✅ Comparação de preço/kg entre produtos
- ✅ Análise de margem, markup, ROI e lucro absoluto
- ✅ Contador de filtros ativos em tempo real

**Endpoints Criados:**
```
GET  /racoes/analises/resumo - Resumo geral do dashboard
POST /racoes/analises/margem-por-segmento - Análise de margem por segmento
POST /racoes/analises/comparacao-marcas - Comparação de preços entre marcas
GET  /racoes/analises/ranking-vendas - Ranking de produtos mais vendidos
GET  /racoes/analises/opcoes-filtros - Opções disponíveis para filtros
POST /racoes/analises/produtos-comparacao - Produtos filtrados para comparação detalhada
```

**Exemplo de Uso:**
1. Selecione filtros clicando nos badges (ex: Premium, Adulto, Médio+Grande, 15kg)
2. Clique em "Aplicar Filtros"
3. Visualize instantaneamente:
   - Produto com MENOR CUSTO de compra (badge verde 💰)
   - Produto com MELHOR MARGEM % (badge azul ⭐)
   - Produto com MELHOR ROI (badge roxo 🎯)
   - Produto com MAIOR LUCRO $ (badge amarelo 💵)
4. Clique nos cabeçalhos para ordenar por qualquer critério
5. Cores indicam rapidamente quais produtos são mais vantajosos

**Cálculos Exibidos:**
- **Margem %**: `(Venda - Custo) / Venda × 100` - Percentual de lucro sobre o preço de venda
- **ROI %**: `(Lucro / Custo) × 100` - Retorno sobre investimento
- **Lucro R$**: `Venda - Custo` - Valor absoluto de lucro por unidade
- **Custo/kg e Venda/kg**: Para comparação justa entre pesos diferentes

### ✅ Fase 5 - Integração PDV com Alertas (IMPLEMENTADO)
**Componente**: `PDVAlertasRacao.jsx`

**Features:**
- ✅ Alerta automático de alergia ao escanear ração no PDV
  - Verifica pets do cliente
  - Identifica alergenos no produto (sabor/proteína)
  - Mostra pets afetados com detalhes de alergias
- ✅ Sugestão de produtos similares por características
  - Score de similaridade baseado em espécie, porte, fase, sabor
  - Mostra disponibilidade de estoque
  - Preço por kg calculado
- ✅ Cross-sell inteligente baseado em histórico de vendas
  - "Clientes que compraram X também compraram Y"
  - Frequência de compra conjunta
  - Filtrado por disponibilidade

**Endpoints Criados:**
```
POST /pdv/racoes/verificar-alergia/{produto_id} - Verifica alergias
GET  /pdv/racoes/produtos-similares/{produto_id} - Produtos similares
POST /pdv/racoes/cross-sell - Sugestões de cross-sell
GET  /pdv/racoes/produtos-complementares/{produto_id} - Produtos complementares
```

### ✅ Fase 6 - Sugestões Inteligentes (IMPLEMENTADO)
**Rota Frontend**: `/ia/sugestoes-racoes`  
**Componente**: `SugestoesInteligentesRacoes.jsx`

**Features:**
- ✅ Detecção de duplicatas por características
  - Similaridade de nome (Levenshtein)
  - Mesma marca, peso, porte, fase, sabor
  - Score de similaridade e razões
  - Sugestão de ação (mesclar, revisar, manual)
- ✅ Sugestões de padronização de nomes
  - Padronização de unidades (kg, KG, Kg → kg)
  - Remoção de espaços duplicados
  - Capitalização consistente (Title Case)
  - Adição de informações faltantes do classificador
  - Score de confiança por sugestão
- ✅ Identificação de gaps de estoque em segmentos importantes
  - Análise por porte, fase, sabor, linha
  - Cálculo de importância (Alta/Média/Baixa)
  - Faturamento histórico do segmento
  - % de produtos sem estoque
  - Recomendações automáticas
- ✅ Score de saúde do cadastro (0-100)
  - Penalização por duplicatas
  - Penalização por nomes não padronizados
  - Penalização por gaps críticos
  - Classificação: Excelente/Bom/Regular/Crítico

**Endpoints Criados:**
```
GET /racoes/sugestoes/duplicatas - Detecta duplicatas
GET /racoes/sugestoes/padronizar-nomes - Sugestões de padronização
GET /racoes/sugestoes/gaps-estoque - Gaps de estoque por segmento
GET /racoes/sugestoes/relatorio-completo - Relatório consolidado
```

### ✅ Fase 7 - Machine Learning (IMPLEMENTADO)
**Backend**: `ml_racoes_routes.py`

**Features:**
- ✅ Sistema de feedback para aprender com correções manuais
  - Registra quando usuário corrige campo classificado
  - Extrai palavras-chave do nome do produto
  - Armazena histórico de correções
- ✅ Análise de padrões aprendidos
  - Identifica palavras-chave frequentes por campo/valor
  - Calcula confiança baseado em frequência
  - Sugestão de novos regex para classificador
- ✅ Previsão de demanda por segmento
  - Análise de vendas mensais (histórico configurável)
  - Detecção de tendência (crescente/estável/decrescente)
  - Projeção para próximo mês
  - Recomendações de compra/estoque
- ✅ Estatísticas do sistema de ML
  - Total de feedbacks registrados
  - Padrões de alta confiança
  - Status de aprendizado

**Endpoints Criados:**
```
POST /racoes/ml/feedback - Registra feedback de correção
GET  /racoes/ml/padroes-aprendidos - Padrões extraídos dos feedbacks
POST /racoes/ml/aplicar-padroes-aprendidos - Aplica padrões ao classificador (dry-run)
GET  /racoes/ml/previsao-demanda - Previsão de demanda futura
GET  /racoes/ml/estatisticas-ml - Estatísticas do sistema ML
```

**Arquivo de Dados:**
- `data/feedback_classificacao.json` - Armazena feedbacks

## 🚀 Roadmap Futuro (Próximas Fases)

### Fase 8 - Dashboard Executivo
- [ ] Gráficos avançados (Chart.js / Recharts)
- [ ] Exportação de relatórios em PDF/Excel
- [ ] Alertas programados por e-mail
- [ ] Comparação período anterior vs atual

### Fase 9 - IA Avançada
- [ ] Integração com OpenAI para descrições automáticas
- [ ] Reconhecimento de imagem de produtos
- [ ] Chatbot para consultas sobre rações
- [ ] Recomendação personalizada por perfil de cliente

### Fase 10 - Automações
- [ ] Pedido automático ao fornecedor quando estoque baixo
- [ ] Ajuste automático de preços baseado em margem alvo
- [ ] Campanhas automáticas para segmentos em queda
- [ ] Sincronização com marketplace (Mercado Livre, etc)

## 📝 Notas Técnicas

### Backup Antes de Implementar
```bash
# Backup criado em: backups/backup_pre_analise_racoes_20260214_002930
# Inclui: backend/, frontend/, docker-compose.*.yml
```

### Migration
```bash
# Aplicada em: 2026-02-14
docker exec petshop-dev-backend alembic upgrade head
# Revision: 20260214_add_racao_ai_fields -> dae0f14c89a2
```

### Dependências
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL 14+
- **Frontend**: React 18, TailwindCSS, lucide-react, react-hot-toast

### Performance
- Classificação individual: ~50-100ms
- Classificação em lote (100 produtos): ~5-10s
- Query com índice JSONB: <10ms

### Índices PostgreSQL
```sql
CREATE INDEX ix_produtos_sabor_proteina ON produtos(sabor_proteina);
-- GIN indexes criados automaticamente para JSONB
```

## 🐛 Troubleshooting

### Problema: Classificação não identifica peso
**Causa**: Nome não contém padrão "15kg" ou "10.5kg"  
**Solução**: Adicionar peso manualmente ou ajustar nome do produto

### Problema: Auto-classificação não funciona
**Causa**: Campo `auto_classificar_nome` = FALSE  
**Solução**: Usar parâmetro `forcar=true` na chamada da API

### Problema: Campos aparecem como "Não identificado"
**Causa**: Nome do produto não contém palavras-chave reconhecidas  
**Solução**: Adicionar padrões ao dicionário em `classificador_racao.py`

## 📚 Referências

- **Planilhas Excel de Referência**: Análise manual de margens por linha
  - Premium
  - Super Premium
  - Rações Pequeno Porte
  - Filhotes

- **Arquivos Principais**:
  - Backend: `backend/app/classificador_racao.py`
  - Routes: `backend/app/produtos_routes.py` (linhas 3517+)
  - Model: `backend/app/produtos_models.py` (linhas 228-235)
  - Frontend Alertas: `frontend/src/components/AlertasRacao.jsx`
  - Frontend Componente: `frontend/src/components/ClassificacaoRacaoIA.jsx`

## 💡 Contribuindo

Para adicionar novos padrões de classificação, edite:
```python
# backend/app/classificador_racao.py

SABORES = {
    "NovoSabor": [r"\bpalavra1\b", r"\bpalavra2\b"],
    # ...
}
```

Teste com:
```python
from app.classificador_racao import classificar_produto

resultado, confianca = classificar_produto("Nome do Produto Teste")
print(resultado)
```

---

**Desenvolvido com ❤️ para Sistema Pet**  
**Versão**: 1.0.0 (2026-02-14)
