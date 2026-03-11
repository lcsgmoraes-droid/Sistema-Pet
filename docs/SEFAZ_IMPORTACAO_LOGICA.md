# SEFAZ — Lógica Completa da Importação Automática e o Erro 656

> Documento técnico para entender como o sistema busca NF-e na SEFAZ,
> como o agendamento automático funciona, o que é o erro 656 e como o sistema tenta se defender dele.

---

## 1. O que é a importação SEFAZ?

O sistema consulta a SEFAZ periodicamente para buscar **NF-e de entrada** — notas fiscais emitidas por fornecedores contra o CNPJ da loja.

O protocolo usado é o **NF-e DistDFeInt** (Distribuição DF-e de Interesse) via SOAP/HTTPS.
Cada chamada retorna um lote de até 50 documentos a partir de um número chamado **NSU** (Número Sequencial Único).

---

## 2. O que é o NSU?

O NSU é um contador crescente mantido pela SEFAZ. Cada documento (NF-e, evento, etc.) tem um NSU único e sequencial por CNPJ.

- O sistema guarda o **último NSU recebido** (`ultimo_nsu`) no arquivo de configuração.
- A cada chamada, envia esse NSU para a SEFAZ e recebe os documentos **a partir dali**.
- A resposta traz também o `maxNSU` — o maior NSU disponível no momento.
- Quando `ultimo_nsu == maxNSU`, não há documentos novos.

---

## 3. Onde fica a configuração?

Cada tenant (loja) tem um arquivo JSON em:

```
/app/secrets/sefaz/{tenant_id}/config.json
```

Campos principais:

| Campo | Descrição |
|-------|-----------|
| `enabled` | Liga/desliga a integração |
| `modo` | `"mock"` (simulado) ou `"real"` (produção) |
| `ambiente` | `"homologacao"` ou `"producao"` |
| `uf` | UF do emitente (ex: `"SP"`) |
| `cnpj` | CNPJ da loja (apenas números) |
| `cert_path` | Caminho do certificado A1 `.pfx` |
| `cert_password` | Senha do certificado |
| `importacao_automatica` | `true` habilita o scheduler automático |
| `importacao_intervalo_min` | Intervalo entre sincronizações (padrão: 60 min) |
| `ultimo_nsu` | Último NSU processado com sucesso |
| `ultimo_sync_at` | Horário real da última tentativa (exibido na tela) |
| `ultimo_sync_status` | `"ok"` ou `"erro_656"` |
| `ultimo_sync_mensagem` | Texto descritivo exibido na tela |
| `_proximo_sync_permitido_at` | Horário mínimo para a próxima chamada (controle interno — pode ser futuro em caso de penalidade por 656, ou igual a `ultimo_sync_at` em caso de sucesso) |

---

## 4. Fluxo de uma chamada à SEFAZ

```
scheduler (a cada 1 min) ou botão manual
        │
        ▼
Verifica se passou intervalo desde ultimo_sync_at
  (ver seção 6 para detalhe da lógica de cooldown/intervalo)
        │
        ▼
SefazService.sincronizar_nsu(config, ultimo_nsu)
        │
        ├── Monta XML da requisição (distNSU com ultNSU=ultimo_nsu)
        ├── Extrai cert + chave do .pfx para arquivos temporários .pem
        ├── POST SOAP para https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/...
        ├── Recebe resposta XML
        ├── Verifica cStat:
        │     137 → ok, documento(s) retornado(s)
        │     138 → ok, nenhum documento novo
        │     656 → BLOQUEIO (Consumo Indevido) → lança exceção
        │     outros → lança exceção com detalhes
        └── Retorna: { ultimo_nsu, max_nsu, docs_list, c_stat, ... }
```

---

## 5. O que acontece com os documentos recebidos?

Os documentos chegam zipados em base64 dentro do XML da resposta.
O sistema descomprime, parseia e salva no banco via `importar_docs_sefaz()`.

Tipos de documento que a SEFAZ pode retornar:
- **NF-e completa** (schema `procNFe`): tem todos os dados — emitente, itens, valores
- **Resumo de NF-e** (schema `resNFe`): apenas dados básicos — sem itens detalhados

---

## 6. O scheduler automático

**Arquivo:** `backend/app/main.py` — função `_loop_sefaz_sync()`

O scheduler roda como **thread em background** dentro do processo uvicorn.

```
Startup do FastAPI
    │
    └── Aguarda 90 segundos (deixa o backend subir completamente)
    │
    └── Loop infinito (a cada 60 segundos verifica todos os tenants):
          Para cada tenant com config.json:
            1. Tem importacao_automatica=true? (senão: pula)
            2. Tem enabled=true? (senão: pula)
            3. Modo é "real"? (senão: pula)
            4. Certificado existe no caminho? (senão: pula)
            5. Verifica cooldown/intervalo → ver lógica abaixo
            6. Se passou: executa até 3 lotes de 50 docs (com 2s de pausa entre lotes)
            7. Salva resultado no config.json
```

