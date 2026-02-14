# 📝 Changelog - Sistema de Padronização de Nomes

## [1.1.0] - 2026-02-14

### 🎉 Adicionado
- **Sistema Completo de Padronização de Nomes**
  - Algoritmo de reconstrução estruturada: `Ração [Marca] [Espécie] [Fase] [Porte] [Sabor] [Tratamento] [Peso]`
  - Inclusão de espécie (Cães/Gatos) usando campo `especies_indicadas`
  - Inclusão de porte com prefixo "Raças" (ex: "Raças Pequenas")
  - Inclusão de tratamento (Light, Hipoalergênico) como campo opcional
  - Sistema de confiança (0-100%) para cada sugestão
  - Sugestões filtradas por confiança mínima (≥50%)

- **Edição de Sugestões Antes de Aplicar**
  - Botão "Editar" para tornar sugestão editável
  - Campo de input com destaque visual (borda azul)
  - Botão "Cancelar Edição" para descartar mudanças
  - Botão "Aplicar Edição" dinâmico (muda texto conforme estado)
  - Estado `nomesEditados` para controlar edições por produto

- **Seleção Visual de Duplicatas**
  - Cards clicáveis para escolher qual produto manter
  - Feedback visual: verde (mantém) vs vermelho (remove)
  - Ícones checkmark (✓) e X nos cards
  - Status badges: "ESTE PRODUTO SERÁ MANTIDO" vs "Este produto será inativado"
  - Botão "Confirmar Mesclagem" só habilitado após seleção
  - Estado `produtosSelecionados` para controlar seleções

- **Persistência de Duplicatas Ignoradas**
  - Nova tabela `duplicatas_ignoradas` no banco
  - Registra pares que usuário marcou como "não são duplicatas"
  - Duplicatas ignoradas não reaparecem ao atualizar
  - Filtro automático na query de detecção

### 🔧 Corrigido
- **Bug Crítico 500 no Endpoint de Atualização**
  - Corrigido erro `NameError: name 'tenant_id' is not defined`
  - Adicionada extração de `tenant_id` de `user_and_tenant`
  - Endpoint PATCH `/produtos/{produto_id}` agora funcional

- **Campo Incorreto de Espécie**
  - Mudado de `especie_compativel` para `especies_indicadas`
  - Agora reflete corretamente o campo da tela de edição

### 🗄️ Banco de Dados
- **Nova Tabela**: `duplicatas_ignoradas`
  - Colunas: id, tenant_id, produto_id_1, produto_id_2, usuario_id, data_ignorado
  - Unique constraint em (tenant_id, produto_id_1, produto_id_2)
  - 4 índices criados para otimização

### 📁 Arquivos Modificados
```
backend/app/sugestoes_racoes_routes.py (linhas 376-480)
backend/app/produtos_routes.py (linha 2197)
backend/app/duplicatas_ignoradas_models.py (novo)
frontend/src/components/SugestoesInteligentesRacoes.jsx (múltiplas seções)
```

### 🎯 Exemplos de Transformação
```
Antes:  "Premier Cães Adultos Raças Médias e Grandes Frango 15kg"
Depois: "Ração Premier Cães Adultos Raças Médias e Grandes Frango 15kg"

Antes:  "Golden Formula Cães Adultos Frango e Arroz 15kg"
Depois: "Ração Golden Cães Adultos Raças Médias e Grandes Frango 15kg"

Antes:  "SPECIAL DOG AD PEQ PORTE 10.1KG"
Depois: "Ração Special Dog Cães Adultos Raças Pequenas Frango 10.1kg"
```

---

## [1.0.0] - 2026-02-14 (Pré-Padronização)

### 🎉 Implementado
- Sistema de Classificação Inteligente de Rações
- Dashboard de Análise Dinâmica
- Integração PDV com Alertas
- Sugestões Inteligentes (duplicatas, gaps de estoque)
- Machine Learning (feedback e previsão de demanda)

---

**Backup Criado**: `backups/backup_pos_padronizacao_nomes_20260214_172530`
