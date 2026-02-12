# 📄 Qual Arquivo Importar na Conciliação?

## ✅ ARQUIVO CORRETO

O arquivo que você deve importar é o **EXTRATO DE RECEBIMENTOS/LIQUIDAÇÕES** que a **operadora de cartões** (Stone, Cielo, Rede, etc) envia para você.

### Como obter o arquivo:

1. **Stone**: 
   - Acesse o portal Stone > Extratos > Exportar CSV
   - Ou verifique seu email (Stone envia automaticamente)

2. **Cielo**: 
   - Acesse Cielo Gestão > Relatórios > Vendas > Exportar CSV

3. **Rede**: 
   - Acesse portal Rede > Relatórios > Extrato de Recebimentos > Gerar CSV

### O arquivo contém:

- **NSU**: Código único da transação na operadora
- **Data da Venda**: Quando o cliente pagou
- **Data do Pagamento**: Quando você recebeu (ou vai receber)
- **Valor Bruto**: Valor total da venda
- **Taxa MDR**: Taxa cobrada pela operadora (%)
- **Valor Líquido**: Valor que você recebeu (bruto - taxa)
- **Parcela**: Se foi parcelado (1/3, 2/3, etc)
- **Tipo**: Débito, Crédito à Vista, Crédito Parcelado
- **Bandeira**: Visa, Mastercard, Elo, Amex, etc

---

## ❌ ARQUIVO ERRADO (não use)

**NÃO importe:**

- ❌ Vendas do seu PDV/sistema interno
- ❌ Relatório de recibos manuais
- ❌ Planilha que você criou
- ❌ Contas a receber do sistema

---

## 📋 Exemplo de Arquivo Correto (Stone)

Veja o arquivo: `docs/EXEMPLO_ARQUIVO_STONE.csv`

```csv
NSU;Data Transação;Data Pagamento;Valor Bruto;Taxa MDR %;Valor Taxa;Valor Líquido;Parcela;Tipo;Bandeira
123456;15/03/2025;16/03/2025;R$ 1.500,00;2,5%;R$ 37,50;R$ 1.462,50;1/1;Débito;Visa
123457;15/03/2025;16/03/2025;R$ 800,00;3,0%;R$ 24,00;R$ 776,00;1/1;Débito;Mastercard
```

---

## 🔍 Fluxo de Conciliação

1. **Você registra vendas no PDV** → Sistema cria "Contas a Receber"
2. **Operadora processa pagamentos** → Gera arquivo CSV com NSUs
3. **Você importa o CSV da operadora** → Sistema compara NSUs
4. **Sistema valida automaticamente** → Encontra divergências (se houver)
5. **Você revisa e processa** → Parcelas são conciliadas

---

## ⚙️ Operadoras Suportadas

Atualmente o sistema suporta:

- ✅ **Stone** (separador: ponto e vírgula)
- ✅ **Cielo** (separador: vírgula)
- ✅ **Rede** (separador: ponto e vírgula)
- 🔄 GetNet (em breve)
- 🔄 SafraPay (em breve)

Se sua operadora não está na lista, entre em contato para adicionarmos o template.

---

## 🆘 Dúvidas Comuns

### "Não sei onde pegar o arquivo"
- Acesse o portal da operadora (Stone, Cielo, etc)
- Procure por "Extratos" ou "Relatórios"
- Exporte como CSV ou TXT

### "O arquivo está dando erro"
- Verifique se selecionou a operadora correta no dropdown
- Confirme que é o arquivo de RECEBIMENTOS (não vendas)
- Verifique o formato (CSV ou TXT, não Excel/PDF)

### "Posso editar o arquivo antes de importar?"
- ❌ NÃO edite o arquivo manualmente
- O sistema precisa do formato original da operadora
- Se tiver dúvidas, importe o original primeiro

### "Preciso importar todo mês?"
- ✅ Sim, importe o extrato mensal de cada operadora
- O sistema evita duplicação automaticamente
- Você pode reimportar o mesmo período sem problemas (não vai duplicar)

---

## 📞 Suporte

Problemas ao importar? 
- Verifique os logs do sistema
- Consulte o administrador
- Envie o arquivo CSV para análise (sem dados sensíveis)
