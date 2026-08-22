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

## Padrão dos guias

Os guias completos devem conter objetivo, público, pré-requisitos, caminho da tela, passos, exemplos, alertas, teste, checklist e dúvidas comuns. Guias curtos de integrações podem usar apresentação horizontal; configurações longas devem usar A4 vertical.

Capturas de tela nunca devem expor dados reais de clientes ou informações sigilosas.
