# 🚀 Guia Rápido - Upload CSV para Conciliação de Cartão

## 📋 Pré-requisitos

1. Token JWT de autenticação
2. Arquivo CSV com o formato correto
3. Contas a receber cadastradas com NSU

---

## 📄 Formato do CSV

### Estrutura Obrigatória

```csv
nsu,valor,data_recebimento,adquirente
123456789,150.00,2026-01-31,Stone
987654321,89.90,2026-02-01,Cielo
555111222,250.50,2026-01-30,Rede
```

### Regras

- ✅ Primeira linha DEVE ser o cabeçalho
- ✅ Colunas obrigatórias: `nsu`, `valor`, `data_recebimento`, `adquirente`
- ✅ Codificação: UTF-8
- ✅ Separador: vírgula (`,`)
- ✅ Data no formato ISO: `YYYY-MM-DD`
- ✅ Valor com ponto decimal: `150.00` (não `150,00`)

---

## 🔧 Como Usar

### Via Postman / Insomnia

1. **Método:** `POST`
2. **URL:** `http://localhost:8000/financeiro/conciliacao-cartao/upload`
3. **Headers:**
   ```
   Authorization: Bearer SEU_TOKEN_JWT
   ```
4. **Body:** `form-data`
   - **Key:** `file` (type: File)
   - **Value:** Selecione o arquivo CSV

### Via cURL

```bash
curl -X POST "http://localhost:8000/financeiro/conciliacao-cartao/upload" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -F "file=@exemplo_conciliacao.csv"
```

### Via Python (requests)

```python
import requests

url = "http://localhost:8000/financeiro/conciliacao-cartao/upload"
headers = {"Authorization": "Bearer SEU_TOKEN_JWT"}
files = {"file": open("exemplo_conciliacao.csv", "rb")}

response = requests.post(url, headers=headers, files=files)
print(response.json())
```

---

## 📊 Resposta Esperada

### Sucesso Total

```json
{
  "message": "Processamento concluído: 3/3 conciliados",
  "processados": 3,
  "conciliados": 3,
  "erros": [],
  "taxa_sucesso": 100.0
}
```

### Sucesso Parcial

```json
{
  "message": "Processamento concluído: 2/3 conciliados",
  "processados": 3,
  "conciliados": 2,
  "erros": [
    {
      "linha": 3,
      "nsu": "987654321",
      "erro": "Conta já conciliada anteriormente em 2026-01-30"
    }
  ],
  "taxa_sucesso": 66.67
}
```

---

## ❌ Erros Comuns

### Arquivo não é CSV

```json
{
  "detail": "Arquivo deve ser CSV"
}
```
**Solução:** Verifique a extensão do arquivo (deve ser `.csv`)

---

### Colunas incorretas

```json
{
  "detail": "CSV deve ter as colunas: adquirente, data_recebimento, nsu, valor"
}
```
**Solução:** Verifique o cabeçalho do CSV

---

### Conta não encontrada

```json
{
  "message": "Processamento concluído: 0/1 conciliados",
  "erros": [
    {
      "linha": 2,
      "nsu": "999999999",
      "erro": "Conta a receber não encontrada para o NSU 999999999"
    }
  ]
}
```
**Solução:** Verifique se o NSU está cadastrado em uma conta a receber

---

### Valor não confere

```json
{
  "erros": [
    {
      "linha": 2,
      "nsu": "123456789",
      "erro": "Valor informado (R$ 150.00) não confere com a parcela (R$ 151.50)"
    }
  ]
}
```
**Solução:** Verifique se o valor no CSV corresponde ao valor da conta

---

### Conta já conciliada

```json
{
  "erros": [
    {
      "linha": 2,
      "nsu": "123456789",
      "erro": "Conta já conciliada anteriormente em 2026-01-30"
    }
  ]
}
```
**Solução:** Esta conta já foi conciliada, não precisa fazer novamente

---

## 🔍 Dicas de Uso

### 1. Validar CSV antes do upload

```python
import csv

with open('conciliacao.csv', 'r') as f:
    reader = csv.DictReader(f)
    
    # Validar cabeçalho
    expected = {'nsu', 'valor', 'data_recebimento', 'adquirente'}
    if not expected.issubset(set(reader.fieldnames)):
        print("❌ Colunas incorretas!")
    else:
        print("✅ Cabeçalho OK")
    
    # Validar linhas
    for idx, row in enumerate(reader, start=2):
        print(f"Linha {idx}: NSU {row['nsu']} - R$ {row['valor']}")
```

### 2. Processar em lotes

Se você tem um arquivo muito grande (>1000 linhas), considere dividir em arquivos menores para melhor controle.

### 3. Monitorar taxa de sucesso

Uma taxa de sucesso < 90% pode indicar problemas nos dados. Revise os erros retornados.

---

## 🎯 Fluxo Recomendado

1. **Exportar** relatório da adquirente (Stone, Cielo, etc)
2. **Converter** para o formato CSV padrão
3. **Validar** estrutura do arquivo
4. **Fazer upload** via API
5. **Analisar** resposta e tratar erros
6. **Corrigir** dados e reprocessar linhas com erro (se necessário)

---

## 🔐 Segurança

- ✅ Requer autenticação JWT válida
- ✅ Respeita isolamento multi-tenant
- ✅ Validação de formato de arquivo
- ✅ Validação de integridade dos dados
- ✅ Auditoria completa de operações
