# Planejamento — Módulo Veterinário (Sistema Pet)

> **Versão:** 2.1 — Março 2026  
> **Status:** Em desenvolvimento — Fase 1 e 2 parcialmente implementadas

---

## 🗂️ STATUS GERAL DA IMPLEMENTAÇÃO

> Legenda: ✅ Completo | 🔶 Parcial (estrutura pronta, falta detalhe) | ❌ Pendente

### Infraestrutura e Banco de Dados
| Item | Status | Observação |
|---|---|---|
| 15 tabelas `vet_*` criadas no banco (DEV) | ✅ | Migração `v1a2b3c4d5e6` aplicada |
| Backend: `veterinario_models.py` | ✅ | Todos os modelos SQLAlchemy |
| Backend: `veterinario_routes.py` | ✅ | Rotas CRUD em `/vet` |
| Backend: router registrado em `main.py` | ✅ | `/vet/*` respondendo `403` (auth OK) |
| Migrações intermediárias corrigidas | ✅ | `60a7b78b30b8` stamped + 3 corrigidas |

### Frontend — Telas criadas
| Tela | Status | Observação |
|---|---|---|
| `VetDashboard.jsx` — painel com KPIs e agenda do dia | ✅ | Integrado com `/vet/dashboard` |
| `VetConsultas.jsx` — lista paginada de consultas | ✅ | Filtros por data e status |
| `VetConsultaForm.jsx` — formulário de consulta (3 etapas) | 🔶 | ✅ Prescrições implementadas (`criarPrescricao`, `finalizarConsulta`); falta IA integrada e cálculo automático de dose por peso |
| `VetAgenda.jsx` — calendário dia/semana | 🔶 | ✅ Criação de agendamento implementada (`criarAgendamento`); falta integração com push notifications |
| `VetVacinas.jsx` — registro de vacinas | 🔶 | ✅ Alerta de vencimento implementado (`vacinasVencendo`); falta calendário preventivo por espécie e carteirinha digital |
| `VetInternacoes.jsx` — fichas de internação | 🔶 | ✅ Criação/alta/evolução/procedimento implementados; falta alertas automáticos de horário e gráficos de evolução |
| `VetCatalogo.jsx` — catálogos (medicamentos e procedimentos) | 🔶 | Tabela com CRUD; falta banco de bulas completo e vinculação de insumos |
| `vetApi.js` — helper Axios para todas as rotas `/vet` | ✅ | Cobre todos os endpoints |
| Rotas em `App.jsx` | ✅ | `/vet/*` mapeadas |
| Menu lateral em `Layout.jsx` | ✅ | Sub-itens do módulo veterinário |

---

---

## 1. Visão Geral e Filosofia

O módulo veterinário do Sistema Pet não é apenas um prontuário eletrônico.  
É um sistema **integrado e inteligente**, que conecta:

- A loja (venda de produtos, banho e tosa)
- O veterinário (clínica, internação, procedimentos)
- O tutor (via aplicativo)
- A IA (que lê tudo e ajuda em tempo real)

**Princípio central:** toda informação clínica deve ser **estruturada** — campos reais no banco, não texto livre. Isso permite que a IA leia, filtre, alerte e sugira de forma precisa.

---

## 2. Arquitetura Multi-Tenant — Solução para o Veterinário Parceiro

O multi-tenant resolve de forma elegante o problema do veterinário vinculado vs. parceiro. São dois modelos operacionais completamente diferentes, cobertos pela mesma plataforma.

### Cenário 1 — Veterinário Funcionário (vinculado)

Veterinário faz parte da empresa. Tudo acontece dentro do **mesmo tenant**:

```
Empresa (tenant único)
 ├── ERP
 ├── Estoque
 ├── Vendas / PDV
 ├── Banho e Tosa
 └── Veterinário
```

- Estoque compartilhado (ou separado por setor "Veterinário", configurável)
- Financeiro unificado — procedimentos entram na caixa da empresa
- Agenda integrada na agenda geral da empresa
- Permissões: veterinário tem perfil próprio com acesso restrito ao módulo dele
- A loja vê tudo — prontuários, exames, agenda

### Cenário 2 — Veterinário Parceiro (tenant próprio)

Veterinário **vira um tenant independente** que se relaciona com a loja:

```
Pet Shop (tenant A)          Veterinário Parceiro (tenant B)
 ├── estoque A                ├── estoque B
 ├── financeiro A             ├── financeiro B
 ├── vendas A                 ├── prontuários B
 │                            ├── agenda B
 │         integração         └── financeiro B
 └─────────────────────────────────────────────
```

- **Tenant B** contrata o sistema separadamente — paga mensalidade própria
- Módulos liberados: Veterinário, Estoque próprio, Financeiro próprio, Agenda, App
- **Prontuário pertence ao veterinário** (tenant B) — correto juridicamente (LGPD + CFV)
- A loja (tenant A) enxerga apenas o resumo do pet (vacinas, alergias, peso) — não acessa prontuário completo
- O tutor (cliente) não precisa saber de tenants — o app agrega dados dos dois

### 2.1 Tabela de Vínculo entre Tenants

Uma tabela leve que define a relação entre os dois tenants:

```sql
vet_partner_link
  id
  empresa_tenant_id    -- tenant da loja
  vet_tenant_id        -- tenant do veterinário
  tipo_relacao         -- 'parceiro' | 'funcionario'
  comissao_empresa_pct -- ex: 20.00 (20% para a loja) — nullable
  ativo
  criado_em
```

### 2.2 Dados Compartilhados vs. Dados Isolados

| Dado | Modelo | Quem acessa |
|---|---|---|
| Dados básicos do pet (peso, vacinas, alergias) | Compartilhado (pet core) | Ambos os tenants |
| Prontuário, diagnósticos, exames | Isolado no tenant do vet | Só o veterinário |
| Histórico de compras, banho | Isolado no tenant da loja | Só a loja |
| Agendamentos | Evento enviado entre tenants | Cada um gerencia o seu |
| Financeiro | Completamente isolado | Cada um o seu |

### 2.3 Catálogo Global de Produtos e Medicamentos

Para evitar duplicação, o catálogo de produtos e medicamentos é **global** no sistema:

```
global_products (catálogo compartilhado)
  id, nome, principio_ativo, concentracao...

tenant_stock (estoque por tenant)
  tenant_id, product_id, quantidade, estoque_minimo...
```

- Produto existe uma vez no catálogo global
- Cada tenant tem seu próprio saldo de estoque
- Veterinário parceiro tem `tenant_stock` independente
- **Transferência entre tenants** é possível: loja pode transferir insumos para o veterinário parceiro (ou vender)

### 2.4 Comissão Automática (diferencial de negócio)

Quando o veterinário for parceiro com comissão configurada:

```
Exemplo:
  procedimento: Consulta
  valor cobrado: R$ 150,00
  comissao_empresa: 20%

Sistema gera automaticamente:
  → R$ 120,00 → financeiro tenant B (veterinário)
  → R$ 30,00  → financeiro tenant A (empresa/loja)
```

- Configurável por tipo de procedimento ou porcentagem geral
- Relatório mensal de repasse para a loja
- Relatório de receitas líquidas para o veterinário
- Isso elimina planilhas manuais e disputas de valor

### 2.5 Configuração no Tenant

```
Configurações > Veterinário

MODELO OPERACIONAL
  ( ) Veterinário vinculado (mesmo tenant)
  ( ) Veterinário parceiro (tenant próprio)

FATURAMENTO (modo vinculado)
  [ ] Procedimentos veterinários somam ao financeiro da empresa

COMISSÃO (modo parceiro)
  Percentual para a empresa: ____%
  Aplicar sobre: ( ) todos os procedimentos  ( ) por tipo

ESTOQUE
  [ ] Veterinário usa estoque próprio separado
  [ ] Alertar quando insumo atingir estoque mínimo

ALERTAS
  [ ] Ativar alerta de alergias na PDV
  [ ] Ativar alerta de alergias no agendamento de Banho/Tosa
  [ ] Ativar alerta de restrições alimentares na PDV
  [ ] Compartilhar dados básicos do pet com veterinário parceiro
```

