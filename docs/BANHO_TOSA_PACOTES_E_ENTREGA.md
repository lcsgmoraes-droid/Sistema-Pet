# Banho e tosa: pacotes e entrega sem cobrança

## Regras da operação

- O catálogo define nome, preço, validade e quantidade de cada serviço incluído.
- Cada contratação nova pertence a um tutor e a um pet. A composição e o preço
  são copiados para a contratação; editar o catálogo não muda o combinado anterior.
- Ao agendar, o sistema reserva automaticamente os créditos daquele pet e serviço,
  priorizando a contratação que vence primeiro. A data do serviço precisa estar
  dentro do período contratado. Contratos antigos sem pet não entram nessa seleção.
- Exemplo: quatro banhos contratados, um agendado → três disponíveis, um reservado.
  No check-in, o reservado vira usado; a disponibilidade continua em três.
- Cancelar ou marcar ausência antes do atendimento devolve a reserva. Cancelar o
  processo depois do check-in estorna o uso, preservando o histórico. Repetir a
  operação não devolve nem consome créditos novamente.
- Serviços ou quantidades fora da cobertura e táxi dog continuam sendo cobrados
  separadamente. O atendimento não cobra novamente os serviços cobertos pelo pacote.
- Duas operações simultâneas não podem reservar o mesmo saldo: os contratos são
  bloqueados durante a transação.

## Validade e combinados

Vencer não apaga o saldo, a contratação ou suas movimentações. A contratação
expirada deixa de cobrir novos agendamentos; as reservas já existentes permanecem
registradas. A equipe pode prorrogar a validade com motivo, por exemplo, uma viagem
do tutor. Também pode encerrar manualmente o saldo não utilizado, com motivo e
histórico. É necessário resolver as reservas existentes antes desse encerramento.

O uso dos créditos e sua eventual prorrogação não renovam o pacote automaticamente.
Para um novo período, a equipe registra uma nova contratação.
A virada de validade segue a data de Brasília, mesmo quando o servidor usa UTC.

## Pagamento

A cobrança do pacote é uma venda própria no PDV. Criar ou usar a contratação não
registra recebimento: o estado pode ser sem cobrança, pendente, parcial, pago ou
com venda cancelada, conforme o financeiro existente.

É permitido iniciar os serviços com pagamento pendente. Isso não quita a dívida.
O recebimento continua no PDV e o saldo financeiro acompanha os pagamentos e
estornos. Cancelar um agendamento ou encerrar créditos não cancela a cobrança do
pacote. A geração repetida da cobrança recupera a mesma venda.

## Serviço zerado na fila

Quando realmente não houver valor cobrável, a ficha oferece entrega sem cobrança,
com justificativa e confirmação da entrega. O sistema registra uma ocorrência de
auditoria e conserva o atendimento, seus custos e histórico, sem inventar venda ou
pagamento. Se houver serviços ou táxi a cobrar, essa opção é rejeitada pelo backend.

Atendimentos que já tinham consumido pacote no fluxo antigo conservam a cobertura
integral anteriormente concedida. A atualização não gera cobrança retroativa nem
consome outro crédito ao repetir o check-in; a dívida do pacote permanece separada.

Para corrigir um atendimento criado indevidamente, a ficha também permite cancelar
o processo com motivo. A cobrança avulsa e a devolução dos créditos são tratadas
na mesma transação. O pacote contratado e sua cobrança continuam preservados.

A central de fechamentos consulta o histórico em lotes limitados. Quando ainda
houver registros anteriores para conferir, ela informa isso e oferece continuar
a busca; uma busca parcial não é apresentada como ausência de pendências.

## Validação e aplicação

Migração: `zzzzzd20261027a1`, após `zzzzzc20261027a1`. Acrescenta composição dos
serviços, snapshots da contratação e vínculos/reservas; conserva os registros antigos.

Os testes HTTP em `backend/tests/integration/test_banho_tosa_pacotes_http.py`
exercitam contratação, cobrança, agenda, check-in, cancelamento, expiração,
prorrogação, encerramento, extras e isolamento entre empresas. O teste de
concorrência PostgreSQL usa schema descartável e exige explicitamente
`BANHO_TOSA_TEST_POSTGRES_URL` de uma instância de testes.

Aplicação em produção segue o fluxo único do repositório e exige autorização
explícita do Lucas. Os dados locais de QA não fazem parte do deploy.
