# Padrão da Central de Ajuda e Novidades

Este documento transforma a documentação de uso em parte obrigatória das entregas do CorePet.

## Fontes de verdade

- Catálogo exibido no ERP e no app: `backend/app/evolucao_corepet.py`.
- Artigos da Central de Ajuda do ERP: `frontend/src/pages/centralAjuda/centralAjudaKnowledge.js`.
- Guias visuais editáveis e PDFs: pasta `Ajudas para configuração do Corepet` mantida pelo Lucas.

## Estados aceitos

`em_estudo -> planejado -> em_desenvolvimento -> disponivel_teste -> implantado -> oculto em Novidades`

No produto, eles são agrupados em Novidades, Em andamento e Em estudo. A palavra “Disponível” só pode ser usada quando o usuário já consegue utilizar a função.

- `disponivel_teste`: aparece em Novidades como **Disponível — em fase de teste**. A função já pode ser usada, mas fica em acompanhamento.
- `implantado`: atingiu o tempo e a quantidade de usos configurados. Continua visível em Novidades pelo período definido para divulgação.
- oculto em Novidades: depois do período de divulgação, sai automaticamente do catálogo exibido. A funcionalidade e seu artigo de ajuda não são removidos.

O ciclo padrão é de 14 dias e 10 usos concluídos, exigindo os dois critérios. Depois da implantação, o item continua visível por 30 dias. Cada item pode ter limites próprios no campo `ciclo_novidade`.

Os usos são contados de forma global e anônima em `evolucao_funcionalidade_usos`. A tabela guarda somente o identificador da funcionalidade, a quantidade e as datas dos marcos; não guarda cliente, usuário ou empresa.

## Regra de entrega

Toda tela ou funcionalidade nova voltada ao usuário deve incluir:

1. item atualizado no catálogo de evolução;
2. público e plataformas afetadas;
3. artigo ou guia de ajuda;
4. link “Ver como usar” quando o status passar para `disponivel_teste`;
5. data de publicação e data da última atualização.

O catálogo é validado por `backend/tests/unit/test_evolucao_corepet.py`. Um item disponível sem data de publicação, caminho de ajuda ou ciclo válido deve falhar na validação.
O mesmo teste também confere se cada link do catálogo aponta para um artigo realmente existente na Central de Ajuda.

## Padrão dos guias

Os guias completos devem conter objetivo, público, pré-requisitos, caminho da tela, passos, exemplos, alertas, teste, checklist e dúvidas comuns. Guias curtos de integrações podem usar apresentação horizontal; configurações longas devem usar A4 vertical.

Capturas de tela nunca devem expor dados reais de clientes ou informações sigilosas.

## Central disponível

Desde 22/08/2026, a Central de Ajuda do ERP está disponível em fase de teste em **Ajuda e Planos → Central de Ajuda**. Ela possui busca por conteúdo, filtros por módulo e abertura direta do artigo a partir de **Novidades → Ver como usar**.

Como a leitura dos artigos não registra cliente, empresa nem usuário, o item `expansao-central-ajuda` usa somente o período mínimo de 14 dias para passar automaticamente de **Disponível — em fase de teste** para **Implantado**. Depois disso, permanece em Novidades por mais 30 dias e sai apenas da divulgação; os artigos continuam disponíveis.

## Decisões encerradas

Projetos descartados não permanecem no catálogo de Novidades, para não sugerir ao usuário que ainda serão desenvolvidos.

- Em 22/08/2026, foi encerrada a ideia de tratar medicamentos fracionados como granel. Para caixas com venda unitária, o padrão do CorePet continua sendo **produto com composição**, funcionalidade que já existe.
