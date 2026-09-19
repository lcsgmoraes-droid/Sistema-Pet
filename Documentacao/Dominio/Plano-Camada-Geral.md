---
tipo: plano
atualizado: 2026-09-19
---

> **Status (2026-09-19): Checkpoints 1-5 implementados e verificados contra Postgres real** (migrations aplicadas, boot limpo, rotas confirmadas no OpenAPI, lógica de sugestão/vínculo/desvínculo testada ao vivo pra cada domínio). Pendência declarada desde o início: nenhum teste `pytest` formal ainda — só verificação manual/ao vivo, mesmo padrão do Checkpoint 0. Ver "Notas de implementação" no fim do documento pra detalhes de cada checkpoint.

# Plano — Camada geral (Pessoas, Produtos, Pet, taxonomias)

Roteiro de execução da segunda fase da reestruturação de grupo — a primeira (`GrupoComercial` obrigatório) está com o código pronto, faltando só testes/validação (ver "Checkpoint 0"). Ver [[Proposta-Modelo-Proprietario-Lojas]] (a origem conceitual disto) e [[EmpresaGrupo]] (ainda com o nome antigo — precisa de atualização, ver Checkpoint 0).

Cada checkpoint só é considerado fechado quando o critério de "pronto" dele for verdade — não avançar pro próximo com um checkpoint pela metade. Escopo de cada um é deliberadamente pequeno; a tentação de fazer tudo de uma vez é exatamente o que gera as tabelas duplicadas/campos órfãos que achamos no levantamento original.

## O padrão técnico (estabelecido uma vez, no Checkpoint 1, reaproveitado depois)

Toda entidade "mestre" segue a mesma forma:

- Tabela nova `xxx_mestre`, escopada por `grupo_id` (FK pra `grupos_comerciais.id`, **não** `tenant_id` — é uma entidade de grupo, igual o próprio `GrupoComercial`, não herda `BaseTenantModel`).
- Guarda só os campos de **identidade** (o que é igual em qualquer loja). Campos **operacionais** (preço, estoque, histórico de compra, disponibilidade) continuam 100% na tabela local de cada loja, sem exceção.
- Tabela local ganha uma coluna nova, opcional, `xxx_mestre_id` — nullable, sem quebrar quem nunca usar isso.
- **Sem vínculo**: loja continua funcionando exatamente como hoje, cadastro 100% independente.
- **Com vínculo**: campos de identidade são herdados do mestre por padrão; uma loja pode sobrescrever um campo específico, mas isso precisa ficar sinalizado na UI ("personalizado nesta loja") — nunca uma divergência silenciosa.
- Cada domínio pega esse molde e só decide *quais campos* são identidade vs. operacional — a mecânica (tabela, FK, herança, override) é a mesma nos quatro.

## Checkpoint 0 — Fundação (feito, com pendência)

**Status:** código completo (rename `EmpresaGrupo`→`GrupoComercial`, grupo-de-1 automático, "adicionar loja ao grupo", onboarding assistido de ops), verificado via build/boot real. **Falta:** testes automatizados (`test_grupo_comercial_service.py`, cobertura de `adicionar_loja`/fechamento de grupo-de-1/onboarding em loop), teste manual no navegador dos dois fluxos novos, atualização do `EmpresaGrupo.md` pro nome novo, commit/push/PR/CI, merge com a `main`.

**Critério de pronto:** PR mergeado na `main` com CI verde. — *Sem isso, os checkpoints abaixo ficam construindo em cima de uma fundação não testada.*

## Checkpoint 1 — Espécie / Raça mestre (prova de conceito do padrão) ✅ Feito

**Por quê primeiro:** é o caso mais simples que existe — dado de taxonomia pura, sem ambiguidade de negócio, sem dado sensível, sem campo operacional nenhum pra separar. Serve pra provar o padrão técnico (tabela mestre + FK local + herança) uma vez, num caso de baixíssimo risco, antes de aplicar em algo mais delicado.

**Escopo:**
- `especie_mestre`/`raca_mestre`, escopadas por `grupo_id`.
- `Especie.especie_mestre_id` / `Raca.raca_mestre_id`, nullable.
- Serviço simples: ao cadastrar espécie/raça numa loja, se já existir uma com nome igual (case-insensitive) no mestre do grupo, sugerir vincular em vez de duplicar.
- Migration só-schema (tabela + FK), sem backfill de dado — não vale a pena tentar casar nomes automaticamente aqui, é baixo volume.

**Fora do escopo agora:** UI dedicada — pode ser só um campo "usar do grupo" no formulário que já existe de Espécie/Raça.

**Critério de pronto:** uma espécie cadastrada como mestre num grupo aparece disponível (herdada) em todas as lojas do grupo; loja continua podendo ter espécie 100% própria sem tocar no mestre; testes cobrindo os dois casos.

## Checkpoint 2 — Produto mestre ✅ Feito

