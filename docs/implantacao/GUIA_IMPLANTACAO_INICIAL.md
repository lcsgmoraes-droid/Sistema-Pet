# Guia de Implantacao Inicial - Sistema Pet

Uso: checklist interno para Lucas/suporte configurar ou revisar uma conta nova.

Atencao: este guia cobre modulos amplos do sistema. Para cliente do Plano Basico
piloto, use `docs/implantacao/CHECKLIST_PLANO_BASICO_PILOTO.md`; itens de
financeiro completo, Stone, WhatsApp e demais adicionais nao entram na promessa
do Basico.

## Sequencia logica de configuracao

Esta ordem evita que o usuario tente vender, receber ou analisar resultado sem
cadastros essenciais.

1. Empresa, usuario admin, plano e modulos liberados.
2. Bancos/caixas/carteiras.
3. Formas de pagamento, taxas de cartao, prazos e conta de destino.
4. Categorias financeiras, DRE e tipos de despesa.
5. Impostos/configuracao fiscal usada no calculo de rentabilidade.
6. Clientes, fornecedores, funcionarios e entregadores.
7. Produtos, servicos, categorias, marcas, custos e estoque inicial.
8. Regras de entrega: entregador, custo por km/taxa, repasse e rota.
9. Regras de comissao: vendedor/parceiro, percentual e base de calculo.
10. Campanhas/cupons quando forem afetar venda liquida.
11. Ecommerce/app quando houver venda online.
12. Venda teste, baixa/recebimento, estoque, contas e relatorios.

Dependencias principais:

| Para funcionar bem | Precisa estar configurado antes |
|---|---|
| Recebimento de venda | Forma de pagamento, banco/caixa, categoria financeira e regra de baixa |
| Taxa de cartao | Forma de pagamento com operadora, percentual, prazo e conta de destino |
| Lucro/margem da venda | Custo do produto, imposto, taxas, desconto, campanha e comissao |
| DRE | Categorias financeiras, tipos de despesa, impostos, CMV e despesas fixas |
| Fluxo de caixa | Contas a pagar/receber, bancos, vencimentos e baixas efetivas |
| Ponto de equilibrio | Despesas fixas, folha/RH, impostos, margem media e faturamento |
| Entrega | Entregador, custo de entrega, endereco, status e regra de repasse |
| Comissao | Pessoa parceira/vendedor ativo, regra de comissao e venda vinculada |
| Ecommerce/app | Produtos com imagem, preco, estoque, entrega/retirada e pedidos |

## 1. Identificacao

- Cliente/tenant:
- Responsavel pela implantacao:
- Data de inicio:
- Plano:
- Modulos ativos:
- Pendencias bloqueantes:
- Pendencias nao bloqueantes:

## 2. Empresa e acesso

- [ ] Dados cadastrais conferidos em `/configuracoes`.
- [ ] Dados fiscais conferidos em `/configuracoes/fiscal`.
- [ ] Usuarios criados em `/admin/usuarios`.
- [ ] Permissoes revisadas em `/admin/roles`.
- [ ] Plano e modulos conferidos em `/meu-plano`.

## 3. Financeiro obrigatorio

- [ ] Bancos, caixas e carteiras conferidos em `/cadastros/financeiro/bancos`.
- [ ] Cada banco/caixa tem nome claro, saldo inicial e uso definido.
- [ ] Formas de pagamento conferidas em `/cadastros/financeiro/formas-pagamento`.
- [ ] Cada forma de pagamento define tipo: dinheiro, PIX, debito, credito, boleto, prazo ou outro.
- [ ] Formas que geram recebivel criam conta a receber/previsao de recebimento.
- [ ] Formas com baixa imediata registram recebimento efetivo no caixa/banco correto.
- [ ] Operadoras de cartao cadastradas em `/cadastros/financeiro/operadoras`, quando houver cartao.
- [ ] Taxas de cartao conferidas: percentual, taxa fixa, prazo de recebimento, bandeira e parcelas.
- [ ] Categorias financeiras revisadas em `/cadastros/categorias-financeiras`.
- [ ] DRE e tipos de despesa revisados em `/financeiro/dre` e `/cadastros/tipos-despesa`.
- [ ] Impostos cadastrados/conferidos para refletir na rentabilidade da venda.
- [ ] Despesas fixas cadastradas: aluguel, folha, energia, sistemas, marketing e impostos recorrentes.
- [ ] Contas a pagar iniciais lancadas para testar fluxo de caixa.
- [ ] Contas a receber/previsoes iniciais conferidas para testar recebimento efetivo.

