# Entrega - registro do acompanhamento de onboarding

Data: 2026-08-27

## Problema tratado

A fila de onboarding ja calculava quem precisava de atencao, mas nao permitia
registrar quem conduziria o acompanhamento, quando um impedimento foi resolvido
nem a percepcao inicial da empresa.

## Mudancas

- Responsavel interno pelo acompanhamento salvo por empresa.
- Data de desbloqueio opcional para registrar a resolucao de impedimentos.
- Satisfacao inicial com quatro estados controlados: nao coletada, satisfeita,
  neutra ou insatisfeita.
- Data da ultima atualizacao registrada automaticamente.
- API exclusiva do administrador da plataforma para salvar esses dados.
- Painel lateral editavel na aba `Pilotos` de `/ops/tenants`.
- Fila passa a priorizar ausencia de responsavel, satisfacao pendente, resposta
  neutra e insatisfacao.

## Estrutura e seguranca

- Os dados ficaram na entidade `tenants`, onde ja vivem os metadados
  operacionais da empresa; nao foi criado cadastro paralelo.
- A satisfacao possui validacao na API e restricao no PostgreSQL.
- A migration preenche empresas existentes com `not_collected`, sem apagar ou
  transformar dados anteriores.
- A escrita continua restrita ao login administrativo da plataforma.
- Nenhuma credencial ou dado de cliente foi colocado no repositorio.
- A entrega nao executa nem autoriza producao.

## Evidencia

A migration foi aplicada em PostgreSQL de homologacao, o formulario foi salvo
pelo navegador com administrador temporario e a fila mudou de uma pendencia
para zero. O usuario e os dados ficticios foram removidos ao final. Detalhes:
`docs/homologacoes/2026-08-27-registro-acompanhamento-onboarding.md`.
