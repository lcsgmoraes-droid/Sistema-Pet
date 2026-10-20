# Relatório das tentativas de XML para contabilidade

## Comportamento

O histórico abre um relatório salvo por tentativa de envio individual, mensal
ou manual. Uma nova tentativa não reescreve a anterior. A seleção continua
exclusiva das notas emitidas no CorePet via INTnfe e dos eventos oficiais
dessas notas.

Emissões ainda sem confirmação não impedem o encaminhamento das outras notas
autorizadas completas. O resultado distingue envio com pendências, somente
pendências, falha de preparação, falha SMTP e envio aceito. O relatório informa
quais documentos foram preparados, enviados ou ficaram de fora, motivos,
orientação e atalho para conferir a emissão CorePet. Ausência de XML obrigatório
de uma nota autorizada ou de seu evento continua sendo erro de integridade.

São exibidos cancelamentos, sequências de CC-e e demais tipos de eventos.
Notas antigas incluídas apenas pelos eventos não aumentam o total de XMLs
de notas enviados no período. Totais monetários usam Decimal sobre o vNF do
XML já validado, sem consulta adicional ao emissor. Valores indisponíveis
não viram zero; canceladas são um subconjunto identificado separadamente.

Após regularizar uma pendência, é necessário solicitar um novo lote da
competência, que pode repetir notas já encaminhadas. A rotina não reemite
notas nem promete recuperar essa competência no próximo mensal.

## Execução e consulta

O POST apenas persiste o pedido. O scheduler existente usa uma thread de
segundo plano, com uma execução simultânea. Preparação, consultas fiscais,
compactação e SMTP não rodam na requisição que enfileira o envio. Histórico
e relatórios usam dados locais e não consultam o emissor. O detalhe é carregado
ao abrir e renderiza no máximo 25 documentos por página.

A migration aditiva `zzzzk20261020a1` cria os snapshots por tentativa com
FORCE RLS, chave estrangeira composta empresa/envio e histórico imutável.
Tentativas antigas sem snapshot são identificadas como sem relatório
detalhado, sem reconstruir fatos passados a partir do estado atual das notas.

## Verificação

- Suíte XML: **194 testes aprovados**, incluindo filas, snapshots, SMTP,
  pendências, reconciliação, cancelamentos, CC-e, valores, deduplicação e fuso.
- PostgreSQL local: **4 testes aprovados**, incluindo FORCE RLS até para o dono
  da tabela, vínculo composto empresa/envio, imutabilidade e reversão aditiva.
- Teste real do scheduler com a rotina artificialmente aguardando: histórico,
  configuração e event loop continuaram respondendo; ciclos não se sobrepuseram.
- Frontend: testes dos auxiliares, lint, formatação e build aprovados.
- Homologação reconstruída pelo script oficial, com migration aplicada e
  frontend/backend saudáveis. Configuração local existente preservada.
- Chrome no DEV autenticado: histórico com pendências, duas tentativas do mesmo
  envio, legado sem relatório, filtro de pendentes e abertura da nota exata
  aprovados. O valor da demonstração foi R$ 651,50 para três XMLs de notas,
  com R$ 250,50 em notas canceladas incluídas; uma emissão ficou pendente.
  Dois cancelamentos e duas sequências de CC-e foram contabilizados, incluindo
  um cancelamento de nota emitida em mês anterior sem repetir o valor da nota.

A massa é sintética, identificada como demonstração sem valor fiscal. O SMTP foi
simulado somente no processo de QA local e todas as chamadas HTTP externas
foram bloqueadas nesse processo. Nenhum e-mail real, emissão ou cancelamento
fiscal foi realizado. Capturas e logs ficam em `runtime/xml-contabilidade-qa`,
ignorados no Git. A produção permanece na versão anteriormente publicada.