---

## 3. Integração com Módulos Existentes

### 3.1 Cadastro de Pessoas
- **Reaproveita 100%** o cadastro já existente
- Campo adicional no cadastro do cliente: `Tem pet cadastrado: Sim/Não`
- Ao abrir a ficha do cliente na PDV ou Banho/Tosa → ícone de alerta se houver alergia registrada no pet

### 3.2 Cadastro de Pet (expandido)
O cadastro de pet atual ganha campos clínicos estruturados — **não texto livre**:

#### Informações Básicas (já existem ou simples)
- Nome, espécie, raça, sexo, data de nascimento, cor/pelagem
- Microchip, registro de pedigree
- Foto do animal

#### Campos Clínicos Estruturados (novos — dados reais no banco)
| Campo | Tipo | Por quê estruturado |
|---|---|---|
| Alergias | Array (lista) | IA pode alertar na PDV |
| Condições crônicas | Array | IA menciona em qualquer contexto |
| Tipo sanguíneo | Enum | Importante em cirurgias |
| Castrado | Boolean + data | Histórico |
| Microchipado | Boolean + nº | Rastreamento |
| Peso atual | Float | Calculadora de doses usa isso |
| Histórico de vacinas | Tabela separada | Calendário vacinal |
| Histórico de vermifugação | Tabela separada | Alertas |
| Restrições alimentares | Array | Alerta na PDV ao comprar ração |
| Medicamentos em uso | Array | IA alerta interações |

### 3.3 Cadastro de Produtos
- Reaproveita 100% o cadastro existente
- Campo adicional: `Categoria veterinária` (medicamento, insumo cirúrgico, vacina, antiparasitário...)
- Campo: `Princípio ativo` — permite que IA detecte interações medicamentosas

---

## 4. Módulos do Veterinário

### 4.1 Agenda Veterinária
- Calendário visual (dia/semana/mês)
- Tipos de agendamento: Consulta, Retorno, Cirurgia, Vacinação, Exame, Banho/Tosa (quando integrado)
- Status: Agendado, Confirmado, Em atendimento, Concluído, Faltou, Cancelado
- Bloqueio de horários (veterinário de folga, cirurgia em andamento)
- **Integração app:** tutor vê seus agendamentos, pode confirmar ou solicitar cancelamento
- **Alerta automático via push notification pelo app** (gratuito — sem custo adicional de WhatsApp)
  - Lembrete 24h antes do agendamento
  - Lembrete 1h antes
  - Confirmação quando o atendimento for concluído
  - Notificação: "Seu pet foi medicado às 14h30" (durante internação)
- Ao confirmar agendamento → sistema verifica alergias do pet e avisa o vet
- **Métricas de performance:** sistema registra hora de início e fim de cada consulta → calcula tempo médio de atendimento e taxa de retorno por veterinário
- **Integração multi-tenant:** quando veterinário for parceiro, agendamento feito na loja gera evento `appointment.created` que é enviado ao tenant do veterinário

### 4.2 Prontuário Eletrônico (Consultas)
Ficha clínica com campos estruturados:

**Sinais Vitais (campos numéricos reais):**
- Temperatura (°C)
- Frequência cardíaca (bpm)
- Frequência respiratória (mrm)
- Peso na consulta (kg) — alimenta automaticamente a curva de peso
- TPC (tempo de preenchimento capilar)
- Mucosas (enum: normocoradas, hipocoradas, hipercoradas, ictéricas, cianóticas)
- Nível de dor (escala 0-10)
- Score corporal (escala 1-9)

**Anamnese e Exame:**
- Motivo da consulta (texto)
- Anamnese (texto)
- Exame físico por sistemas (campos separados: cardiovascular, respiratório, digestório, pele, locomotor...)
- Sintomas (seleção múltipla de lista + opção livre)

**Diagnóstico e Conduta:**
- Diagnóstico principal
- Diagnósticos diferenciais
- Sugestão da IA (campo separado, não mistura com diagnóstico humano)
- Conduta / tratamento
- Retorno em X dias (automático já cria o agendamento de retorno)
- Observações

### 4.3 Banco de Bulas / Medicamentos
Cadastro completo de medicamentos:
- Nome comercial + princípio ativo
- Concentração, forma farmacêutica, fabricante
- **Doses por espécie:** cão, gato, equino, bovino, exóticos
- Dose mínima / máxima (mg/kg)
- Via de administração (oral, IV, IM, SC, tópico)
- Intervalo entre doses
- Contraindicações (array — permite que IA detecte conflito com histórico do pet)
- Efeitos colaterais
- Tempo de carência (para animais de produção)
- Interações medicamentosas (referência cruzada)
- Texto da bula completa (para consulta)
- Campo: `Receituário obrigatório` (Boolean)
- Campo: `Fonte` (fabricante, MAPA, cadastro manual) — para rastreabilidade da origem da informação

#### Estratégia de População do Banco de Bulas

A forma correta e legal de popular o banco é com dados fornecidos pelos próprios fabricantes:

**Fase 1 — Fabricantes diretamente (prioridade)**
- Entrar em contato com os principais fabricantes (Zoetis, MSD Animal Health, Ceva, Ourofino, Syntec, Vetnil, etc.) e solicitar as bulas em formato digital (PDF ou planilha)
- Fabricantes geralmente fornecem: todos os dados de bula já estão nos PDFs públicos nos sites deles
- Criar um script de importação: recebe o PDF da bula → IA extrai os campos estruturados (princípio ativo, doses, vias, contraindicações) → cadastra no banco para revisão manual antes de publicar
- Processo: Lucas fornece os arquivos → sistema processa e pré-preenche → veterinário valida antes de ativar

**Fase 2 — MAPA (Ministério da Agricultura)**
- Base pública de medicamentos veterinários registrados (nome comercial, princípio ativo, fabricante, registro)
- Importação via planilha/CSV disponibilizado pelo govérno
- Serve como base inicial — os dados de dosagem precisam ser complementados pelas bulas

**Fase 3 — Cadastro colaborativo pelos veterinários**
- Veterinários que usam o sistema podem cadastrar medicamentos novos
- Cadastro fica com status `pendente_revisao` até ser aprovado pelo administrador
- Incentivo: veterinários que mais contribuem ganham badge/destaque no sistema

**Fase 4 — Importador de PDF de bula (via IA)**
- Funcionalidade no painel admin: upload de um PDF de bula
- IA lê o documento e pré-preenche todos os campos do cadastro
- Operador revisa e confirma
- Reduz drasticamente o tempo de cadastro manual

### 4.4 Formulários Dinâmicos (Receituário/Prescrição)
- Seleciona o **pet** → puxa peso atual automaticamente
- Seleciona o **medicamento** do banco de bulas
- Sistema **calcula automaticamente** a dose (mg/kg × peso)
- Converte para unidade prática (comprimidos ou ml)
- Preenche: via de administração, frequência, duração sugerida
- Veterinário revisa e ajusta
- **Gera PDF de receituário com assinatura digital** (ver Seção 16)
- Múltiplos medicamentos por receituário
- Salva no histórico do pet
- **App:** tutor vê a receita no app
- Receituário tem validade legal: data de emissão, CRMV, QR Code de verificação de autenticidade

### 4.5 Calculadora de Doses
- Independente do formulário de receituário
- Busca o pet pelo cadastro (peso puxado automaticamente)
- Seleciona o medicamento da base
- Mostra: dose calculada, intervalo, duração, quantidade total a dispensar
- Ferramenta rápida de bolso para o vet
- Histórico de cálculos realizados

