# XML para contabilidade

Atualizado em: 2026-10-19.

Acesse **Configurações → XML para contabilidade**. Também há um atalho na
central de notas de saída. É necessário ter o módulo fiscal e a permissão
`configuracoes.editar` na empresa selecionada.

## Como usar

1. Confira o CNPJ da empresa e salve o e-mail do contador.
2. Para automatizar, ative **Enviar automaticamente o mês anterior completo**,
   escolha dia e hora e salve. Todo envio reúne do primeiro ao último dia do mês
   anterior à data programada, no horário de Brasília.
3. Para um período diferente, escolha as datas em **Envio manual por período** e clique em
   **Baixar ZIP** ou **Enviar agora**.
4. Acompanhe o resultado no histórico. Desligar a rotina mensal preserva o
   histórico e cancela os envios mensais ainda pendentes.

Exemplo: no dia 1º de março, o lote contém fevereiro inteiro, até 28 ou 29.
No dia 1º de maio, contém abril até o dia 30; no dia 1º de agosto, julho até
o dia 31. Janeiro envia dezembro do ano anterior. O período não é uma janela
móvel de 30 dias. Se o dia escolhido para executar não existir no mês, a execução
ocorre no último dia desse mês, mantendo a competência anterior completa.

Datas são interpretadas em `America/Sao_Paulo`. As datas inicial e final do
período são inclusivas. Períodos livres são exclusivamente manuais: não há
envio por emissão nem agendamento avulso de um intervalo personalizado.
O usuário pode deixar a rotina mensal desligada e usar apenas os lotes manuais.

O download não exige e-mail configurado. Os envios usam o SMTP já existente no
sistema, sem solicitar senha do contador. O destino fica registrado em cada
envio; tentar novamente uma falha usa o e-mail atual salvo na configuração.

## Arquivos e acompanhamento

- Lote: ZIP com XMLs originais e eventos oficiais, mais `manifesto.json`, identificando empresa, período,
  notas, situação e disponibilidade de eventos.
- Somente NF-e/NFC-e de saída em produção, emitidas pelo CNPJ da empresa.
  Notas de entrada e homologação são excluídas.
- Inclui notas autorizadas e canceladas, junto com cancelamentos, todas as
  sequências de cartas de correção e outros eventos oficiais retornados pelo
  emissor. A seleção do período é pela emissão da nota, e inclui seus eventos
  existentes no momento da coleta; não é uma varredura de eventos de notas
  emitidas em todos os meses anteriores.
- XML de nota ou evento esperado ausente/inválido bloqueia o lote: não se
  fabrica evento nem se apresenta pacote incompleto como sucesso.
- Os XMLs assinados são preservados byte a byte, inclusive eventos já embutidos.
- IntNFe: consulta a lista oficial de eventos mesmo quando o XML da nota já está
  salvo, incluindo cancelamento, substituição de NFC-e, CC-e e demais registros
  autorizados. Bling legado: a API pública atual não documenta listagem de todos
  os eventos/CC-e; são usados os comprovantes retornados ou embutidos no XML.
  Cancelamento conhecido sem comprovante bloqueia o pacote. Não há garantia de
  descobrir CC-e externas desconhecidas nesse legado.
- Limites por lote: 366 dias, 1.000 notas, 10 MB por XML, 30 MB de XMLs e 15 MB
  de ZIP. Use períodos menores quando ultrapassar os limites.

No histórico, **Enviado** significa que o servidor SMTP aceitou a mensagem,
sem confirmação de leitura ou de entrega na caixa de entrada. Confira com o
contador e verifique spam. **Sem notas** finaliza o trabalho sem mandar um ZIP
vazio. Envios pendentes/agendados podem ser cancelados; falhas podem ser
tentadas novamente. Os envios individuais e agendamentos livres da versão de
teste anterior deixam de executar; o histórico antigo é preservado e uma nova
entrega deve ser feita manualmente por período.

## Operação e falhas

O scheduler roda a cada 30 segundos no processo líder do backend; não exige
navegador aberto. A fila está no PostgreSQL, com isolamento por empresa,
identificação de operações repetidas e claim persistido antes de acessar a rede.
O SMTP nunca roda dentro da emissão fiscal. O único trabalho automático é a
competência mensal fechada; datas do período manual não alimentam o agendamento.

São até três tentativas, com espera de 5 e 30 minutos após falhas. Falta de
SMTP é erro real, sem simulação de sucesso. Após interrupção de um processamento
por mais de 30 minutos, o histórico exige conferir com o contador antes de
repetir: uma queda depois da aceitação SMTP pode deixar o resultado incerto.

Os XMLs oficiais continuam nas fontes fiscais existentes. ZIPs e anexos são
gerados em memória; a nova fila guarda metadados, destinatário e resultado.
Ações manuais/configurações/exportações são registradas na auditoria existente.
Não registrar XML, certificado, credencial ou senha nos logs.

## Publicação e reversão

A migration aditiva `zzzzh20261019a1` cria `xml_contabilidade_config` e
`xml_contabilidade_envios`, ambas com RLS forçado. A revisão `zzzzi20261019a1`
desliga o envio individual e cancela trabalhos legados pendentes por empresa,
respeitando o RLS e preservando histórico. Aplicá-las antes de iniciar
o backend atualizado pelo fluxo oficial. Todos os automatismos começam
desligados; a configuração por empresa deve ser conferida antes da ativação.

Reversão: desligar as rotinas e cancelar agendamentos, retornar imagens/código
anteriores e preservar as tabelas aditivas. O downgrade remove configurações e
histórico; só utilizá-lo depois de avaliar essa perda. Produção continua
dependendo da autorização explícita do Lucas.

Ajuda no ERP: `/ajuda?aba=central&artigo=xml-notas-contabilidade`.
