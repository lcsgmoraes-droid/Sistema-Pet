# Cadastro de produto e central do iFood

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Branch | `feat/20261019-1708-cadastro-e-central-ifood` |
| Prioridade / risco | P2 / médio: preços, catálogo e isolamento entre lojas |
| Domínios | Produtos, estoque derivado, integração iFood |

## 1. Necessidade e requisitos

Preparar o iFood a partir do cadastro existente, sem duplicar produtos ou formulários.
Usuários configuram seleção, preço próprio e promoção no cadastro; na central,
consultam preços, contribuição, estoque e pendências e acessam a edição canônica.
Requisitos: controles V2, cálculos iguais nas duas superfícies, persistência local,
paginação/busca, custos desconhecidos distinguíveis de zero e isolamento por loja.
Aceite: salvar/reabrir, calcular nos dois cenários, listar pendências e preservar
app/ecommerce/ERP. Envio real, catálogo remoto, conciliação e pedidos no PDV ficam
fora desta entrega.

## 2. Regras de negócio e dados

Produto é a entidade canônica. Seleção iFood inicia falsa; preço nulo segue ERP
regular + acréscimo, preço específico prevalece; zero explícito gera pendência.
Promoção tem período próprio e não herda descontos de outros canais. Custo zero
inicial do ERP é tratado como não informado; taxas e despesa unitária aceitam
zero explícito. A meta avisa, sem impedir salvar ou tornar o item inapto.

Estoque desconta reservas e segurança, com capacidade dos componentes em kits
virtuais. Custos de kits seguem o serviço existente. Pausa não é removida por
reposição. Produto compartilhado de outra loja não recebe configurações iFood
da loja atual: é preciso cadastrá-lo localmente. Não há novos dados pessoais.
Migration aditiva `zzzzg20261019a1`, filha de `zzzzf20261019a1`.

## 3. Arquitetura e integrações

`ProdutosNovo` mantém os componentes/hook canônicos. `IfoodProdutoSection`
pertence ao domínio de produto; `IfoodCentral` usa cliente `api/ifood.js`.
Backend concentra preço, contribuição e pendências em `pricing.py`/`management.py`.
Novos endpoints autenticados: `GET /integracoes/ifood/catalogo/gestao`,
`POST /integracoes/ifood/catalogo/produto/preview` e
`PUT /integracoes/ifood/catalogo/configuracao`. Este último aceita somente
campos comerciais, com atualização parcial e preservação da conexão.
Preview não grava nem chama rede externa.
Busca e paginação não descartam silenciosamente pendências fora da página.
Reservas/custos/capacidade de kits são consultados em lote.

## 4. Segurança e privacidade

Catálogo exige `produtos.visualizar`; preview exige criar ou editar produtos;
alteração usa a permissão já existente do produto. Configuração comercial exige
`configuracoes.editar` no tenant e informa a capacidade efetiva à interface;
não aceita `merchant_id`, `active` ou outros campos de conexão. A superfície
legada de conexão/envio conserva seu controle administrativo.
Consultas restringem tenant; ID de outra empresa não é aceito no preview.
Sem novas credenciais, sem exposição de tokens e sem logs de segredos.

## 5. Desenvolvimento e qualidade

Fatias: persistência e cálculo comum; seção no cadastro; central e navegação;
testes unitários/contrato; migration e jornadas locais no navegador.
Testes cobrem preço específico/regra, promoções, contribuição, null/zero,
reservas/kits, permissões, tenant e configuração parcial. Regressões existentes
de margem, clonagem e cadastro foram executadas. Resultados e comandos estão no
[registro de homologação](../homologacoes/2026-10-19-cadastro-central-ifood.md).

## 6. Ambientes e homologação

Validação exclusivamente local no projeto `corepet-homolog`, acessível em
`http://127.0.0.1:18080`, com tenant e massa fictícios. Usado o fluxo oficial
`scripts/homologacao_local.ps1`, preservando volumes e credenciais existentes.
Flags de escrita, operação e polling iFood permanecem falsas; pagamentos,
SEFAZ e outras integrações reais desabilitados. Aceite visual de negócio fica
com Lucas após a validação técnica.

## 7. Publicação e rollback

Entrega backend/frontend com migration aditiva, sem mobile. Produção não está
autorizada. Para uma futura publicação autorizada: aplicar migration, reconstruir
backend/frontend pelo fluxo oficial, conferir saúde e smoke local do canal.
Em falha, reverter código/imagens; colunas aditivas podem permanecer sem uso,
preservando dados. Downgrade só após avaliar perda dos novos campos.

## 8. Observabilidade e sustentação

Falhas de consulta/salvamento aparecem na interface com opção de tentar novamente.
Estados locais não simulam publicação, fila ou confirmação remota. Indicadores
mostram selecionados, pendências e indisponibilidade. Sem geração de repasse
financeiro ou promessa de lucro líquido; custos por pedido/mensalidade precisam
de apuração própria. Usar as vendas existentes enquanto o canal não for ativado.

## 9. Comunicação e treinamento

Orientar o piloto a configurar taxas contratuais, selecionar no cadastro e
resolver impedimentos na central. A escolha de cenário de entrega simula custo;
não contrata logística nem altera a modalidade de um pedido.
Guia oficial atualizado em `docs/INTEGRACAO_IFOOD_FASE1.md`.

## 10. Fechamento

Critérios técnicos validados: persistência no cadastro canônico, preço específico
e zero explícito, contribuição por modalidade, pendências, permissões, tenant,
migration e saúde local. Testes, build, lint e jornada no navegador aprovados.
Branch revisável sem artefatos de build ou segredos. Publicação/rollback,
documentação e comunicação avaliados nas seções anteriores.

Decisão técnica: aprovado para revisão de negócio em DEV. Lucas revisará a
experiência usando o exemplo fictício disponível; produção e envio real ao
iFood continuam fora deste aceite.