### 4.6 Upload de Exames + Análise por IA
- Upload de imagens (JPG, PNG, DICOM) e documentos (PDF)
- Tipos: Hemograma, Bioquímico, Urinálise, Radiografia, Ultrassom, ECG, Laudo laboratorial, Outros
- **IA analisa:**
  - Parâmetros laboratoriais: compara com valores de referência por espécie e idade, destaca alterações
  - Radiografia / imagens: descreve achados relevantes (via GPT-4 Vision ou similar)
  - Resultado fica salvo na ficha do pet e visível no app para o tutor
- Histórico organizado por data e tipo de exame
- Comparação entre exames (ex: hemograma de hoje vs. 3 meses atrás)

### 4.7 Cadastro de Procedimentos + Insumos
Cadastro do catálogo de procedimentos do veterinário:

| Campo | Exemplo |
|---|---|
| Nome | Castração feminina |
| Tipo | Cirurgia |
| Duração estimada | 90 min |
| Preço | R$ 350,00 |
| Insumos vinculados | 2× Luva, 1× Máscara, 10ml Propofol, 5 Gaze... |

- Ao **executar o procedimento**, o sistema deduz automaticamente os insumos do estoque certo (loja ou vet parceiro)
- Calcula custo real de insumos vs. preço cobrado = **margem por procedimento**
- Histórico de procedimentos por pet
- Integração com financeiro (quando faturamento for da empresa) ou financeiro próprio do vet parceiro

### 4.8 Internação
Ficha de internação com controle em tempo real:

**Dados de Abertura:**
- Pet, tutor, veterinário responsável
- Data/hora de entrada
- Motivo da internação
- Estado geral na entrada (campos clínicos)
- Previsão de alta

**Durante a Internação:**
- Registro de temperatura (com horário) → gera gráfico de evolução
- Registro de ingestão de água e alimento
- Diurese e evacuação (frequência e característica)
- Medicamentos administrados (deduz do estoque com horário e responsável)
- Insumos utilizados (deduz do estoque)
- Evolução clínica — texto por turno
- Nível de dor (por turno)

**Sistema de Alertas / Protocolos:**
- Veterinário cadastra o protocolo: "Dar analgésico X às 8h, 14h e 20h"
- Sistema dispara notificação para o responsável de plantão no horário
- Notificação no app do tutor: "Seu pet foi medicado às 14h30" (opcional)
- Alerta se temperatura sair do range configurado

**Fechamento:**
- Data/hora de saída
- Estado geral na saída
- Custo total (insumos + medicamentos + diárias)
- Orientações de alta
- Agendamento automático de retorno

### 4.9 IA — Consultora de Diagnóstico (Melhorada)
Este não é um simples chatbot. É um **parceiro clínico**:

**Modo "Debater Caso":**
- Veterinário seleciona um paciente → IA recebe automaticamente toda a ficha: anamnese, sinais vitais, histórico, exames recentes, medicamentos em uso, alergias
- Chat com memória do contexto — a IA "sabe" quem é o paciente durante toda a conversa
- Veterinário pode perguntar: "O que você acha desse quadro?", "Quais são os diagnósticos diferenciais?", "O tratamento que prescrevi está correto?"
- IA responde sempre lembrando que é suporte ao profissional, não substitui diagnóstico

**Modo "Alerta Rápido":**
- Veterinário digita apenas os sintomas → IA responde sem precisar vincular a nenhum paciente
- Rápido, como uma consulta de segundo parecer

**Modo "Analisar Exame":**
- Vet faz upload do exame diretamente no chat
- IA analisa e responde no mesmo fluxo da conversa
- Pode cruzar com dados do paciente: "Considerando que ele tem DRC, esses valores renais são preocupantes"

**Histórico de conversas:**
- Cada conversa salva no histórico do paciente
- Vet pode retomar uma conversa anterior
- IA pode ver o histórico de conversas anteriores sobre aquele paciente

---

### 4.10 Fluxo de Atendimento — Tela de Consulta (UX Completo)

Este é o coração do uso diário do veterinário. O fluxo foi desenhado para ser rápido, rico em informações e não interromper o raciocínio clínico.

#### Etapa 1 — Abertura via Agenda (ou avulsa)

O vet acessa a sub-aba **"Consulta"** na sidebar do módulo veterinário.

- **Vindo da agenda:** 1 clique no agendamento → tela abre com tutor e pet já preenchidos
- **Avulsa:** vet busca o tutor/pet manualmente

Nessa tela inicial, dois botões:
```
[ Preparar atendimento ]   →  Vai para a Tela de Preparação (sem iniciar contagem de tempo)
[ Iniciar consulta ]        →  Registra hora de início, marca "cliente compareceu" na agenda, vai para a Tela de Atendimento
```

#### Etapa 2 — Tela de Preparação (pré-atendimento)

Tela de leitura rápida antes de entrar na sala. O objetivo é o vet chegar preparado.

**Card de resumo gerado pela IA (narrativa dinâmica):**

> A IA lê todos os registros do pet e gera um texto narrativo com destaques visuais por cor. Exemplo:
>
> *"**Bolt**, 3 anos, 12,4 kg, macho castrado. **4 consultas** registradas no sistema.*  
> *⚠️ Em fevereiro/2025 apresentou **reação alérgica a dipirona** — registrada como alergia.*  
> *✅ **V10** aplicada há 45 dias (Zoetis). **Antirrábica** vence em **23 dias** — considere revacinação.*  
> *📈 Evolução de peso: 1ª consulta 10,2 kg → última 12,4 kg (**+2,2 kg** em 8 meses — acima do esperado para a raça).*  
> *🩺 Último procedimento: **limpeza de ouvido** (02/01/2026). Sem internações.*  
> *💊 Medicamentos em uso: **Apoquel 16mg** (uso contínuo desde julho/2025)."*

Cores e ícones usados:
- 🔴 Vermelho: alergias, alertas críticos
- 🟡 Amarelo: vacinas próximas do vencimento, retorno pendente
- 🟢 Verde: evolução positiva, vacinação em dia
- 🔵 Azul: informações neutras relevantes

**Botão "Ver histórico completo"** → abre a linha do tempo do pet (registro individual de cada atendimento, exame, vacina — em ordem cronológica)

**Botão na tela de preparação:**
```
[ Iniciar consulta ]  →  Dá start oficial no atendimento
```

#### Etapa 3 — Tela de Atendimento (consulta em andamento)

Tela rica e dinâmica, dividida em blocos. **Tudo na mesma tela** — sem precisar trocar de aba para registrar.

---

**Bloco: Sinais Vitais + Gráficos em Tempo Real**

| Campo | Tipo | Comportamento ao preencher |
|---|---|---|
| Peso (kg) | Numérico | Mini-gráfico de evolução de peso aparece ao lado instantaneamente |
| Temperatura (°C) | Numérico | Indicador colorido: normal (🟢), febril (🟡), hipotermia (🔵) |
| Freq. Cardíaca (bpm) | Numérico | Indicador visual de range |
| Freq. Respiratória (mrm) | Numérico | Indicador visual de range |
| Score Corporal (1–9) | Slider | Descrição da classificação aparece ao lado |
| Nível de dor (0–10) | Slider | — |
| Mucosas | Enum | — |
| TPC | Numérico | — |

> O mini-gráfico de peso mostra os últimos 6 registros + o valor digitado agora, em tempo real. Mesma lógica para temperatura se o pet estiver em protocolo de acompanhamento.

---

**Bloco: Anamnese e Exame Físico**

- Motivo da consulta
- Anamnese (texto livre)
- Exame físico por sistemas: cardiovascular, respiratório, digestório, pele/pelagem, locomotor, neurológico, oftalmológico, otológico
- Sintomas: seleção múltipla de lista + opção de adicionar livremente

---

**Bloco: Procedimento Realizado**

```
[ Selecionar procedimento ]
  ↓ ao selecionar:
    Sistema lista os insumos vinculados ao procedimento
    com quantidades pré-definidas no cadastro do procedimento
    Vet confirma ou ajusta as quantidades
    → Sistema deduz do estoque automaticamente ao finalizar
```

