# Governança do contrato SaaS CorePet

Atualizado em: 2026-09-14

Status: regra operacional para preparar propostas e aceites. O texto contratual
deve passar por revisão jurídica brasileira antes de ser adotado como modelo
definitivo ou negociado com cliente de maior risco.

## Objetivo

Evitar que preço, escopo, suporte, migração, disponibilidade ou desenvolvimento
sob medida sejam prometidos fora do comprovante aceito pelo cliente.

## Ordem dos documentos

Em assunto específico, a ordem operacional é:

1. proposta ou resumo da contratação aceito;
2. Ordem de Serviço ou anexo específico assinado;
3. Contrato de Assinatura CorePet;
4. Termos de Uso;
5. Política de Privacidade, para transparência do tratamento de dados.

Mensagem, reunião, chamado ou WhatsApp inicia uma negociação, mas não altera o
contrato até que a condição seja registrada e aceita.

## Condições padrão protegidas pelo sistema

Toda nova proposta personalizada registra:

- escopo contratado;
- implantação e eventual migração;
- itens fora do escopo e dependências;
- canal oficial de suporte;
- existência ou ausência de desenvolvimento sob medida.

Na ausência de anexo específico, o padrão é:

- assinatura mensal sem fidelidade;
- cancelamento ao final do ciclo já pago;
- suporte em dias úteis, das 9h às 18h, horário de Brasília;
- metas de primeira resposta são operacionais, não prazo de resolução;
- não há SLA contratual nem crédito automático por indisponibilidade;
- exportação assistida pode ser solicitada por até 30 dias após o encerramento;
- código, arquitetura e componentes reutilizáveis permanecem do CorePet;
- exclusividade, cessão de direitos ou entrega de código-fonte não estão incluídas.

Proposta antiga sem essas condições não pode receber novo aceite. Deve ser
revogada e reemitida.

## Quando um SLA pode ser oferecido

Não oferecer percentual de disponibilidade até existirem:

- medição externa confiável e histórico suficiente;
- fórmula aprovada de disponibilidade;
- manutenção e exclusões definidas;
- RPO e RTO aprovados e restauração exercitada;
- consequência comercial e limite de créditos calculados;
- capacidade de suporte compatível com o horário prometido;
- revisão jurídica e aceite do responsável pelo negócio.

Até esse momento, usar somente a política de suporte e as metas internas do
piloto.

## Incidente de dados

O processo interno continua em `docs/GESTAO_INCIDENTES_SUSTENTACAO.md`. No
relacionamento com o cliente:

1. CorePet confirma fatos e preserva evidências mínimas;
2. cliente é avisado sem atraso indevido e, quando razoavelmente possível, em
   até um dia útil após a confirmação de impacto em seus dados;
3. controlador decide as comunicações legais e o CorePet coopera como operador;
4. nenhuma parte assume culpa antes de delimitar causa e participação;
5. custos e responsabilidade seguem a participação comprovada e a lei;
6. registro do incidente e decisões de comunicação são preservados pelo prazo
   aplicável.

## Desenvolvimento sob medida

Não iniciar personalização paga sem Ordem de Serviço contendo:

- problema e resultado esperado;
- entregáveis e itens excluídos;
- dependências do cliente;
- preço, prazo e forma de cobrança;
- critérios de aceite e prazo para validação;
- manutenção e correção após o aceite;
- titularidade, licença, reutilização, exclusividade e código-fonte;
- efeito de atraso ou mudança solicitada pelo cliente.

Se não houver cessão expressa, o CorePet mantém os direitos sobre o código e
concede o uso da funcionalidade enquanto a assinatura estiver vigente.

## Verificação antes de enviar a proposta

- conferir empresa, representante, plano, módulos, valor e vencimento;
- remover promessas vagas como “completo”, “sem falhas” ou “disponível sempre”;
- registrar migração e personalização como incluída ou excluída;
- confirmar canal de suporte que realmente será acompanhado;
- abrir o link público e revisar as condições como o cliente verá;
- não enviar o link se houver P0 aberto ou condição ainda não aprovada;
- guardar o aceite imutável e o resumo das condições específicas.

## Aprovações ainda necessárias

Antes de transformar este padrão em contrato definitivo, validar com advogado:

- teto de responsabilidade equivalente a 12 mensalidades e suas exceções;
- aplicação do CDC em cada perfil de contratante;
- propriedade de desenvolvimento encomendado;
- prazo contratual de aviso de incidente;
- exportação, retenção e eliminação no encerramento;
- foro e forma de solução de conflitos.

O limite contratual não substitui prevenção. Seguro de responsabilidade civil e
risco cibernético deve ser avaliado conforme número de clientes, dados tratados
e exposição financeira.
