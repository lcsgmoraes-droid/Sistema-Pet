# Migracao DigitalOcean -> Hostinger

Data de preparacao e execucao: 2026-08-07  
Janela executada: antecipada com autorizacao explicita do Lucas  
Estado: migracao concluida; Hostinger em producao e DigitalOcean preservada para rollback

## Resultado da execucao

- VPS Hostinger: KVM 4 em Campinas, Ubuntu 24.04, 4 vCPU, 16 GB de RAM e
  200 GB de disco;
- novo IPv4: `179.198.116.52`;
- dump final: `migration_final_20260807_130331.dump.gz`;
- SHA-256 do dump final:
  `0b1e515e76b397ae605e0eddfa8e11c202b7c19587a16e3051032cdff768716c`;
- restauracao final validada e restore smoke posterior aprovado com 243 tabelas
  publicas e uma revisao Alembic;
- backend, worker Bling, Nginx e PostgreSQL saudaveis na Hostinger;
- `corepet.com.br`, `www` e `img` apontados no Registro.br para a Hostinger;
- `mlprohub.com.br` e `www` apontados na Cloudflare para a Hostinger, mantendo
  o proxy;
- loja, login, health e API responderam HTTP 200 depois da propagacao;
- o app mobile manteve `https://corepet.com.br/api`, sem exigir nova build;
- certificados de `corepet.com.br` e `mlprohub.com.br` renovados ate
  2026-11-05; certificado de imagens valido ate 2026-10-28;
- simulacao de renovacao dos tres certificados aprovada e hook de recarga do
  Nginx instalado;
- backup local, restauracao descartavel e copia externa para o R2 aprovados por
  tamanho e SHA-256;
- token R2 limitado aos IPv4/IPv6 dos servidores de producao durante a janela
  de rollback;
- aplicacao, worker e Nginx da DigitalOcean parados sem politica de reinicio;
  PostgreSQL antigo mantido ligado e rotinas automaticas antigas desativadas.

Pendencias deliberadas: validar os fluxos funcionais que exigem acao humana ou
transacao real, acompanhar a nova VPS e cancelar a DigitalOcean somente depois
do periodo de seguranca e de nova autorizacao explicita.

## Decisao recomendada

Criar uma VPS Hostinger exclusiva para o CorePet, sem compartilhar o servidor do
ECOMMERCEAI.

Configuracao recomendada para a primeira migracao:

- Hostinger KVM 4;
- regiao Brasil, se estiver disponivel no momento da compra;
- Ubuntu 24.04 LTS limpo;
- 4 vCPU, 16 GB de RAM e 200 GB NVMe;
- backup semanal da Hostinger habilitado;
- acesso root inicial e chave SSH deste computador.

A KVM 2 provavelmente comporta a carga atual, mas a KVM 4 reduz o risco da
migracao e deixa margem para PostgreSQL, API, worker Bling, ecommerce, imagens e
novos clientes.

## O que existe hoje

Servidor de origem:

- provedor: DigitalOcean;
- Droplet: `MLPROHUB`;
- IP de origem: `192.241.150.121`;
- regiao: NYC1;
- Ubuntu 24.04;
- 2 vCPU, 4 GB de RAM e 25 GB de disco;
- projeto no host: `/opt/petshop`;
- servicos Docker: PostgreSQL, backend, worker Bling e Nginx.

Dados publicos observados em 2026-08-07:

| Nome | DNS atual | TTL | Administracao |
|---|---|---:|---|
| `corepet.com.br` | `192.241.150.121` | 3600 s | DNS do Registro.br |
| `www.corepet.com.br` | `192.241.150.121` | 3600 s | DNS do Registro.br |
| `img.corepet.com.br` | `192.241.150.121` | 3600 s | DNS do Registro.br |
| `mlprohub.com.br` | proxy Cloudflare | 300 s | DNS da Cloudflare |
| `www.mlprohub.com.br` | proxy Cloudflare | 300 s | DNS da Cloudflare |

Importante: `corepet.com.br` usa os nameservers `a.sec.dns.br` e
`b.sec.dns.br`. O dominio legado `mlprohub.com.br` usa os nameservers da
Cloudflare. Portanto, a virada completa exige acesso ao Registro.br e a
Cloudflare.

Baseline publico medido antes da migracao:

- paginas, loja publica e `/api/health`: HTTP 200;
- tempo observado nos checks simples: aproximadamente 0,46 a 0,52 segundo;
- raiz de `img.corepet.com.br`: HTTP 404 esperado, pois somente rotas de imagem
  sao publicadas;
- `/api/health/watchdog`: HTTP 404 intencional pela configuracao atual do Nginx.

