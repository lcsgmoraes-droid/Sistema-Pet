# Auditoria frontend, dependencias e producao - 2026-06-20

Auditoria feita em 2026-06-20, usando como referencia principal a producao publica e a branch `origin/main`, porque o deploy real do projeto puxa `origin/main` via `scripts/deploy_producao_seguro.sh`.

Nao foi executado SSH, deploy, push ou comando no servidor de producao. A leitura de producao foi feita somente por HTTP publico.

## Resumo executivo

- Producao esta no ar em `https://mlprohub.com.br`, `https://www.mlprohub.com.br`, `https://corepet.com.br` e `https://www.corepet.com.br`.
- `mlprohub.com.br` passa por Cloudflare; `corepet.com.br` respondeu direto por `nginx/1.29.5`.
- Os health checks publicos responderam `200`:
  - `https://mlprohub.com.br/api/health`: `{"status":"ok"}`
  - `https://corepet.com.br/api/health`: `{"status":"ok"}`
  - watchdog publico: `healthy`, banco conectado, latencia aproximada de 2,74 a 3,35 ms no momento da consulta.
- O bundle servido em producao foi gerado em 2026-06-20 14:05:38 UTC, portanto a leitura esta fresca.
- A producao serve `/assets/index-fWsiqFDt.js` e `/assets/index-CTKhQNom.css`.
- A producao bate com a linha de `origin/main`, que usa Vite 8 e Rolldown. A branch local foi rebaseada depois da auditoria inicial e agora nao tem diferenca de frontend contra `origin/main`.
- `npm audit` contra o lock de `origin/main` retornou 0 vulnerabilidades conhecidas.
- Antes do rebase, a branch local antiga retornava vulnerabilidades; isso nao representa mais o estado atual do frontend nesta branch.

## Estado do repositorio local

- Branch local: `fix/20260608-1703-seed-adquirentes-schema`
- `HEAD` local apos rebase: `8b2d52ff6d13eb94f35d8d144eba1ce18b0fd640`
- `origin/main`: `c4c76ff8132cfc45b5a2ed65e2a0e8d48e1b531e`
- Diferenca entre a branch local e `origin/main` no frontend apos rebase: 0 arquivos.

Conclusao pratica: a branch local agora esta segura como base para trabalho de frontend, porque o frontend nela esta alinhado com `origin/main`/producao.

## Stack frontend em producao/main

- Aplicacao: SPA React.
- Runtime UI: React 18.3.1 e React DOM 18.3.1.
- Roteamento: React Router DOM 6.30.4, com `BrowserRouter` e flags futuras de v7 (`v7_startTransition`, `v7_relativeSplatPath`).
- Bundler/build: Vite 8.0.16 com `@vitejs/plugin-react` 6.0.2.
- Bundler interno em producao: Rolldown aparece no bundle (`rolldown-runtime`), esperado com Vite 8.
- CSS: Tailwind CSS 3.4.19, PostCSS 8.5.15 e Autoprefixer 10.5.0.
- UI e componentes: `lucide-react`, `react-icons`, `react-hot-toast`, `recharts`, `driver.js`, `leaflet`.
- Markdown seguro/UI: `react-markdown`, `remark-gfm`; `dompurify` aparece transitive no lock e esta corrigido via override.
- Estado: Context API para auth/modulos e `zustand` para WhatsApp.
- HTTP: `axios` com base `/api`; em dev, Vite proxy para backend local.
- Tempo real: `socket.io-client` e servico WebSocket nativo.
- Exportacao/relatorios: `jspdf` e `write-excel-file`.
- Qualidade: `eslint`, `eslint-plugin-react-hooks`, `prettier`, `typescript`, `typescript-eslint`.
- Deploy real do frontend: build estatico em `runtime/frontend/dist`, servido pelo nginx de producao.

## Producao HTTP

| URL | Status | Servidor | Cache HTML | Observacao |
|---|---:|---|---|---|
| `https://mlprohub.com.br` | 200 | Cloudflare | `no-cache, no-store, must-revalidate` | Injeta Cloudflare Insights |
| `https://www.mlprohub.com.br` | 200 | Cloudflare | `no-cache, no-store, must-revalidate` | Mesmo bundle |
| `https://corepet.com.br` | 200 | `nginx/1.29.5` | `no-cache, no-store, must-revalidate` | Direto no nginx |
| `https://www.corepet.com.br` | 200 | `nginx/1.29.5` | `no-cache, no-store, must-revalidate` | Mesmo bundle |

Assets principais em producao:

| Asset | Tipo | Tamanho | Cache | Last-Modified |
|---|---|---:|---|---|
| `/assets/index-fWsiqFDt.js` | JS | 138443 bytes | `max-age=31536000, public, immutable` | 2026-06-20 14:05:38 UTC |
| `/assets/index-CTKhQNom.css` | CSS | 145331 bytes | `max-age=31536000, public, immutable` | 2026-06-20 14:05:38 UTC |

O JS de producao contem `/api`, nao contem `sourceMappingURL`, e portanto nao esta expondo source maps publicos no bundle principal.

## Dependencias diretas em producao/main

