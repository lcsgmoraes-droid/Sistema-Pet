# Pacote comercial do piloto - Plano Basico

Atualizado em: 2026-07-13

Uso: fonte unica para proposta, aceite, suporte e acompanhamento dos primeiros
clientes pagantes. Este documento e um modelo operacional; a versao entregue ao
cliente deve ter valor, datas e dados das partes preenchidos e revisao juridica
antes de ser usada como contrato definitivo.

## 1. Oferta

O Plano Basico organiza a operacao principal de um pet shop:

- cadastro de clientes e pets;
- cadastro de produtos, categorias, marcas e departamentos;
- estoque inicial, entradas e ajustes simples;
- vendas no PDV, formas de pagamento e baixa de estoque;
- historico e relatorios gerenciais basicos de vendas;
- usuarios e permissoes essenciais.

O piloto e acompanhado e limitado inicialmente a 2 a 5 empresas. Nao e uma
oferta de autoatendimento em escala.

## 2. Fora do escopo

Nao fazem parte da promessa do Plano Basico:

- financeiro ERP completo, DRE oficial, contas a pagar/receber ou conciliacao;
- fiscal, NF-e ou substituicao de sistema contabil;
- veterinario, banho e tosa, e-commerce, aplicativo mobile ou marketplaces;
- Stone, WhatsApp, Bling, automacoes e IA avancada;
- cobranca automatica da assinatura do Sistema Pet;
- migracao integral de dados legados ou integracoes sob medida.

Qualquer adicional precisa de proposta separada e liberacao tecnica explicita.

## 3. Condicao comercial a preencher

Preencher antes do aceite, sem deixar combinados apenas em conversa:

| Campo | Condicao acordada |
| --- | --- |
| Cliente e CNPJ/CPF | [preencher] |
| Valor mensal | R$ [preencher] |
| Implantacao | [inclusa / valor / nao aplicavel] |
| Primeiro vencimento | [preencher] |
| Forma de cobranca durante o piloto | [preencher] |
| Inicio e duracao inicial | [preencher] |
| Usuarios incluidos | [preencher] |
| Canal oficial de suporte | [preencher] |
| Responsavel do cliente | [preencher] |

Como a cobranca automatica da assinatura esta em standby, o meio manual acordado
deve ser registrado nesta tabela e conferido pelo responsavel comercial.

## 4. Implantacao e aceite

A implantacao segue `docs/implantacao/CHECKLIST_PLANO_BASICO_PILOTO.md` e termina
quando cliente e responsavel pela implantacao registrarem:

- acesso do usuario principal confirmado;
- configuracao minima da empresa concluida;
- produtos e estoque inicial suficientes para iniciar a operacao;
- uma venda teste concluida com baixa de estoque correta;
- escopo e itens fora do escopo compreendidos;
- canal de suporte testado.

Pendencias nao bloqueantes devem ficar registradas com responsavel e data. Senhas,
tokens e dados pessoais desnecessarios nunca devem entrar na evidencia.

## 5. Politica de suporte do piloto

O suporte cobre duvidas de uso, falhas do escopo contratado e orientacao de
implantacao. Solicitacoes de novos modulos ou personalizacoes entram como melhoria
ou proposta separada.

Horario padrao: dias uteis, das 9h as 18h, horario de Brasilia. O canal oficial e
o preenchido na proposta. Contatos por outros canais devem ser consolidados nele.

| Nivel | Exemplo | Primeira resposta alvo | Tratamento |
| --- | --- | --- | --- |
| P0 critico | sistema indisponivel ou risco de acesso entre empresas | ate 2 horas corridas | triagem imediata e atualizacoes durante o incidente |
| P1 alto | venda/estoque bloqueado sem alternativa segura | ate 4 horas uteis | priorizar correcao ou alternativa operacional |
| P2 normal | erro pontual com alternativa, duvida de uso | ate 1 dia util | orientar ou planejar correcao |
| Melhoria | nova funcao ou ajuste de preferencia | ate 2 dias uteis | registrar para avaliacao, sem prazo automatico de entrega |

