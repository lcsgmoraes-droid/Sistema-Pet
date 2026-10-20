# Homologação — XML das notas emitidas no CorePet

| Campo | Valor |
|---|---|
| Data | 2026-10-19 |
| Escopo | NF-e/NFC-e emitidas no CorePet pela IntNFe em produção e seus eventos oficiais |
| Entrega inicial | PR #1530, publicada com autorização do Lucas no commit `dd1c0d5b` |
| Ajuste de origem | PR #1531, antes da publicação |
| Ambientes | SQLite descartável, PostgreSQL DEV, UI simulada e teste de e-mail autorizado |

## Origem e critérios de aceite

A rota `POST /nfe/emitir` emite exclusivamente pela IntNFe. A seleção contábil
utiliza as vendas da empresa com `nfe_provider=intnfe` e `nfe_ambiente=1`.
Cache e notas emitidas no Bling para marketplaces não participam do lote,
mesmo com o mesmo CNPJ, número ou período de uma nota CorePet.

Essa regra vale para lookup, seleção manual/mensal, monitoramento, hooks,
comprovantes persistidos e trabalhos individuais antigos. Uma nota CorePet com
referência fiscal ausente continua candidata e bloqueia a confirmação de todos
os eventos; não é escondida como "sem notas". XMLs e comprovantes são validados e
preservados, incluindo todas as sequências de CC-e e cancelamentos oficiais.

## Cenários

| Cenário | Evidência |
|---|---|
| Individual e mensal independentes | Quatro combinações de flags; ativação não envia histórico |
| Mês anterior completo | Fevereiro 28/29, meses 30/31, virada de ano e fuso Brasília |
| Notas CorePet, outros providers e cache no mesmo período | Lookup, seleção e referências isolam origem e tenant |
| Eventos novos de notas antigas CorePet | Consulta oficial IntNFe e inclusão pelo registro do evento |
| Fila/evento antigo de outra origem | Bloqueio antes de SMTP, sem recuperar comprovante Bling |
| XML/protocolo/chave/modelo/emitente/ambiente inválido | Bloqueio do lote incompleto |
| Cancelamento, substituição NFC-e e CC-e com várias sequências | ZIPs por tipo e um XML por envio individual |
| PostgreSQL e migrations | Três testes reais com FORCE RLS e smoke clean/history/production_uuid aprovados na entrega inicial |
| UI desktop e 390/320px | Sem overflow; dia/hora visíveis e carregamento único em StrictMode |

Os testes locais usam dados fictícios. O PostgreSQL cria schema/papel temporários
sem bypass de RLS e encerra em rollback. Builds, capturas, logs e ZIPs de teste
ficam em `runtime/xml-contabilidade-qa`, ignorado no Git.

## Conferência autorizada em produção

- O PR #1530 publicou somente XML para contabilidade; o catálogo iFood do #1526
  não foi publicado nesta entrega.
- O XML individual real chegou ao Gmail indicado. O SHA-256 do anexo recebido
  correspondeu ao conteúdo enviado pelo sistema.
- O lote de setembro foi bloqueado porque uma emissão CorePet continua em
  processamento na IntNFe; nenhuma nota foi omitida para produzir sucesso parcial.
- A investigação posterior de XMLs externos do Bling esteve fora do escopo e foi
  retirada da adaptação antes de publicá-la. Nenhum XML Bling foi enviado por SMTP.
- Nenhuma emissão, cancelamento ou alteração manual de situação fiscal foi feita
  para criar massa de teste. Eventos inexistentes não são simulados em produção.

As configurações começam com os automatismos desligados e sem destinatário.
O teste pontual não ativa o envio recorrente. Aceite SMTP significa aceitação pelo
servidor; a entrega real só é afirmada quando conferida na caixa de entrada.

## Validação do ajuste de origem

A suíte XML passou com **168 testes**, comprovando a exclusão das outras origens
e preservando os casos mensal, manual e individual com documentos IntNFe.
Ruff, formatação e `git diff --check` foram aprovados. O build e o gate oficial
de release permanecem necessários antes da publicação do PR #1531.