Certificados observados:

- `corepet.com.br` e `www`: Let's Encrypt, vencimento em 2026-08-29;
- `img.corepet.com.br`: Let's Encrypt, vencimento em 2026-08-29;
- `mlprohub.com.br` e wildcard: Let's Encrypt apresentado pela Cloudflare,
  vencimento em 2026-09-19.

Os certificados CorePet precisam ser copiados com seguranca para o alvo durante
o ensaio e reemitidos/renovados no novo host logo depois da virada.

## O que precisa ser transferido

Nao copiar somente o banco. O pacote completo e:

1. PostgreSQL, por dump logico validado com checksum.
2. `/opt/petshop/.env`, sem imprimir ou enviar seu conteudo pelo chat.
3. `/opt/petshop/backend/uploads/`:
   - produtos;
   - ecommerce;
   - pets;
   - banho e tosa;
   - demais anexos criados pelo sistema.
4. `/opt/petshop/backend/data/`, incluindo snapshots e heartbeats necessarios.
5. `/opt/petshop/backend/secrets/`, preservando owner e permissoes.
6. Certificados atualmente montados em `/opt/petshop/nginx/ssl/`.
   A renovacao no alvo usa `scripts/certbot_deploy_nginx.sh` como deploy hook.
7. Configuracao de copia externa, se existir em
   `/etc/petshop/backup-external.env`.
8. Inventario das rotinas `/etc/cron.d/petshop-*` e dos wrappers
   `/usr/local/sbin/petshop-*`; eles devem ser reinstalados pelo codigo, nao
   copiados cegamente.
9. Evidencias operacionais e o ultimo backup valido. Logs antigos podem ficar
   arquivados no servidor de origem durante o periodo de seguranca.

Nunca copiar o volume bruto do PostgreSQL enquanto ele estiver em execucao. A
transferencia oficial do banco usa `scripts/prod_db_backup.sh` e restauracao
logica.

## O que nao deve mudar para os usuarios

Os nomes publicos serao preservados. Por isso:

- o app mobile continua usando `https://corepet.com.br/api`;
- nao e necessario publicar uma nova versao Android/iOS apenas por causa da
  troca de servidor;
- deep links `corepet://` e `https://corepet.com.br/app` continuam iguais;
- ecommerce e ERP continuam na mesma URL;
- links de e-mail, recuperacao de senha e confirmacao continuam iguais;
- URLs de webhook e OAuth continuam iguais.

O app ainda deve ser testado em aparelho real depois da virada, mas nenhuma
mudanca EAS, Firebase, Google Play ou App Store e esperada.

## Integracoes que precisam de validacao

Os valores secretos devem ser copiados, nunca recriados sem necessidade. A
chave `PAYMENT_CONFIG_ENCRYPTION_KEY` e critica: sem o mesmo valor, credenciais
de pagamento guardadas no banco podem deixar de ser decifradas.

| Integracao | O que preservar | Teste depois da virada |
|---|---|---|
| Bling | client, secret, tokens, tenant e worker | OAuth existente, fila, heartbeat e webhook |
| Mercado Pago | token, segredo de webhook, OAuth e chave de criptografia | configuracao, checkout e webhook controlado |
| Asaas | API key e token de webhook | status da assinatura e recebimento de webhook |
| SMTP | host, usuario, senha e remetente | e-mail controlado de recuperacao/confirmacao |
| Expo/Firebase/APNs | banco com tokens push e projeto EAS existente | login no app e push controlado |
| Google Maps | chave do backend e do build atual | mapa/rota em web e app |
| OpenAI/Groq/Gemini | chaves realmente habilitadas | uma consulta controlada por recurso ativo |
| WhatsApp/WAHA/360dialog | URL, tokens, sessao e webhooks ativos | status e mensagem controlada, se habilitado |
| Alertas Ops | webhook/e-mail e arquivo de deduplicacao | smoke de alerta sem revelar destino |

## Preparacao antes das 18h

### 1. Acessos e decisoes

- [ ] Comprar a VPS Hostinger separada.
- [ ] Anotar o novo IPv4 sem publica-lo em documentacao definitiva ainda.
- [ ] Confirmar acesso root por SSH.
- [ ] Confirmar acesso ao Registro.br de `corepet.com.br`.
- [ ] Confirmar acesso a Cloudflare de `mlprohub.com.br`.
- [ ] Confirmar que a chave SSH local de deploy sera instalada na VPS nova.
- [ ] Baixar o TTL dos tres registros CorePet de 3600 para 300 segundos, sem
      mudar o IP. Essa mudanca externa exige confirmacao no momento da acao.