---

**Bloco: Medicamentos Utilizados na Consulta**

Toggle: **"Usou medicamentos?"**
> Se sim, abre o campo:
- Busca o medicamento no banco de bulas
- Informa quantidade/dose utilizada
- Campo para mais de um medicamento
- Deduz do estoque ao finalizar

---

**Bloco: Outros Custos / Insumos Avulsos**

Toggle: **"Lançar outros custos?"**
> Se sim, abre o campo:
- Busca o insumo no estoque (ex: tapete higiênico, gaze, seringa)
- Informa quantidade utilizada
- Calcula custo da consulta em tempo real (insumos + medicamentos + procedimento)

---

**Bloco: Diagnóstico e Conduta**

- Diagnóstico principal
- Diagnósticos diferenciais
- Conduta / plano de tratamento
- Retorno em: [___] dias → ao preencher, botão "Já criar agendamento de retorno" aparece
- Observações

---

**Bloco: Prescrição / Receituário**

- Seleciona medicamentos do banco de bulas
- Peso do pet já vem preenchido → dose calculada automaticamente
- Vet revisa e confirma
- Botão: **"Gerar receituário PDF"**
- Receituário fica disponível no app do tutor

---

**Bloco: Vacinas Aplicadas na Consulta**

- Seleciona a vacina aplicada
- Campo: fabricante, lote, nº série
- Data da próxima dose: sistema sugere automaticamente com base no calendário vacinal
- Atualiza carteirinha digital do pet no app instantaneamente

---

**Ícone de Chat com IA (fixo no canto da tela, igual ao PDV)**

- Ao clicar: abre painel lateral de chat com a IA
- IA já recebe automaticamente: **todo o histórico do pet + tudo que foi preenchido na tela de atendimento até o momento**
- O vet pode discutir: "Com base nesse hemograma e na história, o que você acha?"
- IA responde considerando o contexto completo — histórico + consulta atual
- O chat fica salvo no histórico do paciente

---

**Botão final:**
```
[ Finalizar consulta ]
  → Registra hora de fim (para cálculo de tempo médio de atendimento)
  → Deduz insumos e medicamentos do estoque
  → Gera lançamento financeiro (se configurado)
  → Atualiza linha do tempo do pet
  → Ativa agendamento de retorno (se criado)
  → Exibe resumo final com opção de imprimir/enviar ao tutor
```

---

**Resumo do fluxo completo:**

```
Agenda
  └→ [1 clique] Tela de Preparação
        └→ Lê resumo IA do paciente
        └→ [Iniciar consulta] Tela de Atendimento
              ├ Sinais vitais + gráficos em tempo real
              ├ Anamnese e exame físico
              ├ Procedimento → dedução de insumos
              ├ Medicamentos utilizados
              ├ Outros custos/insumos avulsos
              ├ Diagnóstico e conduta
              ├ Receituário
              ├ Vacinas aplicadas
              ├ Chat IA (ícone fixo) → debate com histórico completo
              └→ [Finalizar consulta]
                    ├ Registra hora fim
                    ├ Deduz estoque
                    ├ Gera financeiro
                    └ Atualiza app do tutor
```

---

## 5. Integração da IA com o Restante do Sistema

### 5.1 Alerta na PDV (Ponto de Venda)
Quando um tutor está comprando na loja:
- Sistema verifica se ele tem pet cadastrado
- Verifica se o produto tem princípio ativo ou componente que conflita com alguma alergia/medicamento em uso do pet
- Exibe alerta laranja/vermelho no balcão: **"⚠ Bolt (cachorro do João) tem alergia a frango — este produto contém frango"**
- Não bloqueia a venda, apenas alerta

### 5.2 Alerta no Agendamento de Banho e Tosa
- Ao agendar banho/tosa, sistema verifica: alergias a shampoo, condicionador, pós recente de cirurgia, medicamentos que impedem molhar
- Alerta para o funcionário da recepção
- Campo na ficha de banho: "Restrições veterinárias ativas: [lista automática]"

### 5.3 Alerta ao Comprar Ração
- Sistema verifica `restrições_alimentares` do pet
- Cruza com ingredientes/categoria do produto
- Alerta: "Este pet tem intolerância a grãos — esta ração contém milho e trigo"

---

## 6. Vacinação e Calendário Preventivo

Módulo separado, mas integrado:

- Cadastro de vacinas aplicadas (data, fabricante, lote, próxima dose)
- Calendário vacinal padrão por espécie (configurável pelo veterinário)
- Alertas automáticos de vencimento:
  - **App:** tutor recebe push notification 30 dias antes e 7 dias antes — gratuito, sem WhatsApp
  - **Sistema:** aparece na agenda do vet como "Pacientes com vacina vencendo esta semana"
- Vermifugação e antiparasitários: mesma lógica de alerta

### Carteirinha de Vacinação Online (no app)
- Tutor acessa pelo app a qualquer momento, sem precisar trazer papel
- Exibe: vacinas dadas, datas de aplicação, laboratório, lote, próximas datas previstas
- Countdown visual: "Antirrábica vence em **23 dias**"
- Histórico completo em ordem cronológica
- **Botão "Agendar Vacina"** → abre agenda e já cria o agendamento com tipo "Vacinação"
- **Exportar PDF** da carteirinha completa (para viagens, hotel de pets, etc.)
- **QR Code do pet:** gerado automaticamente → ao escanear, abre carteirinha completa na web (sem precisar baixar o app)
- QR Code pode ser impresso na carteirinha física, na coleira, na bolsa de transporte

---

## 7. Relatórios e Dashboard Clínico

### Dashboard do Veterinário (visão do dia)
- Pacientes agendados para hoje
- Internados no momento (com status rápido)
- Retornos pendentes (pacientes que deveriam ter voltado e não voltaram)
- Lembretes de vacinas a vencer (próximos 30 dias, nos pacientes da clínica)
- Última temperatura registrada dos internados

### Relatórios
- Procedimentos realizados no período (com receita gerada)
- Medicamentos mais utilizados (para gestão de estoque)
- Diagnósticos mais frequentes (inteligência clínica)
- Taxa de retorno de pacientes
- Custo de insumos por procedimento

---

## 8. App Mobile — Seção Veterinária

O tutor acessa pelo app — **sem precisar saber que existem dois tenants**. O app agrega dados da loja e do veterinário de forma transparente:

- **Meus pets:** ficha resumida de cada animal
- **Agendamentos:** próximas consultas, histórico, opção de confirmar/cancelar, botão "Agendar nova consulta"
- **Exames:** ver laudos e imagens (com resumo da IA em linguagem simples, não jargão médico)
- **Carteirinha de vacinas:** datas dadas + próximas datas, countdown, botão para agendar
- **Histórico de consultas:** resumo das últimas consultas em linguagem acessível
- **Receitas:** receituários prescritos, com instrução de uso
- **Notificações push (gratuitas):**
  - Lembrete de agendamento (24h e 1h antes)
  - "Seu pet foi medicado agora" (durante internação)
  - Vacina vencendo em 30 / 7 dias
  - Retorno agendado pelo veterinário
  - Confirmação de alta da internação
- **Tudo funciona mesmo que o vet seja parceiro (tenant diferente)** — app unifica visualmente

---

## 9. Sugestões Adicionais — Diferenciais Competitivos

### 9.1 Curva de Peso
- Gráfico de evolução do peso do animal ao longo do tempo
- Referência visual para o vet e para o tutor no app
- Alerta se variação for acima do esperado

### 9.2 Odontograma Veterinário
- Mapa interativo dos dentes do animal
- Registro de problemas por dente (tártaro, fratura, ausência)
- Histórico de procedimentos odontológicos

### 9.3 Protocolo Anestésico
- Ficha estruturada para cirurgias: medicação pré-anestésica, indução, manutenção
- Cálculo automático de doses baseado no peso
- Monitoramento intraoperatório: FC, FR, SpO2, temperatura, pressão

