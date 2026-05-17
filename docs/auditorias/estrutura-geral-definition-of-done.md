# Definition of Done - refatoracao modular

Data: 2026-05-16

Este checklist deve ser usado em toda refatoracao estrutural do Sistema Pet,
principalmente no piloto de Produtos definido em
`docs/auditorias/estrutura-geral-inventario.md`.

## Principio

Refatoracao estrutural so esta pronta quando reduz acoplamento sem alterar
comportamento observavel. Se mudar regra de negocio, deixa de ser refatoracao e
vira feature/fix com teste proprio e comunicacao explicita.

## Antes de mexer

- [ ] Confirmar branch de tarefa fora da `main`.
- [ ] Rodar `scripts/validar_fluxo.ps1 -PermitirAlteracoesLocais`.
- [ ] Identificar endpoints, telas, jobs e integrações afetadas.
- [ ] Listar contratos publicos que nao podem mudar: URL, payload, status code,
  permissoes, eventos de auditoria, efeitos em banco e mensagens principais.
- [ ] Criar ou escolher testes focados para o comportamento que sera preservado.
- [ ] Definir uma fatia pequena o bastante para um PR curto.

## Padrao de modulo

Backend:

- `routes.py`: HTTP, dependencias, auth e serializacao.
- `schemas.py`: entrada/saida Pydantic.
- `services.py`: regra de negocio e orquestracao.
- `repositories.py` ou `queries.py`: acesso a banco quando a query for
  compartilhada ou complexa.
- `events.py`: auditoria/eventos de dominio quando existir efeito operacional.
- `tests/`: contrato de endpoint e unitarios dos services puros.

Frontend:

- `index.ts` ou `index.js`: superficie publica da feature.
- `pages/`: tela roteavel.
- `components/`: componentes sem regra de negocio pesada.
- `hooks/`: estado, busca e efeitos colaterais da tela.
- `services/`: chamadas HTTP e adaptadores.
- `utils/`: funcoes puras testaveis.

## Durante a refatoracao

- [ ] Mover codigo sem alterar nomes de campos nem payloads.
- [ ] Manter rotas antigas apontando para a nova camada enquanto o contrato nao
  for explicitamente alterado.
- [ ] Evitar misturar limpeza estetica com quebra estrutural.
- [ ] Remover duplicacao apenas quando a origem da regra estiver clara.
- [ ] Preservar auditoria, tenant, permissoes e `request_id`/`correlation_id`.
- [ ] Atualizar imports com escopo minimo.
- [ ] Nao apagar codigo antigo antes dos testes cobrirem o caminho movido.

## Depois de mexer

- [ ] Rodar testes focados do modulo.
- [ ] Rodar `scripts/validar_fluxo.ps1 -PermitirAlteracoesLocais`.
- [ ] Conferir diff procurando mudanca acidental de contrato.
- [ ] Atualizar docs/checklist quando o padrao do modulo evoluir.
- [ ] Registrar no PR qual comportamento foi preservado e quais testes provam.

## Piloto Produtos

Primeira fatia permitida:

- Extrair consultas/listagens puras de `backend/app/produtos_routes.py`.
- Manter endpoints, payloads, filtros, paginacao e status code iguais.
- Nao mexer ainda em PDV, venda, estoque critico ou importacao fiscal.

Testes minimos antes do merge:

- Listagem de produtos preserva filtros principais.
- Busca por identificador/codigo preserva retorno.
- Permissao/tenant continuam obrigatorios.
- Nenhum evento sensivel perde auditoria.

## Bloqueadores

Parar e abrir nova tarefa se aparecer:

- Alteracao necessaria de schema de banco.
- Mudanca de contrato HTTP.
- Mudanca em regra de preco, estoque, pagamento, cupom ou fiscal.
- Falta de teste para comportamento que sera movido.
- Arquivo tocado por outra frente ativa.

## Manutencao do 10/10 estrutural

Depois dos PRs #89 a #95, o padrao modular esta provado em Produtos, Estoque,
PDV/vendas, campanhas/cupons e financeiro. Para manter a nota estrutural:

- Arquivo acima de 2.000 linhas nao deve receber nova regra de negocio sem
  plano de extracao ou justificativa no PR.
- Helper puro novo em rota critica deve nascer em modulo dedicado quando for
  reutilizavel, testavel isoladamente ou sensivel para dinheiro/estoque/cupom.
- Toda extracao deve preservar endpoint, payload, permissao, tenant e auditoria.
- O PR deve citar quais testes provam que o comportamento foi preservado.
- Duplicacao de regra em frontend deve apontar para service/helper central ou
  abrir tarefa de consolidacao.