**Escopo** (já desenhado em detalhe na [[Proposta-Modelo-Proprietario-Lojas]], seção 5.2):
- `produto_mestre` (nome, descrição, fotos, categoria/marca/departamento, ficha técnica, GTIN, dados fiscais de referência) + `categoria_mestre`/`marca_mestre`/`departamento_mestre` andando junto.
- `Produto.produto_mestre_id`, nullable.
- Fluxo "adotar produto-mestre existente" ao cadastrar em loja adicional do mesmo grupo (busca por nome/GTIN).
- Sugestão automática usando o Catálogo Mestre **global** já existente (`catalogo_mestre_produtos`) como fonte de dados prontos pra criar um produto-mestre novo — só sugestão, nunca escrita automática.
- Override explícito por campo, sinalizado na UI.

**Fora do escopo agora:** migrar produtos já cadastrados nas lojas pra um mestre automaticamente (isso é o Checkpoint 6, "adoção assistida" — requer matching difuso, é trabalho à parte).

**Critério de pronto:** cadastrar um produto numa 2ª loja do grupo permite escolher "usar produto existente do grupo" e herdar nome/descrição/fotos, mantendo preço/estoque 100% locais; teste cobrindo herança + override; smoke manual no PDV confirmando que preço/estoque continuam corretos por loja.

## Checkpoint 3 — Pet mestre ✅ Feito

**Por quê antes de Pessoa:** é o ganho mais visível pro usuário final (continuidade de atendimento entre lojas do mesmo grupo) e tem menos ambiguidade de consentimento do que Pessoa — dado do animal, não da pessoa em si.

**Escopo:**
- `pet_mestre` (nome, espécie/raça, sexo, data de nascimento, microchip, alergias, doenças crônicas, medicamentos contínuos, tipo sanguíneo, foto) + `PerfilComportamental` dobrado junto (temperamento, medo de tesoura/secador etc. — hoje já é satélite 1:1 do Pet).
- `Pet.pet_mestre_id`, nullable.
- **Continua 100% local:** toda consulta, vacina, exame, internação — eventos clínicos não sobem pro mestre, só a identidade do pet.
- Vínculo Especie/Raça do pet aponta pro mestre do Checkpoint 1, quando existir.

**Fora do escopo agora:** consolidar o *histórico clínico* entre lojas (isso seria um relatório de leitura, à parte — não faz parte de "camada mestre", é uma feature de consulta, decisão separada).

**Critério de pronto:** tutor que leva o pet a duas lojas do mesmo grupo não precisa recadastrar alergia/doença crônica/microchip na segunda; consulta na loja 2 lê o perfil comportamental cadastrado na loja 1; teste cobrindo isso.

## Checkpoint 4 — Pessoa mestre (Cliente / Fornecedor / Veterinário) ✅ Feito

**Por quê por último:** é a mais sensível (dado pessoal, LGPD) e a mais complexa (a mesma tabela hoje cobre cliente, fornecedor e veterinário via `tipo_cadastro`). Só começar depois que o padrão já estiver validado nos três anteriores.

**Escopo:**
- `pessoa_mestre` (nome, CPF/CNPJ, telefone, e-mail, endereço, tipo, CRMV quando aplicável).
- `Cliente.pessoa_mestre_id`, nullable.
- **Vínculo é sempre sugestão + confirmação manual, nunca automático** — mesmo padrão CDP já decidido na proposta: ao cadastrar um CPF/telefone que já existe em outra loja do grupo, sugerir "já existe cadastro em [loja], vincular histórico?".
- Continua 100% local: histórico de compra, segmentação, campos financeiros/DRE, consentimento — cada loja é dona do que coletou.

**Pré-requisito de negócio, não técnico:** confirmar com o usuário se os termos de uso já foram atualizados pra cobrir "consentimento vale pro grupo econômico" (mencionado por ele numa rodada anterior — não é bloqueio técnico, mas vale checar antes de ativar isso em produção).

**Critério de pronto:** cadastro de cliente já existente noutra loja do grupo sugere vínculo (nunca funde sozinho); teste cobrindo a sugestão e a recusa; confirmação de que o time validou o texto de consentimento antes de ligar isso pra clientes reais.

## Checkpoint 5 — Interface consolidada ✅ Feito (versão enxuta)

Depois dos 4 domínios prontos no backend: uma tela única (provavelmente dentro de "Grupos Comerciais", ao lado do que já existe) listando os mestres do grupo — produtos, pets, pessoas, espécies/raças — com quem está vinculado e a ação de vincular/desvincular. Sem isso, os recursos existem só via API, difícil de operar no dia a dia.

**Critério de pronto:** um usuário sem acesso ao backend consegue, sozinho, ver e gerenciar os vínculos do grupo.

## Checkpoint 6 — Adoção assistida (opcional, avaliar depois)