### 9.4 NPS / Avaliação Pós-Consulta
- Após a consulta, tutor recebe no app: "Como foi o atendimento?"
- Score simples de 1 a 5
- Comentário opcional
- Dashboard de satisfação para o vet

### 9.5 Linha do Tempo do Pet
- Visualização cronológica de toda a vida do animal no sistema
- Ícones por tipo de evento: consulta, vacina, exame, cirurgia, internação, banho/tosa
- Filtro por tipo e período
- O tutor vê uma versão simplificada no app

### 9.6 Importação de Exames de Laboratório
- Integração com laboratórios parceiros via API ou importação de PDF/CSV
- Resultado entra automaticamente na ficha do pet sem precisar digitar
- IA já analisa ao importar

### 9.7 Telemedicina (Fase futura)
- Consulta por vídeo within o app
- Vet compartilha tela com exames durante a chamada
- Receituário gerado ao final da teleconsulta

### 9.8 Análise de Padrões pela IA (Inteligência Clínica)
- IA detecta padrões: "Este pet sempre piora em outubro — possível alergia sazonal"
- "3 animais desta raça na sua clínica tiveram displasia — considere rastreamento"
- "Este paciente voltou 3 vezes com o mesmo problema — pode haver causa não resolvida"

### 9.9 IA Clínica Coletiva (dados anonimizados)
- Com consentimento, dados anonimizados de múltiplos tenants alimentam um modelo de inteligência coletiva
- Exemplos do que a IA aprende: "10.000 casos de dermatite — padrão de resposta ao tratamento X"
- Benefício para cada vet: sugestões mais precisas baseadas em volume real de casos
- **Detecção de surtos regionais:** se múltiplos pets da mesma cidade apresentam sintomas similares, sistema alerta: "Possível surto na sua região — 8 casos de vômito nas últimas 48h"
- Todos os dados são anonimizados antes de sair do tenant (sem nome de pet, tutor ou vet)

### 9.10 Banco de Protocolos Veterinários
- Veterinário cria e salva protocolos de tratamento reutilizáveis
- Exemplos: "Protocolo Giardíase", "Protocolo Pós-Castração", "Protocolo Internação DRC"
- Cada protocolo tem: medicamentos, doses, frequência, duração, observações de acompanhamento
- Ao iniciar tratamento, seleciona o protocolo → sistema já preenche a prescrição
- Biblioteca de protocolos pode ser compartilhada entre profissionais do mesmo tenant

### 9.11 Dashboard de Performance Clínica
- **Tempo médio de consulta** (baseado em "Iniciar atendimento" / "Finalizar atendimento")
- **Taxa de retorno:** % de pacientes que voltaram dentro do prazo indicado
- **Taxa de falta:** pacientes que não compareceram
- **Diagnósticos mais frequentes** no período
- **Procedimentos mais realizados**
- **Receita por procedimento** (para identificar o que é mais lucrativo)
- **Custo de insumos por procedimento** (margem real)
- **Benchmark regional (anonimizado):** compara as métricas da clínica com a média dos outros tenants do sistema na mesma região
  - Ex: "Tempo médio da sua clínica: 18 min | Média regional: 22 min"
  - Ex: "Taxa de retorno da sua clínica: 42% | Média regional: 35%"
  - Nenhum dado identificável é compartilhado — apenas médias agregadas

### 9.12 Health Score do Pet

Um score calculado automaticamente pelo sistema com base nos dados estruturados do pet:

```
Bolt — Health Score: 82/100

✅ Vacina V10 em dia
✅ Peso dentro do esperado para a raça
⚠ Vacina antirrábica vence em 23 dias
⚠ Exame de sangue com TGP elevada (último exame)
🔴 Sobrepeso detectado nas últimas 3 consultas
```

**Componentes do score:**
| Critério | Peso |
|---|---|
| Vacinas em dia | 20% |
| Peso ideal para raça/idade | 20% |
| Exames laboratoriais normais | 20% |
| Ausência de doenças crônicas ativas | 15% |
| Vermifugação em dia | 10% |
| Consultas regulares (retornos feitos) | 10% |
| Sem alergias ativas sem tratamento | 5% |

- Score visível no app para o tutor com linguagem simples
- Usado pela IA para priorizar alertas e sugestões
- Vet vê score na tela de preparação antes de atender

### 9.13 Perfil Comportamental do Pet

Campos estruturados para registrar o temperamento — essencial para Banho e Tosa, consultas e futuro hotel pet:

| Campo | Opções |
|---|---|
| Temperamento geral | Calmo / Agitado / Ansioso / Agressivo |
| Reação a outros animais | Amigável / Indiferente / Agressivo |
| Reação a pessoas desconhecidas | Amigável / Tímido / Agressivo |
| Medo de secador | Sim / Não / Moderado |
| Medo de tesoura/máquina | Sim / Não / Moderado |
| Aceita coleira/focinheira | Sim / Não / Com resistência |
| Comportamento no carro | Calmo / Agitado / Vomita |
| Observações comportamentais | Texto livre |

- Preenchido pelo veterinário ou pelo próprio tutor no app
- Aparece automaticamente para o tosador ao abrir o agendamento de banho
- Aparece para o vet na tela de preparação da consulta

### 9.14 Pré-triagem no App (antes da consulta)

Após confirmar o agendamento, o tutor recebe no app um formulário rápido de pré-triagem:

- Qual o motivo da consulta?
- Desde quando o pet apresenta esses sintomas?
- Está vomitando? (Sim / Não)
- Está com diarreia? (Sim / Não)
- Está comendo normalmente? (Sim / Com dificuldade / Não)
- Está bebendo água normalmente? (Sim / Mais que o normal / Não)
- Tem sangramento em algum lugar? (Sim / Não)
- Está se coçando muito? (Sim / Não)
- Alguma outra informação relevante?

- Tutor responde pelo app até o dia da consulta
- Veterinário vê as respostas na **tela de preparação**, antes de iniciar o atendimento
- Economiza tempo de anamnese e permite o vet ir mais preparado

### 9.15 Predisposição Genética por Raça

O sistema carrega uma base de conhecimento de predisposições por raça. Ao cadastrar ou editar o pet, aparece automaticamente:

```
Labrador Retriever — predisposições conhecidas:
⚠ Displasia coxofemoral
⚠ Obesidade
⚠ Dermatite atópica
⚠ Epilepsia

Golden Retriever:
⚠ Displasia coxofemoral
⚠ Câncer (alta incidência na raça)
⚠ Hipotireoidismo

Bulldog Inglês:
⚠ Síndrome braquicefálica
⚠ Problemas de pele em dobras
⚠ Displasia de cotovelo
```

- Aparece como aviso na tela de preparação da consulta
- IA usa isso para sugerir exames de rastreamento preventivo
- Pode ser expandida/editada pelo veterinário (cada vet pode adicionar observações à base)

### 9.16 Timeline Farmacológica (Histórico de Medicamentos)

Visualização cronológica de todos os medicamentos usados pelo pet:

```
Linha do tempo — medicamentos:

Jan/2026  Amoxicilina 250mg  (7 dias)
Jun/2025  Amoxicilina 250mg  (5 dias)  ← uso repetido detectado
Abr/2025  Apoquel 16mg       (contínuo — em uso)
Dez/2024  Prednisolona 20mg  (3 dias)
```

- IA detecta padrões: "Este pet usou o mesmo antibiótico 3 vezes em 12 meses — considere cultivo"
- Alerta de interações ao prescrever: "Atenção: Prednisolona + Apoquel — monitorar imunossupressão"
- Alerta antes de salvar a prescrição se houver: alergia registrada ao medicamento, interação conhecida, ou dose acima do limite para o peso

### 9.17 Controle de Antibióticos (Antimicrobial Stewardship)

Funcionalidade voltada a boas práticas clínicas e rastreabilidade:

