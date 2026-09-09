# Creditos CorePet — primeira entrega

## Objetivo e limite desta etapa

Preparar uma carteira por empresa para medir o uso de recursos pagos e mostrar
um orcamento antes de executar. Creditos comerciais CorePet nao sao os tokens
tecnicos de uma IA e nao representam uma tarifa universal do WhatsApp.

Esta entrega nao compra creditos de fornecedores, nao cobra cartao/Pix, nao
cria checkout Asaas, nao conecta novos numeros de WhatsApp e nao altera a
cobranca dos clientes em producao. Video, kit de imagens, rotas, campanhas e
recargas financeiras precisam de entregas e validacoes especificas.

O piloto envolve os pontos de geracao de imagem e descricao de produto ja
existentes. A chamada ao fornecedor continua tendo custo real quando usada;
`shadow` elimina o debito comercial, nao o custo da API.

O catalogo inicial e um rascunho para homologacao, nao uma tabela comercial
aprovada nem o custo real do fornecedor: 1 credito representa R$ 0,02;
descricao com sugestao fiscal custa 125 creditos (R$ 2,50); uma imagem custa
150 creditos (R$ 3,00). Descricao e fiscal separados ainda estao indisponiveis.
Os precos devem ser recalculados com consumo medido antes de vender pacotes.

Nesta entrega nao foi aplicada migracao em banco existente, nem habilitada
flag em `.env` ou em producao. As novas tabelas so foram criadas em bases de
teste isoladas.

## Modos e habilitacao controlada

| Configuracao | Finalidade |
|---|---|
| `COREPET_CREDITOS_MODE=off` | Padrao seguro; nova cobranca desativada. |
| `COREPET_CREDITOS_MODE=shadow` | Medir operacoes sem descontar saldo do cliente. |
| `COREPET_CREDITOS_TENANT_ALLOWLIST` | Restringir os tenants participantes, inclusive em shadow. |
| `enforced` | Fase de debito efetivo; nao liberar comercialmente nesta entrega. |

Nao habilitar um modo globalmente sem confirmar a lista de empresas, os
precos, as permissoes e os testes. Ativar uma flag nao substitui as etapas
de homologacao e autorizacao de producao. Nao colocar chaves de fornecedor,
dados pessoais, imagens em base64 ou prompts completos em logs de cobranca.

## Contrato operacional

O backend autenticado expoe o catalogo, carteira, extrato, orcamento e consulta
de operacao sob `/creditos`. A empresa vem da sessao autenticada, nunca de um
`tenant_id` escolhido no corpo da requisicao.

Um orcamento fica vinculado a:

- empresa e usuario que o solicitaram;
- servico e versao comercial usados no calculo;
- conteudo normalizado da solicitacao, incluindo a identidade da imagem;
- prazo de validade;
- identificador de idempotencia da operacao.

Ao confirmar, o servidor compara esses dados novamente. Um orcamento de
descricao nao autoriza uma imagem; trocar produto, prompt, foto ou orientacao
exige novo orcamento. O cliente deve preservar o identificador da operacao
enquanto aguarda a resposta e ao consultar uma execucao interrompida.

## Falhas e repeticoes

1. Reservar/registrar a operacao antes de chamar o fornecedor.
2. Uma repeticao da mesma operacao concluida retorna o resultado registrado.
3. Operacao em andamento ou de resultado incerto nao chama o fornecedor de novo.
4. Falha comprovada libera a reserva do cliente. Resposta recebida mas
   inutilizavel tambem pode liberar o cliente, mantendo o consumo do fornecedor
   para conciliacao: isso nao significa que a API devolveu o dinheiro.
5. Timeout ou conexao interrompida sem resposta conclusiva podem ter custo:
   manter a reserva para reconciliacao, sem estornar nem repetir cegamente.
6. Registrar apenas metadados de consumo permitidos e referencias tecnicas
   necessarias, separando custo do fornecedor do preco comercial CorePet.

O registro por empresa e a idempotencia precisam permanecer corretos mesmo
com duas requisicoes simultaneas, reenvio do navegador ou webhook repetido.

## Validacao local

Os testes desta etapa usam dados ficticios e fornecedores simulados. A suite
padrao usa SQLite; a suite opt-in usa PostgreSQL local descartavel. Nenhuma
delas precisa de `.env`, chave real, banco de producao ou API paga.
Executar a partir de `backend`, com variaveis explicitas
para nao herdar um destino de banco externo:

```powershell
$env:DATABASE_URL = 'sqlite://'
$env:ENVIRONMENT = 'test'
$env:JWT_SECRET_KEY = 'test-secret-key-min-32-chars-long-for-security'
$env:COREPET_CREDITOS_MODE = 'off'
.\.venv\Scripts\python.exe -m pytest tests/unit/test_creditos_api.py tests/unit/test_creditos_service.py tests/unit/test_creditos_migration.py -q
```

Foram validados isolamento entre empresas/usuarios, orcamento adulterado ou
expirado, retentativa sem chamada duplicada, incerteza do fornecedor e ausencia
de segredos nos retornos. Imagem usa multipart com identidade por URL ou hash
do arquivo. Os clientes OpenAI nao repetem automaticamente chamadas pagas.

Em 09/09/2026, os quatro testes de `test_creditos_postgres.py` passaram em
PostgreSQL local, com banco exclusivo e papel proprietario nao-superusuario:
concorrencia da mesma operacao e de operacoes diferentes, isolamento RLS,
integridade da empresa, bloqueio de UPDATE/DELETE/TRUNCATE do extrato e
resolucao de reserva incerta. A migracao foi executada duas vezes para
verificar repeticao segura. Banco e papel descartaveis foram removidos;
nenhuma tabela do banco de desenvolvimento existente foi alterada.

Para repetir essa suite, um operador deve criar outra base local descartavel
com prefixo `corepet_creditos_test_`, usar papel sem SUPERUSER/BYPASSRLS e
configurar somente `COREPET_CREDITOS_TEST_POSTGRES_URL`. Ela nao utiliza
`DATABASE_URL` da aplicacao e nao deve apontar para uma base com dados reais.
A aprovacao desses testes nao substitui o piloto integrado no navegador.

## Proximas etapas antes de vender pacotes

1. Conferir resultados em shadow com uma empresa piloto e limite de gasto.
2. Reconciliar custos reais e tentativas; aprovar uma tabela de precos por acao.
3. Homologar o fluxo completo na versao implantada, incluindo isolamento e
   transacoes concorrentes, sem substituir o banco existente por dados de teste.
4. Adicionar recarga com evento financeiro confirmado e idempotente, extrato
   auditavel, estorno/reembolso e regras comerciais claras.
5. Validar saldo insuficiente, abandono, reinicio e recuperacao de operacoes.
6. So entao ativar debito para tenants autorizados, com alertas e rollback.

Uma franquia de servico do WhatsApp, quando aplicavel, deve ser separada de
creditos comprados e de bonus comerciais: ela nao paga campanhas, imagens
ou rotas. Valores e limites de fornecedor devem ser consultados novamente
antes da definicao comercial e do lancamento.
