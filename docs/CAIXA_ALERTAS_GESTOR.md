# Conferência de caixa e alertas do gestor

A tela **Gestão → Alertas do gestor** (`/alertas-gestor`) reúne vendas finalizadas
ou parcialmente pagas com justificativa de margem, diferenças registradas entre
fechamento e abertura e sobras/faltas registradas no fechamento. Permite filtrar
por período (até 93 dias), tipo e operador, com paginação. O operador do fechamento
é quem o executou, mesmo quando outra pessoa abriu o caixa compartilhado.

O acesso exige `relatorios.gerencial` no frontend e no backend. Todas as consultas
são limitadas à empresa selecionada. Esta primeira versão é uma consulta para
conferência; não aprova justificativas nem altera os valores financeiros.

## Referência do fechamento

`data_fechamento`, um campo legado sem fuso, recebeu tanto horários locais como
UTC em encerramentos operacionais. Ordenar diretamente por esse campo podia
selecionar um caixa antigo. Exemplo reproduzido: um encerramento às 19h59 UTC
(16h59 em Brasília) aparecia depois de um fechamento às 17h58 de Brasília.

Os novos fechamentos gravam também `fechamento_em`, com fuso. A ordenação usa
esse instante e, nos registros antigos, `updated_at` (horário com fuso da gravação
do fechamento). O campo antigo não é reescrito. Não editar caixas fechados
legados por SQL sem considerar que `updated_at` ainda serve como referência.

Ao abrir, `conferencia_abertura` preserva caixa anterior, valor contado,
responsável, instante, abertura e diferença. Reabrir o caixa anterior não apaga
esse registro da abertura seguinte. O formulário mostra a referência consultada
e o servidor retorna 409 se ela tiver mudado antes de confirmar a abertura.

## Registros históricos

As aberturas antigas continuam mostrando a comparação gravada na observação,
com identificação de **comparação histórica**. Não se recalculam vínculos usando
a configuração atual de caixa compartilhado: ela pode ser diferente da vigente
na época. Uma referência incorreta antiga deve ser revisada como ocorrência
histórica, sem presumir falta de dinheiro do operador.

Sobras/faltas históricas mostram o saldo esperado gravado no fechamento. Os
novos resumos e fechamentos usam o mesmo cálculo do dinheiro físico: entradas e
suprimentos menos sangrias, despesas, transferências e devoluções em dinheiro.
PIX e cartão não entram na contagem física. Valores são comparados em centavos.

## Validação e entrega

- Testes de regressão em `backend/tests/unit/test_alertas_gestor_caixa.py` cobrem
  horários mistos, isolamento entre empresas, operadores, permissão, filtros,
  paginação, referência alterada e a sequência resumo → fechamento → abertura.
- Migration `zzi20260905a1` adiciona dois campos opcionais, sem alterar registros
  históricos; deve entrar antes de servir o backend atualizado.
- Aplicação em produção segue o fluxo oficial e depende da autorização do Lucas.