### 2. Auditar a origem sem alterar nada

Executar, somente depois de autorizacao explicita para SSH de producao:

```bash
cd /opt/petshop
bash scripts/migration_inventory.sh source
```

Guardar apenas o relatorio sem secrets. Precisamos confirmar:

- tamanho real do banco;
- tamanho e quantidade dos uploads;
- espaco livre;
- commit em producao;
- versoes Docker, PostgreSQL, Node e Ubuntu;
- certificados e vencimentos;
- crons, wrappers, firewall e backups;
- containers ou servicos extras que nao estejam no Compose versionado.

### 3. Preparar a Hostinger

O script abaixo e para uma VPS nova. Ele nao clona o repositorio, nao recebe
senhas e nao inicia a aplicacao.

```bash
HOSTINGER_BOOTSTRAP_CONFIRM=HOSTINGER_BOOTSTRAP \
  DEPLOY_PUBLIC_KEY_FILE=/root/chave-publica-do-pc.pub \
  bash scripts/bootstrap_hostinger_vps.sh
```

Depois:

- [ ] Clonar `origin/main` em `/opt/petshop`.
- [ ] Conferir que o commit e o mesmo da producao.
- [ ] Copiar `.env`, uploads, data, secrets e certificados por SSH direto.
- [ ] Ajustar owner e permissoes sem abrir acesso publico.
- [ ] Subir PostgreSQL vazio no alvo.
- [ ] Restaurar um dump de ensaio.
- [ ] Construir frontend e backend.
- [ ] Validar migrations sem criar uma segunda linha de schema.
- [ ] Instalar os wrappers e crons versionados.
- [ ] Validar a VPS nova com `bash scripts/migration_inventory.sh target`.

### 4. Ensaio antes do DNS

Com certificados validos ja copiados para a VPS nova, testar pelo IP novo sem
alterar o DNS:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_hostinger_target.ps1 \
  -IpAddress "NOVO_IP"
```

O teste usa `curl --resolve`: envia o dominio correto diretamente para o novo
IP, mantendo a verificacao HTTPS.

Tambem validar manualmente, usando hosts local temporario ou navegador de teste:

- login do ERP;
- loja publica `/{slug}`;
- imagens de produto, ecommerce, pet e banho/tosa;
- um carrinho sem finalizar pagamento;
- painel Ops;
- estado do worker Bling;
- app mobile apontando para o dominio normal somente depois da virada.

## Roteiro da janela depois das 18h

Estimativa inicial: 20 a 45 minutos. A estimativa final depende do tamanho real
do banco e dos uploads medido pela auditoria.

### Ponto de controle A - antes de parar a origem

So continuar se todos os itens estiverem verdes:

- [ ] alvo restaurou o dump de ensaio;
- [ ] build e containers do alvo estao saudaveis;
- [ ] HTTPS do alvo passou com `--resolve`;
- [ ] primeiro rsync de uploads/data/secrets terminou;
- [ ] backup da origem existe, tem checksum e passou no restore smoke;
- [ ] Registro.br e Cloudflare estao abertos e autenticados;
- [ ] rollback foi lido;
- [ ] Lucas autorizou explicitamente os comandos de producao e DNS.

### Execucao

1. Registrar horario, commit de origem e responsaveis.
2. Interromper novas escritas parando backend e worker Bling na origem. O Nginx
   pode continuar exibindo o frontend, mas a janela deve ser tratada como
   manutencao.
3. Gerar o dump final do PostgreSQL e validar seu SHA-256.
4. Fazer o rsync final dos diretorios persistentes.
5. Restaurar o dump final no PostgreSQL da Hostinger.
6. Subir backend e worker no alvo; manter o Nginx do alvo pronto.
7. Validar internamente banco, migrations, health, watchdog e heartbeat.
8. Rodar `test_hostinger_target.ps1` contra o novo IP.
9. Alterar no Registro.br os registros `@`, `www` e `img` para o novo IP.
10. Alterar na Cloudflare o origin de `mlprohub.com.br` e `www` para o novo IP,
    mantendo o proxy e o modo SSL existentes.
11. Validar DNS por resolvedores diferentes.
12. Validar web, ecommerce, app mobile e integracoes.
13. Reabrir o sistema somente depois dos testes criticos.

Durante a janela, nao rodar migrations novas que nao estejam no mesmo commit da
origem. A migracao de servidor deve trocar infraestrutura, nao funcionalidade.

## Testes obrigatorios depois da virada

### Infraestrutura

- [ ] `https://corepet.com.br/health` retorna 200.
- [ ] `https://corepet.com.br/api/health` retorna 200.
- [ ] backend e worker estao healthy.
- [ ] PostgreSQL esta healthy e sem conexoes no servidor antigo.
- [ ] certificado cobre `corepet.com.br`, `www` e `img`.
- [ ] logs nao mostram loop de erro, falta de secret ou falha de conexao.