## 4. Cadastros base

- [ ] Departamentos, categorias e marcas conferidos.
- [ ] Produtos cadastrados ou importados.
- [ ] Produtos de venda possuem custo, preco, margem, unidade, categoria e estoque.
- [ ] Produtos de ecommerce/app possuem imagem, canal habilitado e estoque disponivel.
- [ ] Estoque inicial e estoque minimo revisados.
- [ ] Clientes, fornecedores, funcionarios, veterinarios e entregadores cadastrados conforme operacao.
- [ ] Funcionarios de RH possuem cargo, salario/base de custo e vinculo operacional.
- [ ] Vendedores com comissao estao marcados como parceiros/funcionarios comissionados.
- [ ] Entregadores possuem regra de custo: fixo, por km, repasse ou RH rateado.
- [ ] Pets cadastrados quando a operacao usa atendimento por tutor/pet.
- [ ] Especies, racas e opcoes de racao revisadas.

## 5. Operacao de venda

- [ ] Caixa aberto no PDV.
- [ ] Venda teste feita.
- [ ] Pagamento em dinheiro ou PIX testado.
- [ ] Pagamento em cartao testado quando houver operadora.
- [ ] Venda com desconto testada.
- [ ] Venda com campanha/cupom testada quando o modulo estiver ativo.
- [ ] Venda com vendedor comissionado testada quando houver comissao.
- [ ] Venda com entrega testada quando houver delivery.
- [ ] Baixa de estoque conferida.
- [ ] Conta a receber conferida quando a forma de pagamento gera recebivel.
- [ ] Recebimento efetivo conferido no banco/caixa.
- [ ] Venda aberta conferida para aparecer em contas a receber/previsao.
- [ ] Caixa fechado e diferenca conferida.

## 6. Modulos condicionais

- [ ] Entregas configurado quando ativo.
- [ ] Custo de entrega aparece em vendas, entregas e financeiro.
- [ ] Comissoes configurado quando ativo.
- [ ] Comissoes geradas aparecem em `/comissoes/abertas`.
- [ ] Banho & Tosa configurado quando ativo.
- [ ] Veterinario configurado quando ativo.
- [ ] Ecommerce configurado quando ativo.
- [ ] Pedido ecommerce/app testado com produto, estoque, entrega/retirada e financeiro.
- [ ] Campanhas configurado quando ativo.
- [ ] WhatsApp configurado quando ativo.
- [ ] Bling configurado quando ativo.
- [ ] App mobile habilitado quando ativo.

## 7. Validacao final

- [ ] Fluxo de caixa conferido.
- [ ] DRE conferido.
- [ ] Ponto de equilibrio conferido com despesas fixas e margem coerentes.
- [ ] Relatorio de vendas conferido.
- [ ] Relatorio de vendas mostra venda bruta, liquida, CMV, imposto, taxas, comissao e lucro.
- [ ] Estoque conferido depois da venda teste.
- [ ] Rotas/entregas conferidas depois da venda com entrega.
- [ ] Comissoes conferidas depois da venda com vendedor.
- [ ] Usuario operacional testado sem acesso admin.
- [ ] Evidencias registradas: prints, video curto ou anotacao.

## 8. Observacoes comerciais

- Dor principal do cliente:
- Funcionalidades que mais geraram interesse:
- Modulos com potencial de venda:
- Criativos sugeridos para este perfil:
