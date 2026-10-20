# Cancelamento da venda após cancelamento fiscal

## Identificação

- Data: 2026-10-20.
- Responsável de negócio: Lucas. Executor técnico: Codex.
- PR: #1526, na branch de tarefa já existente.
- Prioridade: P1. Risco: médio, pois a ação estorna estoque e lançamentos financeiros.
- Domínios: PDV, fiscal, estoque e financeiro.

## 1. Necessidade e critérios de aceite

O PDV podia manter a nota como Autorizada e a venda como `pago_nf` após o
cancelamento fiscal. A tela não oferecia uma ação de cancelamento da venda.

- Consultar o emissor ao abrir uma venda com documento fiscal e ao retornar à aba.
- Exibir Cancelada somente após a confirmação do emissor.
- Disponibilizar **Cancelar venda** diretamente, com confirmação e justificativa,
  sem precisar reabrir a venda.
- Bloquear notas vigentes e preservar vendas já canceladas ou devolvidas.
- Estornar estoque uma única vez, inclusive quando um webhook Bling antigo já
  devolveu parte ou toda a quantidade.

## 2. Regras e dados

O cancelamento fiscal apenas libera a trava `pago_nf`; o cancelamento comercial
continua sendo uma ação explícita. Preserva o documento e o histórico da venda.
O serviço valida a situação fiscal antes dos estornos e mantém as verificações
de devolução e empresa. Não há migration, importação ou alteração de credenciais.

Os estornos fiscais legados são consultados por empresa de estoque, venda,
produto, tipo de referência e situação, consumindo a quantidade já devolvida
somente uma vez entre itens repetidos.

## 3. Contratos e integrações

Reutiliza GET `/nfe/vendas/{id}/status` para IntNFe e POST
`/nfe/{id}/sincronizar-status` para Bling. Uma solicitação aceita de cancelamento
Bling permanece pendente até a consulta confirmar a situação fiscal.

Se o emissor estiver indisponível, a venda continua acessível com a última situação
registrada e aviso explícito. **Atualizar situação** permite repetir a consulta.
Respostas antigas não podem substituir outra venda selecionada nem regredir o
cancelamento confirmado do mesmo documento.

## 4. Segurança e privacidade

Reutiliza autenticação, empresa da sessão e os filtros existentes. Não há acesso
ao servidor de produção, consulta à venda real da Tecnoagro, emissão fiscal,
cancelamento real ou restituição externa de Pix/cartão nesta validação. Os testes
de navegador usam APIs simuladas, dados fictícios e token sintético sem validade.

## 5. Desenvolvimento e qualidade

Testes backend cobrem solicitação pendente e cancelamento confirmado em ambos os
emissores, bloqueio antes dos estornos, preservação de cancelamentos/devoluções,
reabertura legada e estoque já devolvido completo, parcial e em itens repetidos.

Testes frontend cobrem atualização fiscal, falha e recuperação, proteção de
respostas atrasadas, concorrência na seleção da venda e ação direta com
confirmação/justificativa. O navegador Chrome executa o PDV real contra API em
memória, sem backend e sem dados reais.

Resultado final: **103 testes backend**, **38 testes frontend** e **4 cenários
Chrome** aprovados, com ESLint/Ruff e build frontend aprovados. A regressão de
concorrência backend usa duas sessões SQLAlchemy reais: enquanto uma consulta
aguarda o emissor, outra sessão cancela/devolve a venda; a confirmação fiscal
posterior preserva o estado comercial mais novo.

Comandos de verificação:

```powershell
# backend
.\.venv\Scripts\python.exe -m pytest tests/unit/test_venda_cancelamento_fiscal.py tests/unit/test_vendas_cancelamento_com_devolucao.py tests/unit/test_intnfe_emission.py tests/unit/test_nfe_operacional_routes_contract.py -q

# frontend
node --test src/utils/pdvFiscalRefresh.test.mjs src/utils/pdvFiscalStatus.test.mjs src/components/pdv/PDVModoVisualizacaoBanner.test.mjs src/hooks/usePDVVendaCarregamento.test.mjs src/utils/pdvCancelarEdicaoVenda.test.mjs src/utils/pdvReturnRefresh.test.mjs src/utils/pdvReturnEligibility.test.mjs
node node_modules/@playwright/test/cli.js test tests/e2e/pdv-nota-cancelada.spec.js --reporter=list
npm run build
```

O E2E exige `E2E_BASE_URL` explícita em localhost e rejeita destino remoto.
ESLint/Prettier e Ruff são aplicados aos arquivos da correção.

## 6. Homologação local

| Cenário | Evidência | Resultado |
|---|---|---|
| Autorizada armazenada, cancelada no emissor | E2E Chrome | Cancelada aparece; cancelamento direto disponível |
| Confirmação e justificativa | E2E Chrome | Texto curto bloqueado; POST cancelar enviado sem reabrir |
| Nota ainda autorizada | E2E Chrome | Cancelamento indisponível; retorno à aba atualiza situação |
| Devolução anterior | E2E Chrome | Cancelamento direto indisponível |
| Emissor indisponível | E2E Chrome | Aviso e última situação; atualização recupera estado confirmado |

Massa: loja e venda sintéticas. Ambiente: frontend local, mocks de emissor/API e
testes automatizados. Aceite de negócio e verificação da venda real permanecem
pendentes; não se afirma homologação no tenant de produção.

## 7. Publicação e rollback

Entrega web/backend sem mudança mobile ou migration. Publicação depende de revisão
do PR, checks, merge e autorização explícita de Lucas pelo fluxo oficial. Não há
autorização de produção neste registro. O rollback de código preserva documentos
e histórico; conferir estoque antes de repetir qualquer operação comercial.

## 8. Observabilidade e sustentação

A venda cancelada mantém justificativa, usuário e data pelo serviço existente.
Falha do emissor é visível no PDV. Uma nota cancelada com venda vigente deve
mostrar a ação direta; uma venda cancelada não deve reabrir por consulta fiscal.

## 9. Limites e pendências

- A restituição efetiva de Pix/cartão continua fora do cancelamento interno.
- Uma rodada adicional de testes de cashback encontrou falha anterior de preparo
  SQLite: FK para `produto_identidades` sem a tabela na fixture; essa infraestrutura
  não faz parte desta correção.
- Callbacks de comissão/entregador/contexto já iniciados não suportam aborto;
  as respostas de carregamento não podem trocar a venda selecionada ou encerrar
  o loading de uma consulta mais nova.
- A branch/PR existente já apresenta conflitos com a main no trabalho anterior
  de XML/iFood. A integração dessas frentes requer conciliar também o histórico
  de migrations antes da publicação; não foi misturada a esta correção do PDV.