### Lógica de cooldown/intervalo (versão atual após commit 2b4cb583)

```
Verificação 1 — Penalidade por 656:
  Se _proximo_sync_permitido_at > agora → PULA (ainda em penalidade)

Verificação 2 — Intervalo normal:
  Se (agora - ultimo_sync_at) < importacao_intervalo_min → PULA (muito cedo)
```

- Se `_proximo_sync_permitido_at` não existe ou já passou: vai para verificação 2
- Se `ultimo_sync_at` não existe: executa imediatamente

### Versão anterior (antes do commit 2b4cb583) — bug de timing

A versão anterior usava um único campo `marcador_intervalo`, que era
`_proximo_sync_permitido_at` ou, se não existisse, `ultimo_sync_at`.
Após um 656, o marcador ficava no futuro (+70 min), e a condição era
`(agora - futuro) < 60` → negativo < 60 = verdadeiro = **pula**.
Só executava quando o campo estivesse no passado **e** tivessem passado 60 min desde ele,
resultando em ~130 min de espera em vez de 70 min.
**Isso era ineficiente mas não causava chamadas extras.**

---

## 7. Multiple workers — como o sistema evita chamadas duplicadas

Em produção o uvicorn roda **4 workers** (4 processos independentes, cada um com sua própria thread).
Cada worker inicia o scheduler na sua thread — ou seja, haveria **4 schedulers tentando sincronizar ao mesmo tempo**.

Para evitar isso, o scheduler usa um **lock de arquivo** (`/tmp/sefaz_sync.lock`):

```python
fcntl.flock(lock_file, LOCK_EX | LOCK_NB)
```

- O worker que consegue o lock executa a sincronização
- Os outros 3 workers chegam ao lock, falham (`OSError`), e esperam 60 segundos antes de tentar novamente
- Funciona apenas em Linux (usa `fcntl`) — no Windows o `import fcntl` falha e todos os workers tentam executar

---

## 8. O erro cStat 656 — "Consumo Indevido"

### O que é?

A SEFAZ bloqueia quando detecta que o mesmo CNPJ está consultando com **muita frequência** ou **sem necessidade**.

A regra exata não é pública, mas comportamentos que provocam 656:
- Chamar com o mesmo `ultNSU` repetidamente quando `ultNSU == maxNSU` (sem novos documentos)
- Muitas chamadas em curto espaço de tempo
- Múltiplos workers chamando simultaneamente (sem lock funcional)

### O que o sistema faz ao receber 656?

1. Captura o erro no bloco `except exc_lote`
2. Seta `_proximo_sync_permitido_at = agora + 70 min`
3. Seta `ultimo_sync_status = "erro_656"`
4. Seta `ultimo_sync_mensagem = "SEFAZ bloqueou... aguarde 70 min"`
5. Salva no `config.json`
6. Frontend lê esse status e:
   - Mostra banner vermelho com aviso
   - Desabilita botão "Sincronizar agora" com contador regressivo

### Por que o 656 pode reaparecer?

Hipóteses a investigar:

| Hipótese | Descrição | Status |
|----------|-----------|--------|
| **Lock não funcionando** | Em Linux o `fcntl` deveria funcionar, mas se `/tmp/sefaz_sync.lock` for compartilhado entre containers não funciona — 4 workers sincronizando ao mesmo tempo | A confirmar |
| **Mesmo NSU consultado** | Quando `ultimo_nsu == maxNSU`, a cada 60 min o sistema faz uma chamada que retorna "nenhum documento". A SEFAZ pode interpretar consultas repetidas com mesmo NSU como abuso | Provável |
| **3 lotes por ciclo** | Se houver muitos NSUs pendentes no primeiro sync, o sistema faz 3 chamadas seguidas com 2s de pausa. Pode acionar rate limit | Possível em 1° sync |
| **Restart do backend** | Ao reiniciar, o backend lê o `_proximo_sync_permitido_at` do arquivo e respeita o cooldown. Mas se houver demora no restart durante a penalidade ativa, o campo pode já ter expirado | Improvável |

---

## 9. Arquivos envolvidos

