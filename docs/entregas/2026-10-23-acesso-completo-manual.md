# Acesso completo por liberacao administrativa

Data: 2026-10-23. Responsavel de negocio: Lucas. Executor: Codex.
Prioridade: P1. Ambiente desta entrega: DEV; publicacao depende de autorizacao.

## 1. Necessidade e aceite

Lucas solicitou acesso completo sem vencimento para uma empresa, com retirada
do aviso de fim de teste e preservacao da situacao financeira. A politica de
continuidade ja mantinha o acesso apos o teste; faltava representar uma
liberacao administrativa independente de plano ou pagamento.

Aceite: concessao explicita libera recursos publicos e limites completos,
retira somente os avisos relacionados ao teste e respeita suspensao cadastral.

## 2. Regras e dados

`tenants.manual_full_access` registra a concessao, com padrao falso. Nao altera
plano contratado, `billing_status`, datas reais do teste, pagamentos,
vencimentos, comprovantes ou propostas. Nao configura nem contrata integracoes
fiscais/Bling. Modulos externos previamente concedidos continuam respeitados.

A migration e aditiva. Empresas existentes permanecem com a concessao
desativada. A ativacao e individual, auditada e sem data de vencimento.

## 3. Arquitetura e integracoes

A politica compartilhada em `billing_access.py` e usada por modulos,
entitlements e limites de vendas/sessoes. O resumo da assinatura expoe
`acesso_completo_manual`; os fatos de cobranca/teste permanecem reais.

A API administrativa usa a identidade global `PlatformAdmin`, distinta do
administrador da loja. Nao cria assinaturas cobradas nem processa pagamento.

## 4. Seguranca e privacidade

Concessao exige administrador global ativo e motivo. O evento registra a
identidade administrativa e o tenant alvo, sem confundir IDs de `users` e
`platform_admins`. O status cadastral continua soberano. Autenticacao, RBAC,
RLS e isolamento entre empresas permanecem.

## 5. Desenvolvimento e qualidade

Validar concessao e auditoria, preservacao financeira, administrador global,
isolamento, empresa suspensa, modulos, recursos e limites. Validar avisos de
teste e de cobranca separadamente e build do frontend. Resultados finais e
checks ficam registrados no PR desta entrega.

Validacao focada: 15 testes novos de concessao e suas regressoes (102 testes
backend no grupo executado) passaram; lint e formatacao Python passaram.
Avisos/contrato frontend, nove cenarios de consulta de modulos, lint,
formatacao e build de producao tambem passaram. O gate completo de release
permanece necessario antes de publicar.

Foi incluida tambem a correcao da falha de consulta de modulos: erro de rede
nao representa ausencia de contratacao. A interface oferece nova tentativa;
acesso previamente confirmado so e preservado para a mesma pessoa/empresa.
Trocas de escopo e respostas 401/403 invalidam a confirmacao. Testes cobrem
resposta atrasada e retorno para uma empresa anteriormente selecionada.

## 6. Ambientes e homologacao

Testes usam dados ficticios. A liberacao real deve ocorrer somente depois da
publicacao autorizada, com auditoria e verificacao da resposta da API e da tela.
Nenhum dado de DEV deve ser transferido para producao.

## 7. Publicacao e rollback

Entrega backend/frontend e migration aditiva; nao envolve mobile. Publicar
por PR e fluxo oficial, com build frontend e rebuild backend. Apos publicar,
ativar a concessao somente na empresa autorizada e conferir acesso e avisos.
Abortar se health/watchdog falharem. Rollback de codigo preserva os fatos
financeiros; a coluna aditiva pode permanecer sem uso. Nao executar downgrade
ou remocao da concessao sem avaliar o impacto no acesso autorizado.

## 8. Observabilidade e sustentacao

A auditoria comprova autor, motivo e concessao. O resumo distingue acesso
manual da situacao do teste. A indisponibilidade de rede de 23/10 esta
registrada separadamente em `docs/incidentes/2026-10-23-rede-hostinger.md`.

## 9. Comunicacao e rotina

O cliente recebe indicacao de acesso completo por liberacao administrativa,
sem vencimento. Avisos financeiros reais continuam disponiveis. Lucas decide
individualmente quais empresas recebem a concessao.

## 10. Fechamento

Implementacao e validacao em DEV. A publicacao e a ativacao em producao
exigem a autorizacao especifica para esta entrega; a autorizacao anterior
cobria diagnostico e recuperacao dos servicos existentes.