Esses tempos sao metas operacionais do piloto, nao garantia de resolucao nem SLA
contratual de disponibilidade. Um SLA comercial so deve ser prometido apos medicao
real dos pilotos e revisao juridica.

## 6. Resposta a incidente

1. Registrar horario, cliente, impacto e `request_id`, quando existir.
2. Classificar P0, P1, P2 ou melhoria.
3. Consultar `/ops` sem copiar dados sensiveis para mensagens.
4. Conter o impacto e informar uma alternativa segura, quando houver.
5. Corrigir pelo fluxo Git e deploy protegido; nunca aplicar correcao sem registro.
6. Validar saude e jornada afetada depois da correcao.
7. Para P0, enviar resumo do ocorrido, impacto, correcao e prevencao.

P0 aberto impede a entrada de um novo piloto ate a estabilizacao.

## 7. Dados, privacidade e encerramento

- cada empresa acessa somente seus dados, conforme o contrato multiempresa;
- o cliente e responsavel pela legitimidade dos dados cadastrados e pelos acessos
  concedidos aos seus usuarios;
- o Sistema Pet deve proteger credenciais, registrar eventos operacionais e seguir
  o processo de incidente;
- solicitacoes de exportacao, correcao ou exclusao devem ser identificadas,
  registradas e avaliadas conforme LGPD e obrigacoes legais de retencao;
- prazo, formato de exportacao e eliminacao no encerramento devem constar da versao
  contratual revisada juridicamente.

## 8. Acompanhamento de 7 dias

Registrar no dia 1, dia 3 e dia 7:

- login e primeira venda real;
- erros P0/P1/P2 e tempo da primeira resposta;
- duvidas recorrentes;
- uso de cadastro, estoque e PDV;
- satisfacao simples de 0 a 10;
- decisao: continuar, corrigir antes de ampliar ou encerrar o piloto.

## 9. Go/No-Go para assinar

Go somente quando:

- cliente se encaixa no perfil do Plano Basico;
- producao e gate de release estao saudaveis;
- valor, datas, cobranca manual e canal de suporte foram preenchidos;
- cliente recebeu escopo e exclusoes por escrito;
- existe agenda para implantacao acompanhada.

No-Go quando houver P0 aberto, dependencia de item fora do escopo ou expectativa
de SLA/funcionalidade que nao esteja escrita na proposta.

## 10. FAQ para venda sem promessa excessiva

**O sistema tem financeiro completo?**  Nao no Plano Basico. Ele registra a
operacao ligada as vendas, mas nao deve substituir o ERP financeiro ou contabil.

**Emite nota fiscal?**  Fiscal e NF-e estao fora desta oferta inicial.

**Tem veterinario ou banho e tosa?**  Existem frentes em evolucao, mas elas nao
fazem parte da promessa nem do preco do Plano Basico piloto.

**Tem WhatsApp, Stone ou cobranca automatica da assinatura?**  Nao nesta etapa.
Esses itens estao em standby e nao podem ser condicao para iniciar o piloto.

**Posso importar todo o sistema antigo?**  A implantacao basica combina a carga
minima necessaria. Migracao ampla precisa ser avaliada e proposta separadamente.

**Existe garantia de disponibilidade?**  O piloto tem acompanhamento e metas de
resposta, mas ainda nao oferece SLA contratual de disponibilidade.

**O que acontece se eu quiser sair?**  O processo de exportacao e encerramento
deve estar definido na versao contratual revisada juridicamente.

## 11. Aceite do piloto

Ao aceitar a proposta, as partes confirmam que leram escopo, exclusoes, condicao
comercial, suporte e criterios de implantacao. Registrar nome, data e meio de
aceite rastreavel. Para uso como contrato definitivo, submeter esta base a revisao
juridica e incorporar termos de privacidade, encerramento e responsabilidade
adequados ao negocio.
