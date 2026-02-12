# ✅ CHECKLIST DE TESTES PRÉ-PRODUÇÃO
# Sistema Pet Shop Pro v1.0

**Data de Execução**: ___/___/______  
**Responsável**: _______________________  
**Ambiente**: [ ] Desenvolvimento  [ ] Staging  [ ] Produção

---

## 📋 CADASTROS BÁSICOS

### Clientes
- [ ] Criar cliente pessoa física
- [ ] Criar cliente pessoa jurídica  
- [ ] Editar dados de cliente
- [ ] Buscar cliente por nome/CPF/telefone
- [ ] Inativar cliente
- [ ] Histórico de compras do cliente

**Observações**: _______________________________________________

### Pets
- [ ] Criar pet associado a cliente
- [ ] Editar dados do pet
- [ ] Listar pets por cliente
- [ ] Buscar pet por nome
- [ ] Histórico de compras do pet

**Observações**: _______________________________________________

### Produtos
- [ ] Criar produto simples
- [ ] Criar produto com variações (tamanho, cor, sabor)
- [ ] Editar preço de venda
- [ ] Editar preço de custo
- [ ] Controle de estoque mínimo
- [ ] Produto kit (composição)
- [ ] Inativar produto

**Observações**: _______________________________________________

---

## 💰 VENDAS - PAGAMENTO À VISTA

### Dinheiro
- [ ] Venda simples em dinheiro
- [ ] Contas a receber criada e liquidada? **SIM [ ] NÃO [ ]**
- [ ] Fluxo de caixa registrado? **SIM [ ] NÃO [ ]**
- [ ] DRE atualizada (receita bruta)? **SIM [ ] NÃO [ ]**
- [ ] Estoque baixado corretamente? **SIM [ ] NÃO [ ]**

**Valores testados**: _________________
**Observações**: _______________________________________________

### PIX
- [ ] Venda simples via PIX
- [ ] Sem taxas aplicadas? **SIM [ ] NÃO [ ]**
- [ ] Liquidação imediata? **SIM [ ] NÃO [ ]**
- [ ] Fluxo de caixa correto? **SIM [ ] NÃO [ ]**

**Valores testados**: _________________
**Observações**: _______________________________________________

### Cartão de Débito
- [ ] Venda no débito
- [ ] Taxa de débito configurada? **Percentual**: ____%
- [ ] Taxa descontada corretamente? **SIM [ ] NÃO [ ]**
- [ ] Valor líquido no fluxo de caixa? **SIM [ ] NÃO [ ]**
- [ ] Taxa registrada como despesa na DRE? **SIM [ ] NÃO [ ]**

**Valores testados**: _________________  
**Taxa esperada**: _____ **Taxa calculada**: _____  
**Observações**: _______________________________________________

---

## 💳 VENDAS - CARTÃO PARCELADO

### Crédito 2x
- [ ] Venda parcelada em 2x
- [ ] 2 contas a receber criadas? **SIM [ ] NÃO [ ]**
- [ ] Valores iguais nas parcelas? **SIM [ ] NÃO [ ]**
- [ ] Vencimentos corretos (30 e 60 dias)? **SIM [ ] NÃO [ ]**
- [ ] Fluxo de caixa NÃO realizado? **SIM [ ] NÃO [ ]**
- [ ] DRE registrada (receita pelo regime de competência)? **SIM [ ] NÃO [ ]**

**Valores testados**: _________________

### Crédito 3x
- [ ] Venda parcelada em 3x
- [ ] 3 contas a receber criadas? **SIM [ ] NÃO [ ]**
- [ ] Taxa de crédito aplicada? **Percentual**: ____%
- [ ] Taxa registrada na DRE? **SIM [ ] NÃO [ ]**

**Valores testados**: _________________

### Crédito 6x e 12x
- [ ] Testar 6 parcelas
- [ ] Testar 12 parcelas
- [ ] Taxas diferenciadas por número de parcelas? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 🔄 OPERAÇÕES EM VENDAS

### Cancelamento de Venda
- [ ] Cancelar venda à vista (dinheiro)
- [ ] Cancelar venda parcelada (crédito)
- [ ] Cancelar venda com múltiplos itens

**Para CADA cancelamento, verificar:**
- [ ] Contas a receber canceladas? **SIM [ ] NÃO [ ]**
- [ ] Fluxo de caixa estornado? **SIM [ ] NÃO [ ]**
- [ ] DRE atualizada (cancelamento)? **SIM [ ] NÃO [ ]**
- [ ] Estoque devolvido? **SIM [ ] NÃO [ ]**
- [ ] Comissões estornadas? **SIM [ ] NÃO [ ]**
- [ ] Motivo do cancelamento registrado? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

