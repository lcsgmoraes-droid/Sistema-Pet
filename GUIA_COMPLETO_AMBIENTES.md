# 📚 GUIA COMPLETO DOS AMBIENTES - Sistema Pet Shop Pro

**Última atualização:** 12/02/2026  
**Status:** ✅ ORGANIZADO E FUNCIONANDO

---

## 🎯 VISÃO GERAL

Este sistema possui **3 ambientes independentes:**

```
┌─────────────────────────────────────────────────────────────┐
│  🔵 LOCAL-DEV (Testes)                                      │
│  ├─ Porta Backend: 8000                                     │
│  ├─ Porta Postgres: 5433                                    │
│  ├─ Dados: FICTÍCIOS                                        │
│  └─ Usar: INICIAR_DEV.bat                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🟢 LOCAL-PILOTO (Loja Real)                                │
│  ├─ Porta Backend: 8001                                     │
│  ├─ Porta Postgres: 5434                                    │
│  ├─ Dados: REAIS                                            │
│  └─ Usar: INICIAR_PILOTO.bat                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ☁️  CLOUD (Servidor Ocean)                                  │
│  ├─ Porta Backend: 8000                                     │
│  ├─ Porta Postgres: 5432                                    │
│  ├─ Domínio: mlprohub.com.br                                │
│  └─ Usar: docker-compose.cloud.yml                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 SCRIPTS DISPONÍVEIS

### 📂 Scripts na Raiz do Projeto:

| Script | Função | Quando Usar |
|--------|---------|-------------|
| `INICIAR_DEV.bat` | Sobe LOCAL-DEV (testes) | Desenvolvimento/Testes |
| `INICIAR_PILOTO.bat` | Sobe LOCAL-PILOTO (loja) | Vendas reais na loja |
| `INICIAR_TUDO.bat` | Sobe DEV + PILOTO juntos | Rodar os 2 simultaneamente |
| `PARAR_TUDO.bat` | Para todos os ambientes | Limpar containers |

---

## 🔵 AMBIENTE LOCAL-DEV (TESTES)

### Para que serve:
- Desenvolvimento de funcionalidades
- Testes locais
- Experimentos
- Quebrar à vontade!

### Como usar:
```batch
# Subir
INICIAR_DEV.bat

# Parar
docker-compose -f docker-compose.local-dev.yml down
```

### Acessos:
- **Backend:** http://localhost:8000
- **Docs API:** http://localhost:8000/docs
- **Frontend:** http://localhost:5173
- **Banco:** localhost:5433

### Credenciais Banco:
- User: `postgres`
- Password: `postgres`
- Database: `petshop_dev`

### ⚠️ IMPORTANTE:
- ❌ NÃO usar para vendas reais
- ❌ NÃO cadastrar clientes reais
- ✅ Pode quebrar, testar, experimentar

---

## 🟢 AMBIENTE LOCAL-PILOTO (LOJA REAL)

### Para que serve:
- Rodar o piloto na loja
- Vendas reaisClientes reais
- Dados para serem preservados

### Como usar:
```batch
# Subir
INICIAR_PILOTO.bat

# Parar
docker-compose -f docker-compose.local-piloto.yml down
```

### Acessos:
- **Backend:** http://localhost:8001
- **Docs API:** http://localhost:8001/docs
- **Frontend:** http://localhost:5173 (apontar para porta 8001)
- **Banco:** localhost:5434

### Credenciais Banco:
- User: `petshop_user`
- Password: `petshop_pass_2026`
- Database: `petshop_prod`

### Login Inicial:
- **Email:** admin@petshop.com
- **Senha:** admin123
- 🔴 **ALTERE A SENHA** após primeiro login!

### ⚠️ IMPORTANTE:
- ✅ Dados REAIS aqui
- ✅ Fazer backup regularmente
- ❌ NÃO testar funcionalidades aqui
- ❌ NÃO apagar dados sem backup

---

##  ☁️ AMBIENTE CLOUD (Ocean / mlprohub.com.br)

### Para que serve:
- Rodar online no servidor
- Acesso via internet
- Sistema 24/7

### Como preparar:
1. Subir para Ocean usando `docker-compose.cloud.yml`
2. Configurar variáveis de ambiente (`.env`)
3. Configurar domínio mlprohub.com.br
4. Setup SSL/HTTPS

### Acessos:
- **Frontend:** https://mlprohub.com.br
- **Backend:** https://api.mlprohub.com.br
- **Porta Backend:** 8000
- **Porta Postgres:** 5432 (interno)

### ⚠️ ATENÇÃO:
- Requer configuração adicional
- SSL/HTTPS obrigatório
- Firewall configurado
- Backups automáticos

---

## 🔄 RODANDO OS 2 AMBIENTES LOCAIS JUNTOS

Você pode rodar **DEV + PILOTO simultaneamente** (portas diferentes):

```batch
# Subir os 2
INICIAR_TUDO.bat

# Ver status
docker ps