- Ao prescrever antibiótico, veterinário informa: indicação clínica, cultura realizada (sim/não), duração prevista
- Relatório mensal: quais antibióticos foram mais utilizados, por qual indicação, por quantos dias
- Alertas: uso repetido do mesmo antibiótico em curto período, prescrição sem exame de cultura para casos recorrentes
- Útil para auditorias internas e conscientização sobre resistência bacteriana
- Dado que pode alimentar a inteligência coletiva (anonimizado)

### 9.18 Registro Fotográfico Clínico com Timeline

Além do upload de exames, o veterinário pode registrar fotos clínicas vinculadas a uma condição:

- Tipo: dermatologia, ferida cirúrgica, pós-operatório, lesão traumática, tumor
- Cada foto tem data e descrição
- Sistema exibe **comparação visual lado a lado** entre fotos da mesma condição em datas diferentes
- IA pode descrever a evolução: "A ferida reduziu aproximadamente 40% em 10 dias"
- Visível para o tutor no app (se o vet autorizar)

### 9.19 Orçamento Veterinário com Aprovação Digital

Antes de procedimentos cirúrgicos ou tratamentos de alto custo:

```
Orçamento — Castração Feminina (Bella, 2 anos)

Consulta pré-operatória     R$ 80,00
Hemograma + bioquímico      R$ 120,00
Procedimento (castração)    R$ 350,00
Anestesia + monitoramento   R$ 150,00
Internação (1 dia)          R$ 100,00
Medicações pós-op           R$ 60,00
─────────────────────────────────────
Total estimado              R$ 860,00
```

- Tutor recebe o orçamento no app
- Botões: **Aprovar** / **Solicitar contato** / **Recusar**
- Aprovação registra: hora, IP, dispositivo (validade jurídica)
- Orçamento aprovado converte-se automaticamente em procedimento agendado
- Ao finalizar o procedimento, sistema compara orçado vs. realizado

### 9.20 Checklist Pré-Cirúrgico

Antes de qualquer cirurgia, o sistema exige a confirmação de um checklist:

```
Checklist — Castração Bella (agendada 14/03/2026 09h)

[ ] Jejum confirmado pelo tutor (mínimo 8h)
[ ] Hemograma realizado e analisado
[ ] Bioquímico realizado e analisado
[ ] Risco anestésico calculado (ASA score)
[ ] Termo de autorização assinado pelo tutor
[ ] Medicação pré-anestésica administrada
[ ] Peso aferido hoje
[ ] Acesso venoso instalado
```

- Itens marcados com hora e responsável
- Cirurgia só pode ser registrada como "iniciada" com o checklist completo
- Vet pode adicionar itens customizados por tipo de procedimento

### 9.21 Score de Risco Anestésico (ASA Score)

Calculado automaticamente antes de qualquer cirurgia com base nos dados do sistema:

| Classe ASA | Critério | Risco |
|---|---|---|
| I | Animal saudável, sem doenças | Mínimo |
| II | Doença sistêmica leve (obesidade, infecção leve) | Baixo |
| III | Doença sistêmica grave (DRC compensada, diabetes) | Moderado |
| IV | Doença sistêmica grave com risco de vida | Alto |
| V | Animal moribundo sem expectativa sem cirurgia | Crítico |

- Sistema sugere a classe com base em: doenças crônicas, exames recentes, peso, idade, medicamentos em uso
- Veterinário confirma ou ajusta
- Score fica registrado no prontuário cirúrgico
- Alertas específicos por classe: "Classe III — recomendado monitoramento de SpO2 contínuo"

### 9.22 Modo Emergência

Botão visível na recepção/sala de espera (e no sistema do vet):

```
🚨 EMERGÊNCIA
```

- Abre ficha rápida: busca pet por nome/tutor, ou cadastra rapidamente se for primeira vez
- Campo: sintoma principal (campo livre + seleção rápida: dispneia, convulsão, trauma, intoxicação, hemorragia...)
- Marcar como "urgente" → paciente sobe para o topo da fila do dia
- Notificação imediata para o veterinário de plantão
- Registra hora de entrada da emergência (para métricas de tempo de resposta)

### 9.23 LTV — Valor Vitalício do Paciente

No perfil de cada pet e de cada cliente:

```
Bolt — cliente desde Jan/2023

Consultas realizadas:    8
Procedimentos:           2
Produtos comprados:     47 itens
Serviços de banho:      14
─────────────────────────────────
Total gasto na empresa: R$ 4.280,00
Total gasto no vet:     R$ 1.340,00
Valor total:            R$ 5.620,00
```

- Útil para identificar clientes de alto valor e fidelizá-los
- Alerta se cliente de alto LTV não retorna há mais de 90 dias
- Relatório: ranking de clientes por LTV

### 9.24 IA Traduzindo o Diagnóstico para o Tutor

O veterinário escreve o diagnóstico técnico normalmente. O sistema gera automaticamente uma versão em linguagem simples para o tutor ver no app:

```
Vet registra:
"Dermatite atópica com hipersensibilidade alimentar secundária a proteína bovina"

App mostra ao tutor:
"Bolt tem uma alergia de pele causada por uma reação ao alimento — 
provavelmente à proteína da carne bovina. Isso causa coceira intensa 
e inflamação. O tratamento inclui mudar a ração e usar medicamentos 
para controlar a coceira. É importante seguir as instruções do 
veterinário rigorosamente."
```

- Gerado pela IA com base no diagnóstico + conduta registrada
- Veterinário pode revisar antes de enviar
- Também traduz a prescrição: "Apoquel 16mg — 1 comprimido de manhã, todos os dias, junto com a comida"

### 9.25 ID Universal do Pet (PET ID)

Cada pet recebe um identificador único no sistema:

```
PET-8F2A91
```

- QR Code gerado automaticamente
- Ao escanear: exibe ficha pública resumida com alergias, contato do tutor, clínica responsável
- Útil em casos de pets perdidos (coleira, plaquinha), internação em emergência desconhecida, hotel pet
- A ficha pública mostra apenas o que o tutor autorizar (configurável)
- Diferente do microchip — complementar, não substitui

### 9.26 Pacotes de Tratamento

Veterinário monta pacotes de serviços com preço fechado:

```
Pacote Dermatologia
  Consulta inicial              R$ 80
  Raspado cutâneo               R$ 50
  Shampoo terapêutico (1 frasco) R$ 45
  Retorno em 30 dias            R$ 60
  ─────────────────────────────────
  Pacote fechado                R$ 195 (desconto de R$ 40)
```

- Pacote fica disponível para ser ofertado ao cliente no app ou no balcão
- Ao contratar: já cria todos os agendamentos e lança os itens no financeiro
- Facilita plano de tratamento completo com custo previsível para o tutor

### 9.27 Curvas Fisiológicas Automatizadas

Além da curva de peso (já prevista), o sistema gera gráficos automáticos para qualquer parâmetro registrado ao longo do tempo:

- Temperatura (especialmente em internação e doenças crônicas)
- Glicemia (diabetes)
- Ureia / Creatinina (DRC)
- Pressão arterial
- Peso corporal
- Nível de dor (escala 0-10 por consulta)

- Gráficos aparecem automaticamente na tela de atendimento ao registrar um novo valor
- IA detecta tendências: "Temperatura subindo progressivamente nas últimas 6h — reavalie"
- Tutor vê gráfico simplificado de peso e temperatura no app

### 9.28 Digital Twin do Pet (Visão de Futuro)

O ponto mais avançado do roadmap. Usando todos os dados estruturados acumulados, o sistema constrói um **perfil preditivo** do animal:

```
Bolt — Perfil preditivo (IA)

Risco de obesidade nos próximos 12 meses:   Alto (87%)
  → Peso aumentou 2,2kg em 8 meses, raça predisposta

Risco renal nos próximos 24 meses:          Moderado (41%)
  → Creatinina subindo gradualmente há 3 exames

Risco articular:                             Alto (72%)
  → Labrador 5 anos, sobrepeso, sem exame articular
  
Próxima ação recomendada:
  📋 Dieta hipocalórica imediata
  🔬 Exame ortopédico preventivo
  💊 Suplemento condroprotedor
```