Legenda:

- `Atual`: lock esta igual ao `latest` do npm no momento da auditoria.
- `Maior pendente`: existe versao major mais nova; atualizar exige plano/testes.

### Runtime dependencies

| Pacote | Declarado | Lock usado | Latest npm | Status |
|---|---:|---:|---:|---|
| `@dnd-kit/core` | `^6.3.1` | `6.3.1` | `6.3.1` | Atual |
| `@dnd-kit/sortable` | `^10.0.0` | `10.0.0` | `10.0.0` | Atual |
| `@dnd-kit/utilities` | `^3.2.2` | `3.2.2` | `3.2.2` | Atual |
| `axios` | `^1.16.1` | `1.18.0` | `1.18.0` | Atual |
| `date-fns` | `^4.1.0` | `4.4.0` | `4.4.0` | Atual |
| `driver.js` | `^1.4.0` | `1.4.0` | `1.4.0` | Atual |
| `jspdf` | `^4.2.1` | `4.2.1` | `4.2.1` | Atual |
| `leaflet` | `^1.9.4` | `1.9.4` | `1.9.4` | Atual |
| `lucide-react` | `^0.300.0` | `0.300.0` | `1.21.0` | Maior pendente |
| `prop-types` | `^15.8.1` | `15.8.1` | `15.8.1` | Atual |
| `react` | `^18.2.0` | `18.3.1` | `19.2.7` | Maior pendente |
| `react-dom` | `^18.2.0` | `18.3.1` | `19.2.7` | Maior pendente |
| `react-hot-toast` | `^2.6.0` | `2.6.0` | `2.6.0` | Atual |
| `react-icons` | `^5.0.0` | `5.6.0` | `5.6.0` | Atual |
| `react-markdown` | `^10.1.0` | `10.1.0` | `10.1.0` | Atual |
| `react-router-dom` | `^6.30.4` | `6.30.4` | `7.18.0` | Maior pendente |
| `recharts` | `^2.15.4` | `2.15.4` | `3.8.1` | Maior pendente |
| `remark-gfm` | `^4.0.1` | `4.0.1` | `4.0.1` | Atual |
| `socket.io-client` | `^4.8.3` | `4.8.3` | `4.8.3` | Atual |
| `write-excel-file` | `^4.0.2` | `4.1.1` | `4.1.1` | Atual |
| `zustand` | `^5.0.11` | `5.0.14` | `5.0.14` | Atual |

### Dev dependencies

| Pacote | Declarado | Lock usado | Latest npm | Status |
|---|---:|---:|---:|---|
| `@eslint/js` | `^10.0.1` | `10.0.1` | `10.0.1` | Atual |
| `@types/react` | `^18.2.0` | `18.3.31` | `19.2.17` | Maior pendente |
| `@types/react-dom` | `^18.2.0` | `18.3.7` | `19.2.3` | Maior pendente |
| `@vitejs/plugin-react` | `^6.0.2` | `6.0.2` | `6.0.2` | Atual |
| `autoprefixer` | `^10.4.16` | `10.5.0` | `10.5.0` | Atual |
| `eslint` | `^10.5.0` | `10.5.0` | `10.5.0` | Atual |
| `eslint-plugin-react-hooks` | `^7.1.1` | `7.1.1` | `7.1.1` | Atual |
| `globals` | `^17.6.0` | `17.6.0` | `17.6.0` | Atual |
| `postcss` | `^8.4.32` | `8.5.15` | `8.5.15` | Atual |
| `prettier` | `^3.8.4` | `3.8.4` | `3.8.4` | Atual |
| `tailwindcss` | `^3.4.0` | `3.4.19` | `4.3.1` | Maior pendente |
| `typescript` | `^6.0.3` | `6.0.3` | `6.0.3` | Atual |
| `typescript-eslint` | `^8.61.1` | `8.61.1` | `8.61.1` | Atual |
| `vite` | `^8.0.16` | `8.0.16` | `8.0.16` | Atual |

## Auditoria de seguranca npm

Resultado usando `frontend/package-lock.json` de `origin/main`:

| Escopo | Vulnerabilidades |
|---|---:|
| Todas as dependencias | 0 |
| Somente producao (`--omit=dev`) | 0 |

Metadados do lock de `origin/main`:

- Dependencias de producao: 202
- Dependencias de desenvolvimento: 229
- Opcionais: 48
- Total informado pelo npm audit: 446

Observacao historica: antes do rebase, a branch local antiga apontava vulnerabilidades que ja tinham sido corrigidas em `origin/main` com atualizacoes e overrides, incluindo `dompurify` e `ws`.

## Achados e riscos

### 1. Branch local precisava ser atualizada antes do frontend

A auditoria inicial mostrou que a branch local estava antiga para frontend. Depois disso, ela foi rebaseada sobre `origin/main`; no estado atual, nao ha diff de frontend contra a base de producao.

Risco mitigado: trabalhar daqui em frontend ja nao deve reintroduzir a base Vite 6 antiga.

Recomendacao: para a proxima tarefa de frontend, criar branch nova a partir desta base atualizada ou de `origin/main`.

