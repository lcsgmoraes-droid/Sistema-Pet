# CorePet - Go-live do dominio

Este runbook prepara a ativacao de `corepet.com.br` em paralelo com
`mlprohub.com.br`.

Ele nao autoriza deploy, SSH, alteracao no servidor, DNS ou redirecionamento.
Qualquer execucao em producao continua exigindo autorizacao explicita do Lucas.

## Objetivo

- Fazer `https://corepet.com.br` e `https://www.corepet.com.br` responderem a mesma aplicacao.
- Manter `https://mlprohub.com.br` funcionando durante a transicao.
- Validar API, login, e-commerce, app e Ops antes de qualquer redirecionamento.
- Deixar clientes novos recebendo links CorePet quando o dominio estiver validado.

## Ordem segura

1. Configurar DNS do dominio novo.
2. Adicionar `corepet.com.br` e `www.corepet.com.br` no Nginx.
3. Emitir ou expandir o certificado SSL.
4. Ajustar variaveis seguras do servidor.
5. Fazer deploy autorizado.
6. Validar dominio novo e dominio legado.
7. Somente depois decidir sobre redirecionamento do dominio antigo.

## DNS

No provedor DNS escolhido, criar:

| Tipo | Nome | Destino |
|---|---|---|
| A | `corepet.com.br` | IP publico do servidor atual |
| A ou CNAME | `www.corepet.com.br` | Mesmo destino do raiz |

Se usar Cloudflare, validar se o Nginx esta preparado para aceitar trafego pelos
IPs da Cloudflare. O `nginx/nginx.conf` atual ja tem allowlist de Cloudflare.

## Nginx

O bloco atual usa:

```nginx
server_name mlprohub.com.br www.mlprohub.com.br;
```

Para rodar os dois dominios em paralelo, a alteracao esperada e:

```nginx
server_name mlprohub.com.br www.mlprohub.com.br corepet.com.br www.corepet.com.br;
```

Aplicar nos blocos HTTP e HTTPS. Nao remover `mlprohub.com.br` nesta fase.

## SSL

O certificado precisa cobrir todos os nomes usados:

- `mlprohub.com.br`
- `www.mlprohub.com.br`
- `corepet.com.br`
- `www.corepet.com.br`

Validar o caminho real usado no servidor antes de qualquer alteracao:

```bash
sudo nginx -T | grep -E "server_name|ssl_certificate"
```

Se o certificado for gerenciado por Certbot, preparar a emissao/expansao para
incluir os dois nomes CorePet. Se houver Cloudflare Full Strict, conferir tambem
o modo SSL no painel Cloudflare.

## Variaveis do servidor

Quando o dominio novo estiver com SSL valido, preparar no `.env` seguro do
servidor:

```env
SYSTEM_NAME=CorePet ERP
FRONTEND_URL=https://corepet.com.br
ECOMMERCE_BASE_URL=https://corepet.com.br
ALLOWED_ORIGINS=https://corepet.com.br,https://www.corepet.com.br,https://mlprohub.com.br,http://localhost:5173,http://localhost:3000
SMTP_FROM=CorePet <noreply@corepet.com.br>
```

Observacoes:

- `mlprohub.com.br` fica em `ALLOWED_ORIGINS` enquanto houver acesso legado.
- `SMTP_FROM` so deve mudar quando o dominio/e-mail estiver autenticado para envio.
- Nao alterar tenants ou usuarios antigos sem roteiro explicito. A troca pontual do administrador para `atacadaopetpp@gmail.com` deve preservar `id`, `tenant_id`, senha, permissoes e historico.

## Validacao antes do deploy

Antes de deploy autorizado:

- PR mergeado na `main`.
- Checks do GitHub verdes.
- `git status --short --branch` limpo.
- Plano de rollback lido em `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`.
- Lucas autorizou explicitamente a execucao em producao.

## Validacao depois do deploy

Rodar os mesmos checks no dominio novo e no legado:

```bash
curl -fsS https://corepet.com.br/api/health
curl -fsS https://corepet.com.br/api/health/watchdog
curl -fsS https://mlprohub.com.br/api/health
curl -fsS https://mlprohub.com.br/api/health/watchdog
```

Validar no navegador:

- `https://corepet.com.br/login`
- `https://corepet.com.br/landing`
- `https://corepet.com.br/register`
- `https://corepet.com.br/termos`
- `https://corepet.com.br/privacidade`
- `https://corepet.com.br/ops` com usuario autorizado

Fluxos funcionais minimos:

- Login e renovacao de sessao.
- Logout.
- Recuperacao de senha gera link CorePet.
- Confirmacao de e-mail gera link CorePet.
- Loja publica por slug abre em `corepet.com.br/{slug}`.
- `robots.txt` aponta para sitemap CorePet.
- `sitemap.xml` lista URLs CorePet.

## App mobile

O app mobile ja esta com identidade CorePet, mas as URLs de API de build ainda
podem apontar para o dominio legado ate a validacao do dominio novo.

Trocar para `https://corepet.com.br/api` apenas quando:

- API e login estiverem validados no dominio novo.
- SSL estiver estavel.
- CORS estiver validado.
- Nova build do app for desejada.

## Redirecionamento do dominio antigo

Nao redirecionar `mlprohub.com.br` no primeiro go-live.

Decidir depois, com dados de uso e validacao dos clientes:

- manter dominio legado ativo;
- redirecionar apenas paginas publicas;
- redirecionar tudo para CorePet;
- manter excecoes para API/app mobile antigo.

## Registro

| Campo | Valor |
|---|---|
| Data/hora |  |
| Responsavel |  |
| Commit implantado |  |
| DNS validado |  |
| SSL validado |  |
| Health CorePet |  |
| Watchdog CorePet |  |
| Health legado |  |
| Watchdog legado |  |
| Observacoes |  |