- Não é diagnóstico — é **apoio à decisão preventiva**
- Veterinário usa como guia para consultas preventivas
- Tutor vê versão simplificada no app: "Bolt precisa de atenção com o peso"
- Quanto mais dados no sistema, mais preciso o modelo fica
- **Fase futura** — requer volume de dados acumulado para ser confiável

---

## 10. Estoque Veterinário

### Cenário 1 — Vet da Casa
- Usa o estoque normal da loja
- Pode ter uma **subcategoria/setor** "Veterinário" para separar visualmente
- Deduções automáticas ao executar procedimento e ao registrar item na internação
- Financeiro unificado com a loja

### Cenário 2 — Vet Parceiro (tenant próprio)
- Estoque completamente independente
- Entrada de insumos: nota de entrada própria
- Saída: procedimentos e internações deduzem do estoque dele
- Relatório de consumo de insumos: custo real vs. receita
- Financeiro próprio: receitas e despesas separados da loja

---

## 11. Configurações do Módulo Veterinário

Tela de configurações exclusiva do módulo:

```
Configurações > Módulo Veterinário

MODELO OPERACIONAL
  ( ) Veterinário vinculado (mesmo tenant — faturamento unificado)
  ( ) Veterinário parceiro (tenant próprio — financeiro separado)

FATURAMENTO (modo vinculado)
  [ ] Procedimentos veterinários somam ao financeiro da empresa
  Impacto: se desmarcado, os procedimentos do vet geram lançamentos
  apenas no centro de custo "Veterinário"

COMISSÃO (modo parceiro)
  [ ] Ativar repasse de comissão para a empresa
  Percentual da empresa sobre procedimentos: ____%
  Aplicar sobre: ( ) Todos os procedimentos  ( ) Somente consultas
  Gerar relatório de repasse: ( ) Semanal  ( ) Quinzenal  ( ) Mensal

ESTOQUE
  [ ] Veterinário usa estoque próprio separado
  [ ] Alertar quando insumo atingir estoque mínimo
  [ ] Permitir transferência de insumos entre loja e veterinário
  
AGENDAMENTO
  Horário de atendimento: __:__ às __:__
  Intervalo padrão entre consultas: [30 min]
  [ ] Permitir agendamento pelo app
  [ ] Enviar push notification de lembrete (24h antes)
  [ ] Enviar push notification de lembrete (1h antes)
  
ALERTAS
  [ ] Ativar alerta de alergias na PDV
  [ ] Ativar alerta de alergias no agendamento de Banho/Tosa
  [ ] Ativar alerta de restrições alimentares na PDV
  
IA
  [ ] IA ativa para análise de exames (laboratoriais)
  [ ] IA ativa para análise de imagens (raio-x, ultrassom)
  [ ] IA ativa para sugestão de diagnóstico
  [ ] Compartilhar análises da IA com o tutor pelo app
  [ ] Participar da base coletiva de inteligência clínica (anonimizado)
  
RECEITUÁRIO
  Nome do veterinário padrão: _______________
  CRMV: _______________
  Assinatura digital: [upload]
  Logo da clínica: [upload]

PRONTUÁRIO / LGPD
  Prontuário pertence a: ( ) Empresa  ( ) Veterinário
  [ ] Loja parceira pode ver resumo do pet (vacinas, alergias, peso)
  [ ] Loja parceira pode ver histórico de consultas completo
  Log de acesso ao prontuário: [ver auditoria]
```

---

## 12. Fases de Implementação Sugeridas

> Legenda: ✅ Completo | 🔶 Parcial | ❌ Pendente

### Fase 1 — Fundação (base sólida)
1. ❌ Expandir campos clínicos do cadastro de Pet (campos estruturados — não texto livre)
2. ❌ Catálogo global de produtos/medicamentos + tabela `tenant_stock`
3. 🔶 Módulo de Medicamentos / Bulas — tabela `vet_medicamentos_catalogo` criada + tela `VetCatalogo.jsx`; falta banco de bulas completo, doses por espécie, interações
4. ❌ Calculadora de doses (peso → dose automática)
5. 🔶 Prontuário (consulta) com sinais vitais estruturados — tabela `vet_consultas` criada + `VetConsultaForm.jsx` (3 etapas) ✅ + prescrição implementada ✅; falta cálculo automático de dose por peso e IA
6. ❌ Configuração do módulo (modelo operacional, faturamento, estoque separado)

### Fase 2 — Clínica em funcionamento
7. 🔶 Agenda veterinária com push notifications — tabela `vet_agendamentos` criada + `VetAgenda.jsx` ✅ + criação de agendamento implementada ✅; falta apenas push notifications
8. 🔶 Formulários dinâmicos / Receituário com cálculo automático de dose — tabelas `vet_prescricoes` + `vet_itens_prescricao` criadas; falta cálculo automático e geração de PDF
9. 🔶 Procedimentos cadastráveis com insumos vinculados — tabelas `vet_catalogo_procedimentos` + `vet_procedimentos_consulta` criadas; falta vinculação de insumos e dedução de estoque
10. 🔶 Upload e análise de exames pela IA — tabela `vet_exames` criada; falta upload de arquivo e análise por IA
11. ❌ Integração alertas → PDV e Banho/Tosa
12. ❌ Comissão automática (para modelo parceiro)

### Fase 3 — Nível avançado
13. 🔶 Internação completa (protocolos, lembretes, curva de temperatura) — ✅ criação/alta/evolução/procedimento implementados (backend + frontend); falta alertas automáticos de horário e gráficos de evolução de temperatura/parâmetros
14. ❌ IA consultora de diagnóstico (modo Debater Caso + Analisar Exame)
15. 🔶 Vacinação, calendário preventivo + carteirinha digital no app — ✅ tabelas + `VetVacinas.jsx` + alertas de vencimento implementados (`vacinasVencendo`); falta calendário preventivo por espécie e carteirinha digital no app
16. 🔶 Dashboard clínico e relatórios de performance — `VetDashboard.jsx` criado; falta KPIs reais (tempo médio, taxa de retorno) conectados ao banco
17. ❌ Banco de protocolos veterinários reutilizáveis

### Fase 4 — Multi-Tenant Avançado
18. ❌ Tabela `vet_partner_link` e arquitetura de eventos entre tenants
19. ❌ `organization_type` (petshop / veterinary_clinic / grooming / hospital)
20. ❌ IA clínica coletiva (dados anonimizados multi-tenant)

### Fase 5 — App e Diferenciais
21. ❌ Seção veterinária no app mobile (agendamentos, exames, receitas, carteirinha)
22. ❌ QR Code do pet → carteirinha pública na web
23. ❌ Curva de peso + linha do tempo do pet
24. ❌ NPS pós-consulta
25. ❌ Telemedicina

---

## 📋 PRÓXIMO MÓDULO APÓS VETERINÁRIO: Banho e Tosa

Ao concluir o módulo veterinário, o próximo módulo prioritário é **Banho e Tosa**, que se beneficia diretamente da infraestrutura veterinária já construída:

**O que o módulo de Banho e Tosa vai precisar (planejamento inicial):**
- Agenda de Banho e Tosa (integrada com a agenda geral)
- Ficha do serviço: tipo (banho simples, banho + tosa, tosa higiênica, tosa na tesoura), tamanho do pet, observações
- **Alerta automático de restrições veterinárias** ao abrir o agendamento:
  - Cirurgia recente (não molhar)
  - Dermatite (shampoo especial necessário)
  - Medicamento tópico em uso
  - Alergias a produtos