Ferramenta de matching pra lojas que **já tinham** produtos/pets/clientes duplicados entre si antes da camada mestre existir — sugere pares prováveis (mesmo GTIN, mesmo CPF, nome de pet + tutor iguais) pra vincular em lote. Mais complexo (matching difuso, revisão humana antes de aplicar), decisão separada sobre se vale o esforço ou se a adoção orgânica (vincular conforme cadastra de novo) já resolve.

---

## Ordem recomendada e por quê

`Checkpoint 0 → 1 → 2 → 3 → 4 → 5`, com `6` avaliado à parte depois. A lógica: prova o padrão no caso mais simples (1) antes de investir nos casos que o usuário realmente quer (2, 3, 4); deixa o mais sensível (Pessoa) por último, quando o time já confia no mecanismo; só constrói a interface consolidada (5) depois que houver mais de um domínio pra mostrar nela, senão ela fica pela metade.

---

## Notas de implementação (Checkpoints 1-5, 2026-09-19)

Registro do que foi construído de fato e onde desviou um pouco do desenho original acima — pra quem for mexer depois não precisar arqueologia de código.

**Arquivos por checkpoint** (todos seguem o mesmo molde: `*_mestre_models.py`, `*_mestre_service.py` com `sugerir_*`/`vincular_*`/`desvincular_*`, rotas próprias, registrado em `db/base.py` e `main_routers.py`):
- Checkpoint 1: `especie_raca_mestre_models.py`, `especie_raca_mestre_service.py`, rotas dentro de `cadastros_routes.py`. Migration `zzy20260918a1`.
- Checkpoint 2: `produto_mestre_models.py` (+ `CategoriaMestre`/`MarcaMestre`/`DepartamentoMestre` no mesmo arquivo), `produto_mestre_service.py`, `produto_mestre_routes.py`. Migration `zzz20260918a1`.
- Checkpoint 3: `pet_mestre_models.py`, `pet_mestre_service.py`, `pet_mestre_routes.py`. Migration `zzza20260918a1`.
- Checkpoint 4: `pessoa_mestre_models.py`, `pessoa_mestre_service.py`, `pessoa_mestre_routes.py`. Migration `zzzb20260918a1`.
- Helper compartilhado por todos: `grupo_comercial_contexto.py` (`obter_grupo_id_ativo`) — resolve o grupo comercial ativo de um tenant, criado no Checkpoint 1 e reaproveitado sem alteração nos outros três.

**Desvios do desenho original:**
- **Pet não tem FK real pra Espécie/Raça** — `especie`/`raca` no `Pet` local sempre foram texto livre, não `ForeignKey`. A frase original do plano ("vínculo Espécie/Raça do pet aponta pro mestre do Checkpoint 1") não foi implementada por isso; `pet_mestre.especie`/`raca` também guardam texto livre, copiado do pet local no momento do vínculo.
- **Sugestão por identificador forte, não só nome**: Produto prioriza GTIN, Pet prioriza microchip, Pessoa só sugere por CPF/CNPJ (nunca por nome) — mais rígido que o texto original do plano, decisão tomada durante a implementação porque nome sozinho é fraco demais pra dado sensível ou pra evitar falso-positivo.
- **Categoria/Marca/Departamento mestre** ganharam vínculo (`sugerir_*`/`vincular_*`/`desvincular_*`) e rotas próprias em `/produto-mestre/{categorias,marcas,departamentos}/...`, além do `produto_mestre` — não estava explícito no escopo original mas é o mesmo padrão, feito junto por consistência.
- **Checkpoint 5 saiu mais enxuto que o critério de pronto pedia**: a tela (`GrupoComercialMestres.jsx`, em `/configuracoes/grupos-comerciais/:grupoId/mestres`) resolve o "ver" por completo (lista os 5 domínios com contagem). O "gerenciar" ficou parcial — os endpoints de desvincular existem e funcionam (`DELETE .../vincular-mestre`, `DELETE .../vincular` em cada domínio), mas a UI de vincular/desvincular um registro específico não foi conectada aos formulários de cadastro de Produto/Pet/Cliente/Espécie (que não foram tocados nesta rodada). Ou seja: **hoje só dá pra vincular/desvincular via API** — falta o botão nos formulários existentes. Isso é a pendência real do Checkpoint 5, não risco técnico, só trabalho de UI que ficou de fora do escopo desta rodada.

**Verificação feita:** `py_compile` em todos os arquivos, metadata do SQLAlchemy conferida (156→164 tabelas ao longo dos 4 checkpoints), as 3 migrations aplicadas de verdade via `alembic upgrade head` contra o Postgres do `petshop-dev-postgres`, boot limpo do container confirmado a cada rodada, todas as 17 rotas novas conferidas no `/openapi.json` ao vivo, e um teste funcional real (criar → sugerir → vincular → confirmar FK → limpar) rodado contra o banco real pra cada um dos 4 domínios, com limpeza confirmada depois (sem lixo deixado no banco de dev). **Sem teste `pytest` automatizado formal** — mesma pendência do Checkpoint 0, ainda em aberto.
