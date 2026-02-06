# 🔧 Correção: Google Maps API - REQUEST_DENIED

## 🚨 Problema Identificado
```
Erro Google Directions: REQUEST_DENIED - API keys with referer restrictions cannot be used with this API.
```

A chave API atual (`AIzaSyClc2jpIcrb2PrCaOBkzQc4XCmEVFlWiO0`) tem **restrições de referer**, mas a **Directions API** não suporta esse tipo de restrição quando chamada do backend.

## ✅ Solução: Remover Restrições de Referer

### Passo 1: Acessar Google Cloud Console
1. Acesse: https://console.cloud.google.com/google/maps-apis/credentials
2. Faça login com sua conta Google
3. Selecione o projeto correto

### Passo 2: Editar a Chave API
1. Na lista de credenciais, encontre sua chave: `AIzaSyClc2jpIcrb2PrCaOBkzQc4XCmEVFlWiO0`
2. Clique no ícone ✏️ de edição
3. Em **"Restrições de aplicativo"**, você verá uma dessas opções:
   - ⚠️ **"Referenciadores HTTP (sites)"** ← Este é o problema!
   
4. Mude para uma destas opções:

   **Opção A: Sem Restrições (Mais Simples)**
   ```
   Restrições de aplicativo: Nenhuma
   ```
   ⚠️ **Atenção**: Menos seguro, mas funciona para testes
   
   **Opção B: Restrições por IP (Mais Seguro)** ✅ RECOMENDADO
   ```
   Restrições de aplicativo: Endereços IP
   IPs permitidos:
   - Seu IP público (para desenvolvimento)
   - IP do servidor de produção
   ```

### Passo 3: Verificar APIs Habilitadas
Certifique-se de que estas APIs estão ATIVAS no projeto:
- ✅ **Directions API** (necessária para otimização de rotas)
- ✅ **Distance Matrix API** (necessária para cálculo de distâncias)
- ✅ **Maps JavaScript API** (necessária para o mapa no frontend)
- ✅ **Geocoding API** (opcional, mas útil)

Acesse: https://console.cloud.google.com/google/maps-apis/api-list

### Passo 4: Salvar e Aguardar
1. Clique em **"Salvar"**
2. ⏱️ **Aguarde 1-2 minutos** para as alterações se propagarem
3. Teste novamente a otimização de rotas

## 🔒 Opção Avançada: Duas Chaves Separadas (Máxima Segurança)

Para produção, é recomendado usar duas chaves separadas:

### Chave 1: Frontend (com restrições de referer)
```env
# frontend/.env
VITE_GOOGLE_MAPS_API_KEY=sua_chave_frontend
```
**Restrições:**
- Tipo: Referenciadores HTTP
- Sites permitidos: 
  - `http://localhost:5173/*`
  - `https://seudominio.com/*`
**APIs necessárias:**
- Maps JavaScript API

### Chave 2: Backend (com restrições de IP)
```env
# backend/.env
GOOGLE_MAPS_API_KEY=sua_chave_backend
```
**Restrições:**
- Tipo: Endereços IP
- IPs permitidos: IP do seu servidor
**APIs necessárias:**
- Directions API
- Distance Matrix API
- Geocoding API

## 🧪 Como Testar Após Correção

### 1. Aguardar Propagação
```powershell
# Aguarde 1-2 minutos após salvar no Google Cloud Console
Start-Sleep -Seconds 120
```

### 2. Reiniciar Backend
```powershell
# Parar containers
docker stop petshop-dev-backend

# Reiniciar
cd "C:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet"
docker-compose -f docker-compose.development.yml up -d
```

### 3. Testar Otimização
1. Acesse o sistema: http://localhost:5173
2. Vá em **Entregas > Entregas Abertas**
3. Clique em **"Otimizar Rotas"**
4. Deve funcionar sem erro! ✅

## 📊 Monitoramento de Uso da API

Monitore o consumo em: https://console.cloud.google.com/google/maps-apis/quotas

**Limites gratuitos mensais:**
- Directions API: 2.500 requisições
- Distance Matrix API: 2.500 elementos
- Maps JavaScript API: Ilimitado (com marcas d'água)

**Dica:** Cache as rotas otimizadas no banco (já implementado no sistema) para economizar chamadas!

## ❓ FAQ

### Q: Por que esse erro acontece?
**A:** As APIs do Google Maps têm diferentes tipos de restrição. A Directions API só funciona com restrições de IP ou sem restrições, não com restrições de referer (HTTP).

### Q: É seguro remover as restrições?
**A:** Para desenvolvimento local, é aceitável. Para produção, use restrições por IP do servidor.

### Q: A chave vai funcionar no frontend também?
**A:** Sim! Se usar "Sem restrições" ou "IP addresses", a chave funcionará tanto no backend quanto no frontend. Mas para segurança máxima em produção, use duas chaves separadas.

### Q: Quanto custa se ultrapassar o limite gratuito?
**A:** Após 2.500 requisições mensais, é cobrado:
- Directions API: $5 por 1.000 requisições adicionais
- Distance Matrix API: $5 por 1.000 elementos adicionais

Com o cache implementado, você dificilmente ultrapassará o limite gratuito!

## 🎯 Resultado Esperado

Após seguir estes passos, o botão "Otimizar Rotas" funcionará perfeitamente:

```
✅ Rotas otimizadas com sucesso! Ordem salva no banco.
📦 Total otimizado: 3 vendas
📋 Ordem final: [V-0023, V-0025, V-0024]
```

---

**Status:** ⏳ Aguardando correção das restrições no Google Cloud Console
