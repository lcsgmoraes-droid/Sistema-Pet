# XML para contabilidade

Atualizado em: 2026-10-19.

Acesse **Configurações → XML para contabilidade**. Também há um atalho na
central de notas de saída. É necessário ter o módulo fiscal e a permissão
`configuracoes.editar` na empresa selecionada.

## Como usar

1. Confira o CNPJ da empresa e salve o e-mail do contador.
2. Para enviar individualmente, ative **Enviar um XML a cada emissão**. Somente
   novas emissões autorizadas entram na rotina; ativar não dispara o histórico.
3. Para obter um lote, escolha as datas em **XMLs por período** e clique em
   **Baixar ZIP** ou **Enviar agora**.
4. Para um envio avulso futuro, selecione o período, preencha a data e hora e
   clique em **Agendar envio do ZIP**.
5. Para repetir todo mês, ative **Enviar um ZIP todo mês**, escolha dia/hora e
   salve. O lote contém o mês anterior completo. Dias inexistentes, como 31 em
   fevereiro, são ajustados para o último dia do mês.

Datas são interpretadas em `America/Sao_Paulo`. As datas inicial e final do
período são inclusivas. O usuário pode combinar as rotinas automáticas ou
deixar ambas desligadas e usar apenas os lotes.

O download não exige e-mail configurado. Os envios usam o SMTP já existente no
sistema, sem solicitar senha do contador. O destino fica registrado em cada
envio; tentar novamente uma falha usa o e-mail atual salvo na configuração.

## Arquivos e acompanhamento

- Individual: anexo XML original, com eventos oficiais disponíveis.
- Lote: ZIP com XMLs originais e `manifesto.json`, identificando empresa, período,
  notas, situação e disponibilidade de eventos.
- Somente NF-e/NFC-e de saída em produção, emitidas pelo CNPJ da empresa.
  Notas de entrada e homologação são excluídas.
- Notas canceladas permanecem acompanhadas da situação. Se o emissor não
  disponibilizar o XML de cancelamento, o manifesto avisa; não se fabrica evento.
- Falha ou XML inválido bloqueia o lote, sem apresentar um ZIP parcial como completo.
- Limites por lote: 366 dias, 1.000 notas, 10 MB por XML, 30 MB de XMLs e 15 MB
  de ZIP. Use períodos menores quando ultrapassar os limites.

No histórico, **Enviado** significa que o servidor SMTP aceitou a mensagem,
sem confirmação de leitura ou de entrega na caixa de entrada. Confira com o
contador e verifique spam. **Sem notas** finaliza o trabalho sem mandar um ZIP
vazio. Envios pendentes/agendados podem ser cancelados; falhas podem ser
tentadas novamente. Desativar uma rotina cancela seus trabalhos ainda pendentes.

## Operação e falhas

O scheduler roda a cada 30 segundos no processo líder do backend; não exige
navegador aberto. A fila está no PostgreSQL, com isolamento por empresa,
identificação de operações repetidas e claim persistido antes de acessar a rede.
O SMTP nunca roda dentro da emissão fiscal.

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
`xml_contabilidade_envios`, ambas com RLS forçado. Aplicá-la antes de iniciar
o backend atualizado pelo fluxo oficial. Todos os automatismos começam
desligados; a configuração por empresa deve ser conferida antes da ativação.

Reversão: desligar as rotinas e cancelar agendamentos, retornar imagens/código
anteriores e preservar as tabelas aditivas. O downgrade remove configurações e
histórico; só utilizá-lo depois de avaliar essa perda. Produção continua
dependendo da autorização explícita do Lucas.

Ajuda no ERP: `/ajuda?aba=central&artigo=xml-notas-contabilidade`.
