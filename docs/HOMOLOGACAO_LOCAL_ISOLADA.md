# Homologação local isolada

Atualizado em: 2026-08-26

Status: ambiente descartável oficial de aceite antes de produção, sem custo de
um segundo servidor e sem acesso aos dados reais dos clientes.

## Objetivo

Executar o sistema em uma configuração próxima de produção, porém isolada:

- frontend compilado pelo `frontend/Dockerfile.prod`;
- backend compilado pelo `backend/Dockerfile.prod`;
- backend em `ENVIRONMENT=staging`, `DEBUG=false` e PostgreSQL;
- PostgreSQL 14 próprio, sem conexão com produção;
- migrations aplicadas antes de liberar o backend;
- integrações que podem escrever fora do CorePet desativadas;
- conta, tenant e dados de teste fictícios;
- jornada E2E do Plano Básico executável pelo fluxo oficial.

O acesso fica limitado ao próprio computador em
`http://127.0.0.1:18080`. Este ambiente não é uma prévia pública para clientes e
não substitui um servidor de staging quando houver necessidade de acesso remoto,
teste de DNS/HTTPS ou carga contínua.

## Arquivos oficiais

- Orquestração: `docker-compose.homolog.yml`.
- Proxy local: `nginx/homolog.local.conf`.
- Exemplo sem segredos: `homolog.env.example`.
- Operação segura: `scripts/homologacao_local.ps1`.
- Prova automatizada: `.github/workflows/homologacao-isolada.yml`.
- Aceite: `docs/templates/REGISTRO_HOMOLOGACAO.md`.

O arquivo real `.env.homolog.local` é gerado com valores aleatórios, está
ignorado pelo Git e nunca deve ser enviado, copiado para documentação ou usado
em produção.

## Uso

Preparar credenciais locais sem exibi-las:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao preparar
```

Validar a configuração do Compose:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao verificar-config
```

Com o Docker Desktop aberto, construir e subir:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao subir
```

Executar a jornada funcional. Na primeira vez, o script cria uma empresa
fictícia e depois roda o E2E oficial:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao validar
```

Consultar estado:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao status
```

Parar preservando os dados descartáveis:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao parar
```

Apagar somente os volumes do projeto `corepet-homolog`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\homologacao_local.ps1 -Acao resetar -ConfirmarReset
```

O reset não remove arquivos do computador e não acessa produção. Ele apaga o
banco, uploads, dados e logs descartáveis mantidos em volumes Docker com o
prefixo do projeto de homologação.

## Regras de segurança

- Nunca restaurar backup de produção neste ambiente como rotina.
- Nunca copiar dados pessoais de clientes para preparar uma demonstração.
- Nunca habilitar Bling, iFood, Stone, Asaas real, SEFAZ real, WhatsApp, IA paga
  ou alertas externos sem uma tarefa específica e credenciais de sandbox.
- Nunca usar o endereço de produção como `E2E_BASE_URL`.
- Não expor a porta `18080` para a rede ou internet sem uma revisão de
  infraestrutura, autenticação, TLS e firewall.
- Resetar o ambiente quando a massa deixar de ser útil ou confiável.

## Evidência de homologação

O workflow `Homologacao Isolada` executa a mesma montagem em Linux no GitHub. Ele
valida contratos, gera segredos efêmeros, compila os Dockerfiles de produção,
aplica migrations, sobe frontend/backend/PostgreSQL, cria tenant fictício, roda
o E2E e apaga os volumes ao final. Não usa GitHub Secrets nem acessa produção.

Ele roda automaticamente quando a infraestrutura de homologação muda e pode ser
acionado manualmente para uma evidência adicional.

Para cada entrega relevante, registrar:

1. commit testado;
2. resultado de migrations;
3. health do frontend e backend;
4. comando e resultado do E2E ou cenários manuais;
5. inconsistências e severidade;
6. decisão de aceite.

Usar `docs/templates/REGISTRO_HOMOLOGACAO.md` e
`docs/PADRAO_EVIDENCIA.md`. A evidência não deve conter a senha gerada ou outros
segredos.

## Limites e gatilho para staging remoto

Criar um ambiente remoto separado quando pelo menos uma destas condições ocorrer:

- mais de uma pessoa precisar homologar ao mesmo tempo;
- cliente ou parceiro precisar acessar uma prévia;
- houver necessidade recorrente de testar HTTPS, DNS, webhooks ou aplicativo
  mobile fora da rede local;
- testes de carga precisarem de execução estável e repetível;
- a frequência de mudanças tornar a montagem local um gargalo;
- o risco financeiro justificar disponibilidade contínua do ambiente.

Essa evolução deve usar banco, segredos, storage e domínio próprios. Não se deve
compartilhar banco, volumes ou credenciais com produção.
