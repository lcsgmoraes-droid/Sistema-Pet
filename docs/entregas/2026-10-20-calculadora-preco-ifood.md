# Calculadora de preço iFood na central

| Campo | Valor |
|---|---|
| Data | 2026-10-20 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Branch | `codex/ifood-calculadora-central` |
| Tipo / risco | Funcionalidade e integração / médio, preço e isolamento entre lojas |
| Domínios | Produto canônico, catálogo iFood e contribuição estimada |

## 1. Necessidade e aceite

Permitir experimentar preços na central antes de aplicá-los, vendo contribuição
e pendências e mantendo um único cadastro do produto. Aceite: simular não grava;
aplicar altera somente `preco_ifood`; reabrir o cadastro e consultar a central
mostram o mesmo preço. Controles V2, permissão por tenant, cancelamento de
respostas antigas e distinção entre preço salvo/simulado são obrigatórios.
Esta branch também incorpora a base de cadastro/central validada em 19/10,
que não estava presente na main de início desta entrega (`f10277690`).

## 2. Regras e dados

Preço específico prevalece; nulo segue ERP regular + acréscimo. Zero é pendência
de canal, sem bloquear o salvamento válido do ERP. Simulação não altera custo,
ERP/app/ecommerce, estoque, taxas, seleção, pausa ou promoção. A contribuição
usa o preço efetivo, incluindo promoção iFood vigente. Dados ficam na loja
proprietária do produto; produto compartilhado de outra loja não é editado pelo
simulador. Nenhum dado pessoal novo.

## 3. Arquitetura e integração

`IfoodProdutoDetalhes` incorpora a calculadora de domínio usando os componentes
V2. `POST /integracoes/ifood/catalogo/produto/simular-preco` aceita somente ID e
preço, lê os demais dados no ERP e chama a fonte de cálculo compartilhada.
`saved_specific_price` distingue o dado persistido do preço virtual. Aplicação
usa `updateProduto`/PUT canônico com um único campo. Sem chamada externa iFood.
Erros de consulta impedem aplicar uma estimativa antiga; a interface permite
tentar novamente. Promoção e custo de kit usam as mesmas regras do cadastro.

## 4. Segurança e privacidade

Simulação exige `produtos.visualizar`; aplicação exige `produtos.editar` no
endpoint existente. Payload fechado rejeita custo/taxas e outros campos.
ID fora do tenant retorna 404; usuário com visualização pode simular sem ganhar
permissão de alterar produtos. Credenciais continuam apenas no ambiente local,
sem logs ou arquivos versionados contendo segredo.

## 5. Qualidade

Testes cobrem simulação sem persistência, preço 0/nulo/específico, permissões,
tenant, promoção, reservas/kits e cálculo compartilhado. São executados os testes
de regressão de cadastro/clonagem/recorrência/datas, lint e build. A jornada em
navegador comprova simulação descartável e aplicação com recarga do cadastro.
Resultados finais no [registro de homologação](../homologacoes/2026-10-20-calculadora-preco-ifood.md).

## 6. DEV e homologação

Projeto local separado `corepet-ifood-dev`, porta 18081, com tenant fictício e
volumes próprios. Preserva a homologação 18080 e o checkout de outros trabalhos.
Fonte usada no rebuild: worktree desta branch, com override local do Compose
oficial fora do Git. Escrita/operação/polling iFood permanecem desativados.

## 7. Publicação e rollback

Frontend/backend e migration de convergência. A revisão `zzzzg20261019a1`
permanece imutável; `zzzzl20261020a1` une essa linha à evolução XML já presente na
main. Há uma única head. A validação local parte do banco que já tinha g, sem
reaplicar a inclusão das colunas. Rollback preferencial: código/imagens anteriores,
preservando colunas; downgrade exige avaliação da perda dos campos iFood.
Produção, merge e ativação do provedor não fazem parte desta entrega.

## 8. Observabilidade e sustentação

Preço salvo e simulação têm identificação própria; salvar atualiza a central.
Erros de simulação/gravação ficam visíveis. Memória da contribuição mostra as
parcelas e as premissas; mensalidade e custos por pedido continuam fora dessa
estimativa unitária. Não há confirmação fictícia de anúncio publicado.

## 9. Comunicação

Orientar: abrir a calculadora na ação do produto, experimentar preço, conferir a
modalidade e usar Aplicar somente quando quiser mudar a oferta. Fechar sem aplicar
preserva o preço salvo. O cadastro completo segue no componente existente.

## 10. Fechamento

Validação técnica aprovada: 35 testes backend, 28 de regressão frontend,
contrato de rotas, lint e build passaram; migration aplicada até a head de
convergência e E2E do Plano Básico aprovado. No Chrome, simular 100/zero preservou
o salvo 150; aplicar 120 atualizou o cadastro, e aplicar 150 restaurou a oferta
final. O preço ERP 100, custo 60 e estoque 4 permaneceram intactos.

Calculadora disponível em DEV para aceite do Lucas. Nenhuma alteração em
produção ou ativação de envios ao iFood autorizada.