# Parar os 2
PARAR_TUDO.bat
```

**Resultado:**
- DEV na porta 8000 (testes)
- PILOTO na porta 8001 (vendas reais)
- Ambos rodando ao mesmo tempo!

---

## 📊 COMPARAÇÃO RÁPIDA

| Característica | LOCAL-DEV 🔵 | LOCAL-PILOTO 🟢 | CLOUD ☁️ |
|---|---|---|---|
| **Porta Backend** | 8000 | 8001 | 8000 |
| **Porta Postgres** | 5433 | 5434 | 5432 |
| **Dados** | Fictícios | Reais | Reais |
| **Acessível via internet** | ❌ (só local) | ❌ (só local) | ✅ (online) |
| **Quando usar** | Testes | Piloto loja | Produção final |
| **Pode perder dados?** | ✅ (é teste) | ❌ (fazer backup) | ❌ (fazer backup) |
| **Precisa SSL** | ❌ | ❌ | ✅ |

---

## 📁 ARQUIVOS DOCKER-COMPOSE

| Arquivo | Ambiente | Usado por |
|---------|----------|-----------|
| `docker-compose.local-dev.yml` | LOCAL-DEV | INICIAR_DEV.bat |
| `docker-compose.local-piloto.yml` | LOCAL-PILOTO | INICIAR_PILOTO.bat |
| `docker-compose.cloud.yml` | CLOUD | Deploy Ocean |

---

## 🔐 SEGURANÇA

### LOCAL-DEV (Testes):
- Senhas simples OK
- JWT key de desenvolvimento
- Debug ativado
- Logs detalhados

### LOCAL-PILOTO (Loja):
- 🔴 Alterar senha admin
- 🔴 Gerar JWT_SECRET_KEY próprio
- Fazer backups regulares
- Debug ativado (troubleshooting)

### CLOUD (Produção):
- 🔴 HTTPS/SSL obrigatório
- 🔴 JWT_SECRET_KEY forte e único
- 🔴 Senhas fortes
- Debug desativado
- Logs em arquivo
- Backups automáticos
- Firewall configurado

---

## 💾 BACKUPS

### Backup Manual:

```batch
# DEV (se precisar)
docker exec petshop-dev-postgres pg_dump -U postgres petshop_dev > backup_dev.sql

# PILOTO (IMPORTANTE!)
docker exec petshop-prod-postgres pg_dump -U petshop_user petshop_prod > backup_piloto_%date:~0,10%.sql
```

### Backup Automático (TODO):
- Criar script de backup diário
- Sincronizar PILOTO → CLOUD
- Sincronizar CLOUD → Backup externo

---

## 🆘 SOLUÇÃO DE PROBLEMAS

### Backend não conecta no banco:
```batch
# Verificar se containers estão rodando
docker ps

# Ver logs do banco
docker logs petshop-dev-postgres
docker logs petshop-prod-postgres

# Reiniciar
docker restart petshop-dev-postgres
docker restart petshop-dev-backend
```

### Porta já em uso:
```batch
# Ver o que está usando a porta
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :5433
netstat -ano | findstr :5434

# Parar container conflitante
docker ps
docker stop <container_name>
```

### Resetar ambiente completo:
```batch
# DEV
docker-compose -f docker-compose.local-dev.yml down -v

# PILOTO (⚠️ CUIDADO: Perde dados!)
docker-compose -f docker-compose.local-piloto.yml down -v
```

---

## 🎯 PRÓXIMOS PASSOS

### ✅ Já Feito:
- [x] Ambientes organizados (DEV, PILOTO, CLOUD)
- [x] Portas sem conflito
- [x] Scripts .bat criados
- [x] Banco PILOTO criado e funcional
- [x] Usuário admin criado

### 📋 TODO:
- [ ] Configurar frontend para trocar URL do backend (DEV vs PILOTO)
- [ ] Preparar deploy CLOUD (Ocean)
- [ ] Implementar backup automático
- [ ] Sincronização LOCAL ↔ CLOUD
- [ ] Failover (se CLOUD cai, usar LOCAL)
- [ ] SSL/HTTPS no CLOUD
- [ ] Domínio mlprohub.com.br configurado

---

## 💡 ESTRATÉGIA: LOCAL + CLOUD (FAILOVER)

> **Sua pergunta:** *"Queria ter o online e instalado local na máquina pra se cair o online o local segue tocando"*

### ✅ SIM, É POSSÍVEL! Estratégias:

#### 1️⃣ **REDUNDÂNCIA SIMPLES**
- PILOTO rodando local na loja
- CLOUD rodando online
- Se internet cair → usa o PILOTO local
- Quando internet volta → sincroniza dados

#### 2️⃣ **SINCRONIZAÇÃO AUTOMÁTICA**
```
PILOTO (Local)  ←→  CLOUD (Online)
    ↓                    ↓
Backup a cada      Backup diário
  1 hora           para storage
```

#### 3️⃣ **FAILOVER AUTOMÁTICO** (Avançado)
- DNS dinâmico aponta para CLOUD
- Se CLOUD cai → DNS redireciona para IP local
- Requer IP fixo ou DDNS

---

**Próximo passo:** Preparar deploy CLOUD e implementar sincronização!

---

**Dúvidas?** Leia este guia com calma. Tudo está organizado! 🚀
