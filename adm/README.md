# CorePet · Administração (adm)

Projeto separado do sistema principal. Destino: `adm.corepet.com.br` (substitui o OPS).
**Ainda não publicado.** Publicar exige autorização explícita (DNS, nginx, variáveis do backend).

## O que tem (PMV)
- Login próprio (`/adm/auth/*`), sem cadastro: os acessos são criados por script.
- Menu lateral + conteúdo. Dashboard vazio (conteúdo a decidir).
- Lojas: lista com módulos ativos, usuários e último acesso; detalhe com ligar/desligar módulos
  (sem compra/pagamento), plano e cobrança, usuários e histórico de alterações.
- Trocar a própria senha a qualquer momento (obrigatório no primeiro acesso de senha provisória).

## Rodar em desenvolvimento
```
cd adm
npm install
npm run dev        # porta 5176; /api vai para o backend (ADM_BACKEND_URL, padrão http://localhost:8000)
npm test && npm run lint && npm run build
```

## Segurança (resumo)
- Token de acesso só em memória; renovação por cookie `HttpOnly`, `SameSite=Strict`, `Secure` em produção,
  com rotação e detecção de reuso. Tempo máximo de sessão e desconexão por inatividade (30 min).
- Mesma origem via `/api` (sem CORS); o backend confere a origem e o cabeçalho `X-Corepet-Adm`.
- Erros de login genéricos, bloqueio por tentativas, limite de requisições, senha mínima de 12 caracteres.
- Acesso ao painel é uma permissão por pessoa (`painel_adm_ativo`), desligada por padrão.

## Administrar acessos
```
python scripts/criar_admin_plataforma.py criar --email x@y.com --provisoria
python scripts/criar_admin_plataforma.py nova-senha|desativar|ativar|liberar-painel|bloquear-painel|listar ...
```
Em desenvolvimento: `admin@teste.com` / `admin1` (senha fraca só local; o script recusa em produção).

## Variáveis do backend para produção
`ADM_ALLOWED_ORIGINS` (incluir `https://adm.corepet.com.br`), `ADM_SESSION_HOURS`, `ADM_COOKIE_SECURE=true`.

## Próximos passos sugeridos
Verificação em duas etapas (2FA), conteúdo do dashboard, edição de plano/cobrança, migrar o que falta do OPS.
