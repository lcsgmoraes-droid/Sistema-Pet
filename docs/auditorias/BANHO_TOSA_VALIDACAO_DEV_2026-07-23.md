# Validação do módulo Banho & Tosa - DEV - 2026-07-23

## Objetivo

Validar o módulo completo no tenant local de demonstração, identificar os
gargalos do fluxo operacional e melhorar a passagem entre agenda, execução,
fechamento, PDV e relatórios.

Esta rodada ocorreu somente no ambiente DEV/local. Nenhuma mudança foi
implantada em produção.

## Diagnóstico inicial

O backend já possuía rotas para timers, responsáveis, recursos, insumos,
ocorrências, fotos, custos e fechamento. A fila antiga não usava essas rotas:

- toda mudança de etapa enviava `iniciar_timer: false`;
- não havia ficha operacional acessível para o atendimento;
- a rota de fechamentos apenas redirecionava para a fila;
- a entrega gerava venda, mas a interface ignorava o retorno e o link do PDV;
- snapshots de custo não eram garantidos no fluxo normal;
- o relatório não exportava PDF ou CSV;
- no celular, o quadro exigia uma largura mínima de 980 px;
- a soma dos preços de tabela dos pacotes era chamada de "Receita cadastrada".

## Melhorias implementadas

### Fila e etapas

- avanço de etapa passou a abrir uma confirmação operacional;
- banho, secagem, tosa, higiene e preparo iniciam timer;
- responsável, recurso e observação podem ser informados antes de iniciar;
- o card mostra tempo, previsão, atraso, responsável e recurso;
- a ação "Abrir ficha" ficou disponível em cada atendimento;
- "Fechar e entregar" leva diretamente ao fechamento guiado;
- no celular, a fila usa seletores de etapa e exibe uma coluna por vez.

### Ficha operacional

A ficha reúne:

- resumo e linha do tempo;
- consumo e desperdício de insumos;
- responsável pelo consumo e baixa opcional de estoque;
- ocorrências com tipo, gravidade e responsável;
- fotos de entrada, durante e saída;
- custo, margem e percentual;
- venda, pagamento, pacote e entrega;
- observações de saída.

### Fechamento

- foi criada uma tela real em `/banho-tosa/fechamentos`;
- a venda pode ser gerada antes da entrega;
- o PDV abre diretamente na venda vinculada;
- o estado do pagamento pode ser sincronizado;
- a entrega exige confirmação explícita;
- observações de saída são persistidas;
- o snapshot de custo é atualizado ao chegar em `pronto` ou `entregue`.

### Relatórios e arquivos

- relatórios históricos sem snapshot persistido recebem cálculo em memória;
- novos atendimentos persistem o snapshot no fechamento;
- foram adicionadas exportações CSV e PDF;
- o PDF possui resumo, margem, produtividade, desperdício e alertas;
- textos longos do PDF quebram linha sem invadir a coluna de valores.

### Clareza e segurança operacional

- o painel passou a explicar cada etapa real do fluxo configurado;
- cancelamento de agenda recebeu confirmação;
- "Receita cadastrada" foi corrigido para "Valor de tabela".

## Fluxo validado no tenant DEV

Registro usado:

- tutor: Ana Costa;
- pet: Thor;
- serviço: Banho Completo;
- valor: R$ 120,00;
- atendimento: `#1`;
- venda: `#202607230001`.

| Etapa | Resultado |
|---|---|
| Aplicar base padrão | 5 portes, 8 serviços, 5 recursos e 2 templates criados |
| Agendar | horário, tutor, pet, recurso, serviço e valor salvos |
| Check-in | atendimento criado na coluna Chegou |
| Banho | timer, Beatriz Vendedora Demo e Banheira 1 salvos |
| Secagem | timer e Secador / Soprador 1 salvos |
| Tosa | timer e Mesa de Tosa 1 salvos |
| Consumo | usado 0,050, desperdício 0,010 e custo R$ 1,44 |
| Ocorrência | comportamento de baixa gravidade salvo |
| Foto | upload PNG, thumbnail e listagem validados |
| Pronto | etapas fechadas e custo disponível |
| Venda | item, pet, tutor, valor e vínculo do atendimento corretos no PDV |
| Recebimento | R$ 120,00 em dinheiro e venda finalizada |
| Entrega | observação de saída salva e atendimento encerrado |
| Fechamento | vínculo financeiro sincronizado e pendência zerada |
| Relatório | receita R$ 120,00, custo R$ 18,07 e margem R$ 101,93 |
| CSV | arquivo gerado com 669 bytes |
| PDF | arquivo A4 gerado, renderizado e inspecionado visualmente |

O snapshot final persistido apresentou:

- valor cobrado: R$ 120,00;
- custo total: R$ 18,07;
- margem: R$ 101,93;
- margem percentual: 84,9%;
- três etapas finalizadas com responsável e recurso;
- venda paga e observação de saída salva.

## Validações técnicas

- build de produção do frontend: aprovado;
- ESLint dos arquivos alterados: aprovado;
- contrato frontend do fluxo: aprovado;
- testes unitários de Banho & Tosa: `25 passed`;
- console do Chrome: sem erros e sem avisos funcionais;
- PDF renderizado com Poppler e revisado visualmente;
- `git diff --check`: deve permanecer limpo no fechamento da branch.

## Pendências que continuam fora desta entrega

As áreas abaixo existem, mas ainda merecem uma rodada própria de produto:

- motivo estruturado de cancelamento de agenda;
- envio automático de mensagem de "pet pronto" e solicitação de NPS;
- comprovante específico do Banho & Tosa, além do cupom do PDV;
- indicadores de SLA por etapa com filtros históricos;
- fluxo completo do Taxi Dog com mapas/roteirização quando as chaves externas
  estiverem configuradas;
- regras de permissão mais granulares para excluir ocorrências, fotos e
  estornar insumos.