### 2. React 18 esta saudavel, mas nao e o mais novo

React e React DOM estao em 18.3.1; o npm ja aponta React 19.2.7. Nao e urgencia, mas e uma migracao relevante.

Recomendacao: tratar React 19 como projeto separado, com build, smoke autenticado, rotas principais, PDV, e-commerce e modulos com graficos.

### 3. React Router 6 ainda nao esta no major atual

O app usa `react-router-dom` 6.30.4. A `latest` desse pacote esta em 7.18.0. O codigo ja usa flags futuras, o que ajuda, mas nao substitui uma migracao testada.

Recomendacao: fazer a migracao para Router 7 depois de estabilizar a branch base; validar rotas publicas, `/ops`, rotas protegidas, ecommerce por slug e redirects.

### 4. Tailwind 3 continua correto, mas Tailwind 4 e uma migracao grande

Tailwind esta em 3.4.19; `latest` e 4.3.1. Como o projeto usa `tailwind.config.js` e PostCSS, a troca para v4 deve ser planejada.

Recomendacao: manter Tailwind 3 por enquanto se o objetivo for estabilidade. Migrar para 4 somente com comparacao visual e revisao de build/CSS.

### 5. `lucide-react` esta muito atras em major

O projeto usa muitos icones de `lucide-react` e o pacote esta em 0.300.0, com latest 1.21.0. O uso e alto no codigo.

Recomendacao: atualizar em uma branch propria e fazer build + smoke visual em telas com muitos icones, especialmente menu/layout, PDV, financeiro, campanhas e veterinario.

### 6. Google Analytics 4 esta configurado, mas o loader esta desativado em producao

O HTML de producao ficou assim:

```js
var id = "G-WPC2ZCFNWW";
if (!id || id === "G-WPC2ZCFNWW" || !id.startsWith("G-")) return;
```

Como a comparacao tambem foi substituida pelo mesmo valor real no build, a condicao sempre retorna e o script do GA nao carrega.

Risco: metricas de e-commerce podem estar zeradas ou incompletas mesmo com `VITE_GA_MEASUREMENT_ID` preenchido.

Recomendacao: alterar o `index.html` para comparar contra um placeholder literal que nao seja substituido pelo Vite, ou mover essa inicializacao para JS usando `import.meta.env`.

### 7. Dockerfiles foram atualizados na main para Node 22, mas o deploy real usa npm no host

Na `origin/main`, `frontend/Dockerfile` e `frontend/Dockerfile.prod` usam Node 22. Isso esta alinhado com Vite 8.

Porem o script real de producao roda:

```bash
cd frontend
npm ci
npm run build -- --outDir "../$NEXT_RUNTIME_DIST" --emptyOutDir
```

Ou seja, o build real depende do Node/npm instalado no host de producao, nao do Dockerfile do frontend.

Recomendacao: documentar/validar a versao de Node no servidor durante `petshop-status-producao` ou no deploy seguro. Vite moderno exige Node novo; hoje o build funcionou, mas vale deixar essa checagem explicita.

## Validacoes executadas

- `git status --short --branch`
- Leitura de `frontend/package.json`, `frontend/package-lock.json`, `vite.config.js`, Dockerfiles e configs.
- `npm outdated --json --long` na branch local antes do rebase, para comparar contra a base antiga.
- `npm audit --json` na branch local antes do rebase, para confirmar que os achados eram da base antiga.
- `npm audit --package-lock-only` usando `origin/main`.
- `git diff --stat origin/main...HEAD -- frontend` apos o rebase: sem diferenca.
- Consulta de `latest` no npm para dependencias diretas da `origin/main`.
- Build local de verificacao em pasta temporaria antes do rebase:
  - Vite 6.4.2 na branch local antiga.
  - 4437 modulos transformados.
  - 224 arquivos gerados.
  - 7502759 bytes brutos.
  - Build concluido com sucesso.
- HTTP publico em dominios de producao.
- HEAD/GET dos assets principais.

## Fontes externas consultadas

- npm React latest: `https://registry.npmjs.org/react/latest`
- npm Vite: `https://www.npmjs.com/package/vite`
- npm `@vitejs/plugin-react`: `https://www.npmjs.com/package/%40vitejs/plugin-react`
- npm Tailwind CSS: `https://www.npmjs.com/package/tailwindcss`
- npm React Router DOM: `https://www.npmjs.com/package/react-router-dom`
- npm Recharts: `https://www.npmjs.com/package/recharts`
- npm Axios: `https://www.npmjs.com/package/axios`
- npm Lucide React: `https://www.npmjs.com/package/lucide-react`
- Vite guide/Node support: `https://vite.dev/guide/`

## Proximos passos sugeridos

1. Corrigir o loader do Google Analytics em uma branch pequena.
2. Criar uma tarefa separada para migrar React Router 6 -> 7.
3. Criar uma tarefa separada para avaliar React 19.
4. Atualizar `lucide-react` em uma branch propria e validar telas com muitos icones.
5. Adiar Tailwind 4 ate haver tempo para comparacao visual completa.
6. Adicionar checagem explicita de Node/npm do servidor no fluxo de deploy/status.
