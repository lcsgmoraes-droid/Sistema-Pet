# Base veterinaria e assistente clinico do CorePet

## O que esta implementado

O CorePet separa tres tipos de informacao:

1. **Catalogo regulatorio global**: metadados e links de rotulos veterinarios
   vindos de fontes oficiais.
2. **Catalogo operacional do tenant**: medicamentos e procedimentos escolhidos
   pela clinica para uso na rotina.
3. **Conhecimento clinico rastreavel**: estudos novos passam por triagem
   automatica de origem, resumo e tipo de publicacao antes de poderem ser
   recuperados pelo assistente.

Essa separacao evita tratar uma listagem externa como prescricao pronta. A
interface informa quando a referencia passou apenas por triagem automatica ou
tambem recebeu revisao humana.

## Volume atual e limites regulatorios

- Foram indexados 3.484 rotulos veterinarios do DailyMed e 5.273 produtos
  autorizados com SPC oficial do Veterinary Medicines Directorate do Reino
  Unido: 8.757 referencias regulatorias no total.
- Esses documentos sao dos Estados Unidos. Um rotulo no DailyMed nao equivale a
  registro no MAPA e nao confirma, sozinho, aprovacao pela FDA.
- O catalogo inicial de procedimentos possui 70 itens comuns e versionados. Ele
  e copiado no onboarding de novos tenants, sem precos e sem insumos
  inventados. Clinicas existentes recebem apenas um aviso e uma opcao explicita
  de importacao; nao existe backfill automatico.
- Dados e telas do Vet Smart nao devem ser copiados. A expansao brasileira deve
  usar fontes licenciadas ou oficiais e contratos proprios.

## Atualizacao por estudos

A sincronizacao usa as E-utilities do PubMed/NLM. No ambiente local ela e
executada automaticamente uma vez por semana, depois de um atraso inicial de
60 segundos. Nos demais ambientes o job fica desativado por padrao e exige
configuracao operacional explicita:

```text
VET_EVIDENCE_SYNC_ENABLED=true
VET_EVIDENCE_SYNC_INTERVAL_HOURS=168
VET_EVIDENCE_SYNC_LIMIT=100
```

O agendamento classifica automaticamente artigos do PubMed com resumo
bibliografico suficiente como `auto_disponivel`. Registros sem resumo ficam
apenas como `referencia`; retratacoes sao rejeitadas. Uma falha de rede nao
interfere no funcionamento do prontuario ou do assistente.

Tambem e possivel executar a sincronizacao manualmente:

```powershell
docker exec petshop-dev-backend python -m app.scripts.run_vet_clinical_evidence_sync
```

O comando acima e somente dry-run. Para persistir os resultados em DEV:

```powershell
docker exec petshop-dev-backend python -m app.scripts.run_vet_clinical_evidence_sync --apply --limit 100
```

Documentos `auto_disponivel` e `aprovado` entram no contexto do assistente. A
resposta recebe a identificacao do nivel de curadoria. Se titulo, resumo,
autores, data ou temas mudarem, a elegibilidade e recalculada.

O endpoint `GET /vet/ia/conhecimento/status` mostra a cobertura. A revisao
humana continua disponivel como curadoria adicional para administradores:

- `GET /vet/ia/conhecimento/documentos?status=pendente`
- `POST /vet/ia/conhecimento/documentos/{id}/revisar`

## Como a IA usa a informacao

O assistente recebe somente o contexto do tenant autenticado: ficha do
paciente, alergias, medicamentos continuos, condicoes cronicas, consulta,
prescricoes, exames e vacinas relacionados. Quando ha evidencia disponivel e
relevante, a resposta recebe referencias `[E1]`, `[E2]` e a interface mostra
titulo, data e link.

Feedbacks explicitos nas respostas formam uma memoria adaptativa por usuario
dentro do tenant. Comentarios como preferencia de formato, nivel de detalhe ou
correcao de fluxo entram nas conversas futuras daquele usuario. Essa memoria
nao transforma opiniao em evidencia cientifica e nunca e compartilhada entre
clinicas.

O assistente nao deve:

- converter mg em comprimidos ou mL sem concentracao/apresentacao;
- afirmar que uma associacao e segura pela simples ausencia de alerta local;
- inventar estudos, doses ou dados de prontuario;
- usar artigo pendente ou rejeitado;
- treinar globalmente com prontuarios ou feedbacks de clientes.

Casos clinicos permanecem isolados por tenant. Um futuro conjunto de avaliacao
anonimizado exige consentimento, remocao de identificadores, revisao humana e
trilha de auditoria; nao deve ser criado automaticamente a partir do uso.

## Fontes oficiais previstas

- DailyMed/FDA para rotulos veterinarios dos Estados Unidos.
- VMD Product Information Database para produtos autorizados e SPCs do Reino
  Unido, sob Open Government Licence v3.0.
- PubMed/NLM para literatura cientifica.
- MAPA/SIPEAGRO para produtos brasileiros quando houver um conjunto oficial que
  represente produtos e bulas, e nao apenas estabelecimentos.
- Union Product Database/EMA para medicamentos veterinarios europeus.

Antes de uma liberacao ampla, a equipe clinica precisa revisar uma amostra
representativa, aprovar protocolos de alto risco e executar a avaliacao
reproduzivel:

```powershell
docker exec petshop-dev-backend python -m app.scripts.evaluate_vet_assistant
```
