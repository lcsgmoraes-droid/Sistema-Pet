# XML para contabilidade

Atualizado em: 2026-10-19.

Acesse **Configurações → XML para contabilidade**. Também há um atalho na
central de notas de saída. É necessário ter o módulo fiscal e a permissão
`configuracoes.editar` na empresa selecionada.

## Como usar

1. Confira o CNPJ da empresa e salve o e-mail do contador.
2. Para receber cada documento, ative **Enviar XML por XML: cada nota e seus eventos**.
   A autorização envia a nota e cada evento confirmado gera seu próprio envio de XML,
   inclusive cancelamento e novas sequências de CC-e posteriores à emissão.
3. Para o resumo mensal, ative **Enviar automaticamente o mês anterior completo**,
   escolha dia e hora e salve. Todo envio reúne do primeiro ao último dia do mês
   anterior à data programada, no horário de Brasília.
4. Para um período diferente, escolha as datas em **Envio manual por período** e clique em
   **Baixar ZIP** ou **Enviar agora**.
5. Acompanhe o resultado no histórico. Desligar uma opção preserva o histórico
   e cancela os respectivos envios ainda pendentes. Individual e mensal são
   independentes: podem ficar ligados juntos, separados ou ambos desligados.

Exemplo: no dia 1º de março, o lote contém fevereiro inteiro, até 28 ou 29.
No dia 1º de maio, contém abril até o dia 30; no dia 1º de agosto, julho até
o dia 31. Janeiro envia dezembro do ano anterior. O período não é uma janela
móvel de 30 dias. Se o dia escolhido para executar não existir no mês, a execução
ocorre no último dia desse mês, mantendo a competência anterior completa.

Datas são interpretadas em `America/Sao_Paulo`. As datas inicial e final do
período são inclusivas. Períodos livres são exclusivamente manuais: não há
agendamento avulso de um intervalo personalizado. O envio individual considera
novas notas e eventos confirmados após a ativação, sem disparar todo o histórico.
Um evento novo de uma nota antiga também é elegível. O usuário pode deixar
os automatismos desligados e usar apenas os lotes manuais.

O download não exige e-mail configurado. Os envios usam o SMTP já existente no
sistema, sem solicitar senha do contador. O destino fica registrado em cada
envio; tentar novamente uma falha usa o e-mail atual salvo na configuração.

## Arquivos e acompanhamento

- Envio individual: um XML por e-mail, para a nota autorizada ou o evento confirmado.
- Lote por e-mail: uma mensagem com ZIPs separados para **notas**, **cancelamentos**,
  **cartas de correção** e cada tipo dos **demais eventos**. Categorias vazias
  não geram anexos. Cada ZIP tem `manifesto.json` com empresa, período e documentos.
- Download manual: um ZIP principal contém os mesmos ZIPs por tipo, para baixar
  tudo de uma vez e manter a organização.
- Somente NF-e/NFC-e de saída em produção, emitidas pelo CNPJ da empresa.
  Notas de entrada e homologação são excluídas.
- Inclui notas autorizadas e canceladas, junto com cancelamentos, todas as
  sequências de cartas de correção e outros eventos oficiais retornados pelo
  emissor. A seleção reúne notas emitidas no período com seus eventos disponíveis,
  mais eventos registrados no período de notas emitidas anteriormente. Assim,
  um cancelamento de outubro de uma nota de setembro entra no lote de outubro.
- XML de nota ou evento esperado ausente/inválido bloqueia o lote: não se
  fabrica evento nem se apresenta pacote incompleto como sucesso.
- Os XMLs assinados são preservados byte a byte. Quando o provedor só retorna
  evento embutido na nota, o arquivo do evento contém o documento original
  completo, sem recortar ou regravar a assinatura; o manifesto explica isso.
- IntNFe: consulta a lista oficial de eventos mesmo quando o XML da nota já está
  salvo, incluindo cancelamento, substituição de NFC-e, CC-e e demais registros
  autorizados. Bling legado: a API pública atual não documenta listagem de todos
  os eventos/CC-e; são usados os comprovantes retornados ou embutidos no XML.
  Cancelamento conhecido sem comprovante bloqueia o pacote. Não há garantia de
  descobrir CC-e externas desconhecidas nesse legado.
- Limites por lote: 366 dias, 1.000 notas, 10 MB por XML, 30 MB de XMLs e 15 MB
  de ZIP. Use períodos menores quando ultrapassar os limites.
  A confirmação de eventos em notas antigas consulta o histórico fiscal;
  históricos acima de 10.000 documentos exigem suporte, sem truncar o lote.

No histórico, **Enviado** significa que o servidor SMTP aceitou a mensagem,
sem confirmação de leitura ou de entrega na caixa de entrada. Confira com o
contador e verifique spam. **Sem notas** finaliza o trabalho sem mandar um ZIP
vazio. Envios pendentes podem ser cancelados; falhas podem ser tentadas novamente.
Agendamentos de períodos livres da versão de teste anterior deixam de executar;
seu histórico é preservado e uma nova entrega deve ser feita manualmente.

## Operação e falhas

O scheduler roda a cada 30 segundos no processo líder do backend; não exige
navegador aberto. A fila está no PostgreSQL, com isolamento por empresa,
identificação de operações repetidas e claim persistido antes de acessar a rede.
O SMTP nunca roda dentro da emissão fiscal. Hooks registram notas/eventos na fila,
e a consulta periódica ao emissor também descobre eventos posteriores.
Notas novas são priorizadas; os demais documentos são consultados em rodízio,
até dez por ciclo, e voltam à consulta após dez minutos. O tempo para localizar
um evento externo depende do tamanho do histórico e da disponibilidade do emissor.
A competência mensal é sempre fechada; datas do período manual não alimentam
o agendamento.

São até três tentativas, com espera de 5 e 30 minutos após falhas. Falta de
SMTP é erro real, sem simulação de sucesso. Após interrupção de um processamento
por mais de 30 minutos, o histórico exige conferir com o contador antes de
repetir: uma queda depois da aceitação SMTP pode deixar o resultado incerto.

Os XMLs oficiais continuam nas fontes fiscais existentes. Os comprovantes de
eventos consultados ficam registrados por empresa para acompanhamento e
deduplicação. ZIPs/anexos são gerados em memória; a fila guarda metadados,
destinatário e resultado.
Ações manuais/configurações/exportações são registradas na auditoria existente.
Não registrar XML, certificado, credencial ou senha nos logs.

## Publicação e reversão

A migration aditiva `zzzzh20261019a1` cria `xml_contabilidade_config` e
`xml_contabilidade_envios`, ambas com RLS forçado. A revisão `zzzzi20261019a1`
desliga configurações da revisão intermediária e cancela seus trabalhos legados
pendentes por empresa, respeitando o RLS e preservando histórico. A revisão
`zzzzj20261019a1` adiciona acompanhamento de documentos e eventos e restaura a
opção individual, inicialmente desligada. Aplicar todas antes de iniciar
o backend atualizado pelo fluxo oficial. Todos os automatismos começam
desligados; a configuração por empresa deve ser conferida antes da ativação.

Reversão: desligar as rotinas e cancelar agendamentos, retornar imagens/código
anteriores e preservar as tabelas aditivas. O downgrade remove configurações e
histórico; só utilizá-lo depois de avaliar essa perda. Produção continua
dependendo da autorização explícita do Lucas.

Ajuda no ERP: `/ajuda?aba=central&artigo=xml-notas-contabilidade`.