### Reabrir Venda
- [ ] Reabrir venda finalizada
- [ ] Status volta para "aberta"? **SIM [ ] NÃO [ ]**
- [ ] Permite adicionar itens? **SIM [ ] NÃO [ ]**
- [ ] Permite remover itens? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

### Remover Item da Venda
- [ ] Venda com 3 itens, remover 1
- [ ] Total recalculado? **SIM [ ] NÃO [ ]**
- [ ] Estoque do item removido devolvido? **SIM [ ] NÃO [ ]**
- [ ] Contas a receber ajustadas? **SIM [ ] NÃO [ ]**
- [ ] DRE atualizada? **SIM [ ] NÃO [ ]**

**Valores**: Antes _____ Depois _____  
**Observações**: _______________________________________________

### Adicionar Item em Venda Aberta
- [ ] Adicionar item extra
- [ ] Total recalculado? **SIM [ ] NÃO [ ]**
- [ ] Estoque baixado? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 🎁 DESCONTOS

### Desconto Percentual
- [ ] Aplicar 5% de desconto
- [ ] Aplicar 10% de desconto
- [ ] Aplicar 20% de desconto
- [ ] Total recalculado corretamente? **SIM [ ] NÃO [ ]**
- [ ] Desconto registrado na DRE? **SIM [ ] NÃO [ ]**

**Teste**: Subtotal R$ 100, Desconto 10%  
**Esperado**: R$ 90,00 **Obtido**: R$ _____

### Desconto em Valor Fixo
- [ ] Aplicar R$ 10 de desconto
- [ ] Aplicar R$ 50 de desconto
- [ ] Total recalculado corretamente? **SIM [ ] NÃO [ ]**

**Teste**: Subtotal R$ 100, Desconto R$ 15  
**Esperado**: R$ 85,00 **Obtido**: R$ _____

**Observações**: _______________________________________________

---

## 🚚 ENTREGAS

### Venda com Entrega
- [ ] Venda com taxa de entrega fixa
- [ ] Taxa de entrega adicionada ao total? **SIM [ ] NÃO [ ]**
- [ ] Endereço de entrega registrado? **SIM [ ] NÃO [ ]**
- [ ] Status de entrega (pendente, em rota, entregue)? **SIM [ ] NÃO [ ]**
- [ ] Entregador associado? **SIM [ ] NÃO [ ]**

### Cálculo de Entrega por KM
- [ ] Distância calculada? **SIM [ ] NÃO [ ]**
- [ ] Valor por KM configurável? **SIM [ ] NÃO [ ]**
- [ ] Cálculo correto? **SIM [ ] NÃO [ ]**

**Teste**: 5 km × R$ 2,00/km  
**Esperado**: R$ 10,00 **Obtido**: R$ _____

**Observações**: _______________________________________________

---

## 💼 COMISSÕES

### Comissão por Venda
- [ ] Comissão calculada automaticamente? **SIM [ ] NÃO [ ]**
- [ ] Percentual correto? **Configurado**: ____%
- [ ] Valor da comissão correto? **SIM [ ] NÃO [ ]**
- [ ] Funcionário comissionado vinculado? **SIM [ ] NÃO [ ]**

**Teste**: Venda R$ 1000, Comissão 5%  
**Esperado**: R$ 50,00 **Obtido**: R$ _____

### Estorno de Comissão
- [ ] Ao cancelar venda, comissão é estornada? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 💵 MÚLTIPLAS FORMAS DE PAGAMENTO

### Pagamento Misto
- [ ] Testar: 50% dinheiro + 50% PIX
- [ ] Testar: 30% dinheiro + 30% débito + 40% crédito 2x
- [ ] Cada pagamento registrado separadamente? **SIM [ ] NÃO [ ]**
- [ ] Taxas aplicadas individualmente? **SIM [ ] NÃO [ ]**
- [ ] Total soma 100% da venda? **SIM [ ] NÃO [ ]**

**Teste realizado**: _______________________________________________  
**Observações**: _______________________________________________

---

## 📊 VALIDAÇÕES FINANCEIRAS

### Contas a Receber
- [ ] Listagem de contas abertas
- [ ] Filtro por cliente
- [ ] Filtro por período
- [ ] Baixa manual de conta
- [ ] Baixa automática (venda à vista)
- [ ] Relatório de inadimplência

**Observações**: _______________________________________________

### Fluxo de Caixa
- [ ] Lançamentos de entrada (vendas)
- [ ] Lançamentos de saída (despesas)
- [ ] Saldo por período
- [ ] Projeção de caixa
- [ ] Exportar para Excel