- Tabela de preços por porte e tipo de serviço
- Controle de fila do dia (qual pet está em qual etapa: aguardando, em banho, em tosa, secando, pronto)
- Notificação push para o tutor quando o pet estiver pronto
- Histórico de serviços por pet
- Métricas: tempo médio por serviço, receita por tipo, profissional mais produtivo
- Ficha de cada tosador/banhista (produtividade, avaliação)
- NPS pós-banho/tosa enviado pelo app

---

## 13. Decisões Técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| Banco de dados | PostgreSQL (já usado) | Suporta JSON, arrays, multi-tenant |
| Dados clínicos | Campos estruturados + JSON para flexibilidade | IA consegue ler e filtrar |
| Análise de imagens | GPT-4 Vision ou Google Gemini Vision | Melhor custo-benefício para raio-x |
| Análise de exames laboratoriais | Tabela de referência + LLM | Precisão com custo controlado |
| Notificações | Push notification via app (gratuito) | Sem custo de WhatsApp/SMS |
| PDF de receituário | Geração server-side (ReportLab ou WeasyPrint) | Mesmo padrão do sistema |
| Campos de alergias | Array de strings (PostgreSQL ARRAY) | IA filtra por substring |
| Catálogo de produtos | Tabela global + tenant_stock por tenant | Evita duplicação |
| Vínculo entre tenants | Tabela `vet_partner_link` | Simples, extensível |
| Eventos multi-tenant | Sistema de eventos interno (appointment.created, exam.uploaded, prescription.created) | Tenants conversam sem acoplamento |
| Tipo de organização | Campo `organization_type` no tenant (petshop / veterinary_clinic / grooming / hospital) | Permite escalar para outros nichos |
| Prontuário / LGPD | Pertence ao tenant do veterinário, loja vê apenas resumo | Correto juridicamente (CFV + LGPD) |
| Auditoria de acesso | Log de quem acessou o prontuário, quando e de qual tenantl | Obrigatório para LGPD |

---

## 14. LGPD e Responsabilidade Clínica

O prontuário veterinário é dado sensível e precisa de tratamento especial:

- **Quem cria o prontuário é o veterinário** — não a loja
- Prontuário pertence ao **tenant do veterinário**, mesmo que ele use o espaço da loja
- A loja (tenant A) só enxerga o **resumo do pet** (vacinas, alergias, peso) — nunca o prontuário completo, a não ser que configurado explicitamente
- **Log de auditoria:** todo acesso a dados clínicos gera um registro (quem acessou, quando, de qual IP, de qual tenant)
- **Transferência de dados:** se o proprietário do pet solicitar, o sistema gera exportação completa do histórico do animal
- **Exclusão de dados:** em caso de solicitação de exclusão, sistema preserva dados anonimizados para fins estatísticos e exclui dados identificáveis
- Termos de uso devem ser claros sobre quem é o controlador do dado (veterinário) e quem é o processador (plataforma)

---

## 15. O que Reaproveitar do SISTEMA VETERINÁRIO existente

| Componente | Aproveitamento |
|---|---|
| Modelos de dados (Consulta, Receituário, etc.) | Adaptar à arquitetura multi-tenant do Sistema Pet |
| Lógica de cálculo de doses | Reaproveitar diretamente |
| Prompts de análise de sintomas da IA | Reaproveitar e melhorar |
| Geração de PDF | Adaptar ao padrão do Sistema Pet |
| Tabela `ExameReferencia` (valores de referência) | Reaproveitar dado puro |
| Telas React (Consultas, Receituário, Calculadora) | Adaptar ao visual do Sistema Pet |
| Serviço AI (`ai_service.py`) | Adaptar — já suporta OpenAI e Groq |

**O que NÃO reaproveitar:** autenticação, banco SQLite, configuração Docker, estrutura de rotas sem multi-tenant.

---

## 16. Prontuário Digital com Assinatura

### O que é o Prontuário Digital

O prontuário veterinário digital é o documento oficial que registra cada atendimento. Quando assinado digitalmente, tem **validade jurídica** equivalente ao papel, conforme a MP 2.200-2/2001 (ICP-Brasil) e o Marco Civil da Internet.

### Documentos que precisam de assinatura digital

| Documento | Obrigatório assinar? | Quem assina |
|---|---|---|
| Prontuário / Ficha Clínica | Sim | Veterinário |
| Receituário | Sim (obrigatório por lei) | Veterinário |
| Laudo de exame | Sim | Veterinário |
| Termo de autorização (cirurgia, internação) | Sim | Tutor |
| Declaração de óbito animal | Sim | Veterinário |
| Alta da internação | Recomendado | Veterinário |

### Modelos de Assinatura (do mais simples ao mais robusto)

**Opção A — Assinatura eletrônica simples (implementar primeiro)**
- Veterinário faz upload de uma imagem da sua assinatura + carimbo (na configuração do perfil)
- Sistema insere a imagem no PDF gerado automaticamente
- PDF é gerado com hash SHA-256 do conteúde + timestamp assinado pelo servidor
- QR Code no documento aponta para URL de verificação: `https://sistema.com/verificar/{hash}`
- Qualquer um pode escanear e confirmar: "Documento áutêntico, emitido em 12/03/2026 por Dr. Ana Silva CRMV-SP 12345"
- **Custo: zero** — geração server-side com Python (ReportLab + hashlib)
- **Validade:** suficiente para uso diário na clínica e exigida em pet shops, farmácias, etc.

**Opção B — Assinatura eletrônica avançada via serviço externo (fase futura)**
- Integração com plataforma de assinatura eletrônica (AutoDoc, D4Sign, ClickSign, Assina.Online)
- Tutor assina o termo de autorização pelo celular (via link no WhatsApp/app)
- Registro de IP, geolocalização e timestamp da assinatura
- Ideal para termos cirúrgicos e de internação onde a assinatura do tutor é crítica
- Custo: a partir de R$ 0,50 por documento assinado (apenas quando necessário)

**Opção C — Certificado Digital ICP-Brasil (fase muito futura)**
- Veterinário usa seu e-CRMV ou certificado A1/A3
- Máxima validade jurídica
- Complexidade alta de implementação — deixar para quando houver demanda real

### Fluxo de geração do Prontuário Digital

```
Veterinário finaliza a consulta na tela de atendimento
  ↓
Sistema consolida todos os dados registrados na consulta
(sinais vitais, anamnese, diagnóstico, conduta, receituário, insumos)
  ↓
Gerado PDF do Prontuário com:
  ├ objeto da consulta
  ├ dados do paciente e tutor
  ├ sinais vitais com comparativo histórico
  ├ diagnóstico e conduta
  ├ hash do documento + timestamp
  ├ QR Code de verificação de autenticidade
  └ assinatura do veterinário (imagem + CRMV)
  ↓
PDF salvo no sistema — imutável após assinado
(qualquer alteração posterior gera nova versão com log)
  ↓
Disponível no app do tutor imediatamente
```

### Termos de Autorização (assinatura do tutor)

Para procedimentos cirúrgicos e internações:
- Sistema gera o termo automaticamente com dados do pet e do procedimento
- **No balcão:** tutor assina em tablet/tela com o dedo (assinatura manuscrita digital)
- **Remoto:** tutor recebe link pelo app → lê e assina pelo celular
- Termo fica salvo no histórico do pet e do prontuário
- Modelo de termos: configurável pelo administrador (cada clínica adequa o texto)

### Armazenamento e Auditoria

- Todo prontuário assinado é **imutável** — apenas leitura após assinado
- Qualquer correção gera uma **adenda** (novo registro vinculado, não sobreescreve)
- Log de auditoria: quem acessou o prontuário, quando, de qual IP (LGPD)
- Backup automático diário dos PDFs em storage seguro
- Tempo de guarda: mínimo 5 anos (recomendação do CFMV)

---

*Este documento é a referência central para implementação do módulo veterinário e do módulo de Banho e Tosa.*  
*Versão 2.0 — Atualizado em Março/2026.*  
*Atualizar a cada decisão tomada durante o desenvolvimento.*