| Arquivo | Papel |
|---------|-------|
| `backend/app/main.py` | Loop do scheduler automático (`_loop_sefaz_sync`) |
| `backend/app/services/sefaz_service.py` | Chamada SOAP real para a SEFAZ, parsing do XML |
| `backend/app/routes/sefaz_routes.py` | Endpoint HTTP manual (`/sefaz/sync-now`) com verificação de cooldown |
| `backend/app/services/sefaz_tenant_config_service.py` | Leitura/escrita do `config.json` por tenant |
| `frontend/src/pages/SEFAZImportacao.jsx` | Tela de importação com botão manual, status e aviso de cooldown |
| `/app/secrets/sefaz/{tenant_id}/config.json` | Configuração e estado do tenant (no servidor) |

---

## 10. Diagnóstico das 8 perguntas

### 1️⃣ Onde roda o backend? O `/tmp` é compartilhado?

**Confirmado pelo código:** Docker container único no DigitalOcean (VPS).
Comando no `Dockerfile.prod`: `uvicorn app.main:app --workers 4`.

Com `--workers 4` no mesmo container, todos os 4 workers são processos filhos do mesmo OS,
rodam no mesmo filesystem e **compartilham o mesmo `/tmp`**.
O lock `/tmp/sefaz_sync.lock` funciona corretamente nesse cenário.

> ⚠️ Se o container for escalado horizontalmente (duas réplicas do mesmo container),
> o lock **não funciona** — cada réplica tem seu próprio `/tmp`.
> Atualmente há apenas 1 container de backend em produção, então está seguro.

---

### 2️⃣ Como o uvicorn é iniciado?

Exatamente:
```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info --access-log
```

Com `--workers 4`, o uvicorn usa a biblioteca `multiprocessing` e **faz fork** de 4 processos.
Cada processo é independente na memória e roda o `startup` event handler do FastAPI — ou seja,
**4 schedulers são iniciados simultaneamente**, um por worker.

A coordenação é feita pelo `fcntl.flock(LOCK_EX | LOCK_NB)`:
- O worker que pegar o lock executa a sincronização
- Os outros 3 falham na tentativa de lock e dormem 60 segundos

Isso funciona — **mas** os 4 workers ficam em ciclos de 60 segundos levemente deslocados.
Quando o intervalo de 60 minutos passa, pode haver uma janela onde 2+ workers tentam
o lock ao mesmo tempo. Apenas 1 pega, os outros dormem. A verificação de intervalo
(`ultimo_sync_at`) garante que, quando o segundo worker tentar de novo 60 segundos depois,
veja que o primeiro já executou e pule.

---

### 3️⃣ Quantos tenants existem?

**Precisamos verificar no servidor:**
```bash
ls /app/secrets/sefaz/
```

O scheduler itera **todos** os diretórios em `secrets/sefaz/`. Se houver múltiplos tenants
com `importacao_automatica=true`, cada um gera suas próprias chamadas à SEFAZ, mas cada
chamada é por um CNPJ diferente — o limite da SEFAZ é **por CNPJ**, então múltiplos tenants
não somam as chamadas.

Hoje o tenant de produção conhecido é `180d9cbf-5dcb-4676-bf11-dcbd91ed444b`.

---

### 4️⃣ Quando aconteceu o 656?

**Do config.json em produção:** `_proximo_sync_permitido_at = 2026-03-11T03:24:54 UTC`
→ o erro ocorreu por volta de **02:14 UTC (23:14 BRT do dia 10/03)**.

O backend foi reiniciado às **23:28:39 BRT** (02:28:39 UTC). Isso significa que o 656
aconteceu ANTES do último restart do backend — ou seja, o erro veio de um ciclo anterior.

**Padrão provável: categoria B — após horas de uso.** O scheduler rodou por um tempo,
fez chamadas periódicas, e em algum momento a SEFAZ bloqueou.

---

### 5️⃣ Qual era o NSU no momento do erro?

**Precisamos verificar no arquivo:**
```bash
cat /app/secrets/sefaz/180d9cbf-5dcb-4676-bf11-dcbd91ed444b/config.json
```

Isso é crítico para entender a causa. Dois cenários:

| Cenário | NSU no erro | O que significa |
|---------|-------------|-----------------|
| **A** | `ultimo_nsu == max_nsu` | Não havia documentos novos. O sistema chamou a SEFAZ N vezes com o mesmo NSU sem necessidade → causa provável do 656 |
| **B** | `ultimo_nsu < max_nsu` | Havia documentos pendentes. O sistema fez muitas chamadas seguidas tentando alcançar o maxNSU (3 lotes × várias horas) → também pode causar 656 |

---

### 6️⃣ Há múltiplas chamadas simultâneas nos logs?

Com o lock funcionando, **não deveria haver**. Mas o lock tem uma brecha:

