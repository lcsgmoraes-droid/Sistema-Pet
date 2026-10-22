# Homologação — preparação de release do cadastro e da central iFood

| Campo | Valor |
|---|---|
| Data / executor | 2026-10-20 / Codex |
| Responsável de negócio | Lucas |
| Branch / PR | `codex/ifood-calculadora-central` / #1533 |
| Ambiente integrado | DEV `corepet-ifood-dev`, `http://127.0.0.1:18081` |
| Escopo | Cadastro canônico, central, calculadora e atualização local das promoções |

## Critérios e resultados

| Cenário | Evidência | Resultado |
|---|---|---|
| Preço específico, regra da loja, promoção, margem e pendências | 83 contratos backend iFood, incluindo 36 novos casos | Aprovado |
| Frações de centavo | Valores 0,004/0,005 e fronteiras do desconto são arredondados antes de validar; promoção inválida não fica elegível | Corrigido e aprovado |
| NaN, infinito, preços enormes e premissas inválidas | HTTP 422 em entradas inválidas; legado fora da faixa vira pendência sem erro 500 ou fallback silencioso | Corrigido e aprovado |
| Datas extremas | Conversão UTC impossível retorna 422; fim máximo representável não tenta agendar um instante impossível | Corrigido e aprovado |
| Produto agrupador legado | Tipo PAI bloqueado na central e no catálogo mesmo com flags antigas inconsistentes | Corrigido e aprovado |
| Tenant, permissões e cliente externo | Simulação sem persistência; permissões distintas; tentativa de envio bloqueada; teste falha se o cliente externo for aberto | Aprovado |
| Respostas fora de ordem, troca da oferta e rascunhos | 10 novos testes do hook real da calculadora com APIs simuladas; nenhuma resposta antiga substitui a atual | Aprovado |
| Gravação concorrente e falha no PUT | Duplo clique gera um único PUT contendo somente preco_ifood; falha não confirma sucesso e preserva o valor | Aprovado |
| Datas, timers, segundo plano, margem e cadastro | `npm run test:ifood`: 58 testes, sem skip | Aprovado |
| Compatibilidade do helper de testes | 44 testes dos consumidores do harness, executados na revisão frontend | Aprovado |
| Perda de conexão real da aba | Chrome CDP offline apenas nas duas abas DEV: avisos de dados antigos, aplicação bloqueada e rascunhos mantidos | Aprovado |
| Recuperação da conexão | Rede restaurada, reconsulta por Tentar novamente/foco; oferta150, simulação160, contribuições46,50/31% e53,80/33,63%; nome e busca intactos | Aprovado |
| Simulação de zero na versão reconstruída | Oferta salva150 mantida; resultado0, margem não calculada e pendência que impede envio; input restaurado a160 sem aplicar | Aprovado |
| Jornada integrada do Plano Básico | Teste oficial `test_plano_basico_e2e.py -m e2e_long`: 1 aprovado, com outra identidade/tenant fictícios no18081 | Aprovado |
| Regressão geral | 203 smoke tests aprovados/2 skips; 761 multitenant aprovados/22 skips; import do backend aprovado | Aprovado |
| App mobile | Auditoria, typecheck e 97 testes aprovados; nenhum build, OTA ou submissão | Aprovado |
| Lint, formato e build | Ruff global, ESLint global, Prettier global e build de produção aprovados | Aprovado |
| Dependências | Backend sem vulnerabilidades conhecidas no audit; gates frontend/mobile aprovados após patch follow-redirects1.16.1 | Aprovado |
| Migrações e artefatos | Uma head `zzzzm20261020a1`; estrutura validada; nenhum dump, segredo ou build rastreado | Aprovado |
| Persistência após rebuild e testes | SQL somente leitura às 16:36:31 Brasília: produto2 com nome original, ERP100/custo60/iFood150/promo120/estoque4/foto/seleção e sem pausa; três flags externas false | Aprovado |

As viradas reais em primeiro/segundo plano constam na
[homologação das promoções](2026-10-20-atualizacao-automatica-promocao-ifood.md).
Os testes novos de hook simulam rede/tempo; a perda de conexão também foi
verificada no Chrome real, sem recarregar os documentos ou salvar seus rascunhos.

## Correções e preparação do ambiente

- Faixa monetária interna iFood de até R$ 999.999.999,99 em módulo, antes dos cálculos. O cadastro admite preço negativo dentro da faixa como pendência; simular preço exige valor não negativo. As regras gerais do ERP não foram alteradas.
- Cinco arquivos backend ajustados ao formato já exigido pelo CI. Sem mudança funcional nas linhas apenas reformatadas de cadastro/modelo/estoque.
- `follow-redirects` 1.16.0→1.16.1 nos locks frontend/mobile, mantendo axios e as demais versões. Corrige GHSA-Q3JH-WRC6-JGQ8 e GHSA-8R9P-F939-6H3C; não adiciona exceção à auditoria.
- Python isolado em backend/.venv com requirements/lock atuais e instalações npm próprias deste worktree. A antiga junction frontend foi removida somente no worktree; o node_modules do checkout original foi preservado. Nenhuma dependência global atualizada.
- Backend/frontend reconstruídos pelo Compose exclusivo do18081, com containers saudáveis. Sem alteração no18080 ou em produção.
- Baterias iFood adicionadas ao Smoke CI, Backend CI e script oficial de validação de release, para execução futura obrigatória.

## Comandos reproduzíveis

```powershell
npm --prefix frontend run test:ifood
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit/test_ifood_management.py tests/unit/test_ifood_catalog_contract.py tests/unit/test_ifood_routes_contract.py tests/unit/test_ifood_orders_contract.py tests/unit/test_ifood_client_contract.py -q
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\fluxo_unico.ps1 -Acao release-check
```

O E2E usa exclusivamente E2E_BASE_URL/E2E_USER_EMAIL/E2E_USER_PASSWORD/E2E_TENANT_ID
do tenant fictício, sem credenciais no código ou nesta ficha. Não apontar a jornada
para produção. Evidências visuais locais deste chat: `ifood-release-rede-indisponivel-dev-2026-10-20.png`,
`ifood-release-rede-recuperada-dev-2026-10-20.png` e `ifood-release-preco-zero-dev-2026-10-20.png`.

## Limites e decisão

Os skips da suíte geral correspondem a pré-condições próprias de testes de
integração legados; não estão contados como testes aprovados. Os 83 contratos
iFood, os 58 testes frontend e o E2E no PostgreSQL DEV não tiveram skips.
As exceções pré-existentes dos audits permanecem documentadas nos scripts:
braces em ferramentas de build e backport mobile de node-forge. O audit frontend
aplica seu limiar vigente de severidade moderada; avisos baixos não são bloqueadores.
O build mantém o aviso pré-existente de chunk PDV maior que500KB.

Preparação local aprovada para revisão final do PR e publicação no CorePet após
os checks do commit final. Isso não habilita publicação/operação real no iFood:
as três flags externas permanecem false. Migrações continuam aditivas; rollback
preferencial é código/imagem anterior, preservando os campos e dados.
Merge e deploy de produção não foram executados e exigem autorização específica.
