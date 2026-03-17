# Cronograma Piloto WhatsApp (WAHA + n8n)

Status: ETAPA DE NUMERO/CHIP CONGELADA ATE TER CELULAR SECUNDARIO
Data base: 2026-03-16

## 1) Objetivo do piloto

Validar fluxo ponta a ponta com baixo custo:
- mensagem WhatsApp -> WAHA -> n8n -> backend Sistema Pet -> IA -> resposta
- consultas de produto/preco/estoque funcionando
- handoff para humano em pedidos (Fase 1)

## 2) O que fica congelado agora

Bloqueado ate ter celular + chip de teste:
- pareamento WhatsApp no WAHA (QR)
- testes reais com numero externo
- validacao de estabilidade de sessao

## 3) O que podemos adiantar sem chip (agora)

### Bloco A - Infra e arquitetura
- Definir stack final do piloto: WAHA + n8n + backend atual
- Definir onde vai rodar: servidor prod separado (preferencial) ou ambiente dev
- Criar compose do piloto com redes separadas e variaveis em .env

### Bloco B - Integracao tecnica
- Criar endpoint interno no backend para entrada de mensagem do WAHA/n8n
- Normalizar payload de entrada/saida (contrato unico)
- Preparar roteamento de intents ja validado na Fase 1

### Bloco C - Seguranca minima
- Criar token de autenticacao entre n8n -> backend
- Criar allowlist de IP/rede quando possivel
- Definir logs sem vazar chave/token

### Bloco D - Testes sem WhatsApp real
- Simulador local de mensagens (POST interno)
- Cenarios de teste: consulta produto, consulta estoque, status pedido, handoff
- Medir tempo medio de resposta e taxa de erro tecnico

### Bloco E - Operacao
- Checklist de subida/queda do piloto
- Checklist de rollback rapido
- Checklist de observabilidade (onde olhar logs)

## 4) Cronograma sugerido (curto)

### Dia 0 (hoje)
- Fechar decisao de arquitetura WAHA+n8n
- Criar este cronograma e plano tecnico
- Listar variaveis de ambiente necessarias

### Dia 1 (sem chip)
- Subir WAHA e n8n em ambiente de teste
- Implementar endpoint interno backend para fluxo n8n
- Criar fluxo n8n inicial (entrada -> IA -> resposta mock)

### Dia 2 (sem chip)
- Integrar fluxo n8n com consultas reais do backend
- Rodar testes simulados e ajustar erros
- Preparar dashboard simples de logs

### Dia 3 (quando tiver chip)
- Parear WhatsApp no WAHA
- Rodar testes reais ponta a ponta
- Ajustar respostas e handoff

### Dia 4
- Piloto controlado com poucas conversas
- Coletar metricas e decidir: continua no piloto ou migra para canal oficial

## 5) Checklist de retomada (amanha)

Quando voce voltar com celular/chip:
1. Confirmar numero de teste dedicado
2. Parear no WAHA via QR
3. Enviar 10 mensagens de teste guiado
4. Validar respostas no backend e no n8n
5. Registrar pontos de falha e correcoes

## 6) Riscos e mitigacao

- Risco: desconexao da sessao WhatsApp
  - Mitigacao: reconexao automatica + monitoramento
- Risco: bloqueio por volume/comportamento
  - Mitigacao: limitar volume e manter mensagens naturais
- Risco: regressao no backend
  - Mitigacao: usar endpoint interno com token e testes automatizados

## 7) Decisao de saida do piloto

Encerrar piloto WAHA+n8n e migrar para oficial quando:
- fluxo estavel por >= 7 dias
- erro tecnico baixo
- operacao depender de alta disponibilidade
- necessidade comercial de numero oficial com menor risco