**Observações**: _______________________________________________

### DRE (Demonstração do Resultado do Exercício)
- [ ] Receita bruta correta
- [ ] CMV calculado
- [ ] Lucro bruto correto
- [ ] Despesas listadas
- [ ] Lucro líquido correto
- [ ] DRE por canal de venda
- [ ] DRE por período

**Teste manual**: Calcular DRE de um período conhecido  
**Observações**: _______________________________________________

---

## 📦 CONTROLE DE ESTOQUE

### Movimentações
- [ ] Entrada de produtos (nota fiscal)
- [ ] Saída automática (venda)
- [ ] Devolução (cancelamento de venda)
- [ ] Ajuste manual de estoque
- [ ] Transferência entre locais
- [ ] Histórico de movimentações

**Observações**: _______________________________________________

### Alertas
- [ ] Alerta de estoque mínimo funciona? **SIM [ ] NÃO [ ]**
- [ ] Produtos sem estoque não podem ser vendidos? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 🏪 CAIXA (PDV)

### Abertura e Fechamento
- [ ] Abrir caixa com saldo inicial
- [ ] Fechar caixa
- [ ] Sangria de caixa
- [ ] Reforço de caixa
- [ ] Relatório de fechamento correto? **SIM [ ] NÃO [ ]**

**Teste**: Abrir com R$ 100, vender R$ 500, fazer sangria de R$ 200  
**Saldo esperado ao fechar**: R$ 400  
**Saldo obtido**: R$ _____

**Observações**: _______________________________________________

---

## 🧾 NOTAS FISCAIS

### NFC-e (Cupom Fiscal Eletrônico)
- [ ] Emitir NFC-e
- [ ] XML gerado corretamente? **SIM [ ] NÃO [ ]**
- [ ] Chave de acesso válida? **SIM [ ] NÃO [ ]**
- [ ] Cancelamento de NFC-e? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

### NF-e (Nota Fiscal Eletrônica)
- [ ] Emitir NF-e
- [ ] XML correto? **SIM [ ] NÃO [ ]**
- [ ] Envio para SEFAZ? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 🔐 SEGURANÇA E PERMISSÕES

### Usuários
- [ ] Criar usuário
- [ ] Definir perfil (admin, vendedor, estoquista)
- [ ] Testar permissões de acesso
- [ ] Usuário sem permissão é bloqueado? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

### Multi-Tenancy
- [ ] Dados isolados por tenant? **SIM [ ] NÃO [ ]**
- [ ] Tenant A não acessa dados do Tenant B? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 📈 RELATÓRIOS

- [ ] Relatório de vendas por período
- [ ] Relatório de produtos mais vendidos
- [ ] Relatório de comissões
- [ ] Relatório de clientes (ranking)
- [ ] Relatório de inadimplência
- [ ] Exportação para Excel/PDF

**Observações**: _______________________________________________

---

## 🤖 INTEGRAÇÕES

### Bling (ERP)
- [ ] Sincronizar produtos
- [ ] Sincronizar estoque
- [ ] Sincronizar pedidos
- [ ] Webhook ativo? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

### Stone (Pagamentos)
- [ ] Conciliação automática de cartão
- [ ] Importação de transações
- [ ] Taxas calculadas corretamente? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

### WhatsApp Business
- [ ] Envio de mensagens
- [ ] Recebimento de mensagens
- [ ] IA responde automaticamente? **SIM [ ] NÃO [ ]**

**Observações**: _______________________________________________

---

## 🎯 CENÁRIOS CRÍTICOS (EDGE CASES)

- [ ] Venda de R$ 0,01
- [ ] Venda de R$ 999.999,99
- [ ] Produto com estoque ZERO
- [ ] Cliente sem CPF
- [ ] Desconto de 100%
- [ ] Cancelar venda 2x (deve dar erro na 2ª vez)
- [ ] Venda com 50 itens
- [ ] Pagamento com valor a MAIOR (troco)

**Observações**: _______________________________________________

---

## ✅ RESULTADO FINAL

**Total de itens testados**: _____  
**Itens APROVADOS**: _____  
**Itens REPROVADOS**: _____  

**Taxa de Sucesso**: _____%

### Principais Problemas Encontrados:
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Pronto para Produção?
[ ] **SIM** - Todos os testes passaram  
[ ] **NÃO** - Corrigir problemas listados acima  

**Assinatura**: _______________________ **Data**: ___/___/______

---

## 📝 NOTAS ADICIONAIS

_______________________________________________
_______________________________________________
_______________________________________________
_______________________________________________
_______________________________________________