**O `sync-now` (botão manual) NÃO usa o mesmo lock de arquivo.**
Se alguém clica "Sincronizar agora" enquanto o scheduler está executando:
- Scheduler: lock adquirido → chamando SEFAZ
- sync-now:  sem lock → também chamando SEFAZ

Resultado: **2 chamadas simultâneas para o mesmo CNPJ na SEFAZ.** Isso pode acionar 656.

Para confirmar nos logs:
```bash
docker logs petshop-prod-backend --since="2026-03-10T20:00:00" 2>&1 | grep -E "SEFAZ|sefaz"
```

---

### 7️⃣ Pode haver chamada manual simultânea com o scheduler?

**Sim, é possível.** O endpoint `POST /sefaz/sync-now` é independente do scheduler.
Se o botão for clicado enquanto o scheduler está no meio de uma sincronização:
- Scheduler: processo worker 1, usa `fcntl` lock
- sync-now: processo worker 2 (ou qualquer outro), **não usa lock**

→ **Duas chamadas SOAP ao mesmo tempo para o mesmo CNPJ.**

A proteção existente no `sync-now` é apenas contra **penalidade ativa** (verificar
`_proximo_sync_permitido_at`). Não há proteção contra concorrência com o scheduler.

---

### 8️⃣ O primeiro sync pode ter gerado muitas chamadas?

**Sim, esse é o cenário mais provável para o 656.**

Se `ultimo_nsu` era `000000000000000` quando a importação foi ativada, e a loja tem
meses de NF-e acumuladas na SEFAZ, o processo seria:

```
Ciclo 1: 3 lotes × 50 docs = 150 docs, novo_nsu ainda < max_nsu
Ciclo 2 (60 min depois): 3 lotes × 50 docs = mais 150 docs
Ciclo 3 (60 min depois): 3 lotes × 50 docs = mais 150 docs
...
```

Isso é controlado — 60 min entre ciclos. Porém, se alguém clicou em
"Buscar pela SEFAZ" manualmente enquanto o scheduler rodava, os ciclos se sobrepõem.

**Outra causa:** se o sistema foi reiniciado várias vezes em pouco tempo
(durante testes de configuração), cada restart inicia um novo scheduler que,
após 90 segundos, verifica se passou o intervalo. Se o `ultimo_sync_at` não foi
atualizado corretamente (ex: o restart foi antes de o config.json ser gravado),
o novo scheduler pode executar imediatamente, sem respeitar o intervalo anterior.

---

### Conclusão — causa mais provável do 656

Com base no código e no padrão de quando ocorreu:

1. **Mais provável:** Chamada manual (`sync-now`) executada simultânea com o scheduler,
   gerando 2 chamadas SOAP ao mesmo CNPJ ao mesmo tempo

2. **Provável:** Na fase inicial, quando havia muitos NSUs pendentes e alguém também
   acionou o botão manual — acumulando muitas chamadas em pouco tempo

3. **Menos provável mas possível:** Consultas repetidas com mesmo NSU (quando
   `ultimo_nsu == maxNSU`) a cada hora — a SEFAZ pode interpretar como abuso se
   isso durar muitos dias sem documentos novos

---

## 11. Linha do tempo de um ciclo normal (sem erro)

```
T+0min    Scheduler verifica: passou 60 min desde ultimo_sync_at? SIM
T+0min    Chama SefazService.sincronizar_nsu(nsu=ultimo_nsu)
T+0min    SEFAZ retorna: cStat=137, 2 documentos, max_nsu=987
T+0min    Importa 2 NF-e no banco
T+0min    nsu_loop = 987
T+0min    max_nsu = 987 → nsu_loop >= max_nsu → para o loop de lotes
T+0min    Salva: ultimo_nsu=987, ultimo_sync_at=agora, _proximo_sync_permitido_at=agora, status=ok
T+60min   Scheduler verifica: passou 60 min? SIM
T+60min   Chama com nsu=987
T+60min   SEFAZ retorna: cStat=138, 0 documentos, max_nsu=987 (nenhum novo)
T+60min   Salva: ultimo_nsu=987 (mantém), status=ok, "Nenhum documento novo"
```

## 11. Linha do tempo com erro 656

```
T+0min    Scheduler chama SEFAZ
T+0min    SEFAZ retorna: cStat=656, "Consumo Indevido"
T+0min    Salva: _proximo_sync_permitido_at = T+70min, status=erro_656
T+1min    Scheduler verifica: _proximo_sync_permitido_at (T+70min) > agora → PULA
T+2min    (repete: pula)
...
T+70min   _proximo_sync_permitido_at chegou → Verificação 1 passa
T+70min   Verifica intervalo: (agora - ultimo_sync_at) = 70 min >= 60 min → Verificação 2 passa
T+70min   Executa sync normalmente
```