Observacao: hoje `/api/health/watchdog` publico retorna 404 por regra explicita
do Nginx. O watchdog deve ser validado internamente no container e pelo wrapper
operacional; nao usar o 404 publico como criterio de falha da migracao.

### ERP e ecommerce

- [ ] login, refresh de sessao e logout;
- [ ] abertura de caixa e consulta sem criar movimento desnecessario;
- [ ] produtos, estoque e imagens;
- [ ] loja publica por slug;
- [ ] carrinho, frete e checkout;
- [ ] pedido controlado e atualizacao de pagamento;
- [ ] e-mail de recuperacao ou confirmacao controlado;
- [ ] Bling: token, worker, fila e webhook;
- [ ] Asaas/Mercado Pago: URLs e assinatura dos webhooks;
- [ ] painel Ops e alertas criticos.

### App mobile

- [ ] abrir o app ja instalado, sem publicar nova build;
- [ ] selecionar loja e fazer login;
- [ ] listar produtos e carregar imagens;
- [ ] consultar/criar carrinho controlado;
- [ ] historico de pedidos;
- [ ] receber uma notificacao push controlada;
- [ ] deep link `corepet://` e link HTTPS do app;
- [ ] mapa/rota para um perfil habilitado, se aplicavel.

## Rollback

### Antes de qualquer escrita no alvo

Se o alvo falhar, manter o DNS na DigitalOcean e religar os servicos de origem.

### Depois do DNS, mas antes de reabrir o alvo

Apontar os registros novamente para `192.241.150.121`, confirmar a propagacao e
religar backend/worker na origem.

### Depois de permitir escritas no alvo

Nao voltar simplesmente para o banco antigo: pedidos, pagamentos e cadastros
podem divergir. Nesse caso:

1. bloquear novas escritas no alvo;
2. medir quais dados entraram depois da abertura;
3. decidir entre corrigir o alvo ou reconciliar os dados antes de retornar;
4. executar somente com nova autorizacao explicita.

## Depois da migracao

- manter a DigitalOcean intacta e desligada logicamente por pelo menos 7 dias;
- nao destruir o Droplet no mesmo dia;
- ativar e verificar backup semanal Hostinger;
- manter backup diario do banco e copia externa;
- rodar restore smoke no novo host;
- reemitir certificados no novo host e validar renovacao automatica;
- atualizar IP e SSH nos documentos/wrappers em um PR separado;
- substituir referencias ao IP antigo em `README.md`,
  `docs/FLUXO_UNICO_DEV_PROD.md`, `docs/PRODUCAO_DEPLOY_SSH.md`,
  `docs/PRODUCAO_ROLLBACK_CHECKLIST.md`,
  `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md` e
  `docs/SEGURANCA_ROTACAO_SSH_SECRETS.md`;
- apos a migracao, aposentar `deploy_completo_producao.sh`, que e legado e
  ainda contem IP antigo e um fluxo de push direto inadequado;
- atualizar monitoramento externo e eventuais allowlists por IP;
- registrar tempos, novo IP, checks e qualquer incidente sem incluir secrets;
- destruir a DigitalOcean somente depois de backup final externo, validacao e
  autorizacao explicita.

## Registro da execucao

| Campo | Valor |
|---|---|
| Inicio da janela | 2026-08-07, antecipada com autorizacao explicita |
| Commit migrado | `5c548467` |
| Novo IP | `179.198.116.52` |
| Dump final | `migration_final_20260807_130331.dump.gz` |
| SHA-256 | `0b1e515e76b397ae605e0eddfa8e11c202b7c19587a16e3051032cdff768716c` |
| Tamanho uploads | transferido no pacote final; manter inventario tecnico fora deste resumo |
| DNS Registro.br | concluido e validado em resolvedores publicos |
| DNS Cloudflare | concluido com proxy mantido |
| Health alvo | backend, worker, Nginx e PostgreSQL healthy; rotas publicas HTTP 200 |
| Ecommerce | paginas publicas e API aprovadas; checkout real nao executado |
| App mobile | endpoint preservado; teste manual no aparelho recomendado |
| Bling | worker healthy; transacao externa real nao executada |
| Pagamentos | configuracoes preservadas; pagamento real nao executado |
| Responsavel pela liberacao | Lucas |
| Fim da janela | 2026-08-07, infraestrutura e continuidade aprovadas |
