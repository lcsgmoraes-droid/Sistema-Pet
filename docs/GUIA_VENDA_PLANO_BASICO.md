# Guia de Venda e Implantacao do Plano Basico

Atualizado em: 2026-07-13

Este e o guia central para organizar a venda controlada do Plano Basico do
Sistema Pet. Use este arquivo para decidir a proxima acao, registrar progresso e
evitar vender algo fora do escopo validado.

## Decisao atual

O Plano Basico pode ser vendido em formato de piloto pago/controlado.

Ainda nao tratar como autoatendimento aberto em escala. Os primeiros clientes
devem entrar com implantacao acompanhada, validacao real de e-mail e suporte
proximo.

## Resumo executivo

| Frente | Status | O que significa |
|---|---|---|
| Produto Plano Basico | Pronto para venda controlada | Escopo basico validado para cadastro, estoque e PDV/vendas. |
| Producao | Pronta para uso acompanhado | Health, deploy seguro, CI e alertas operacionais estao em 10/10. |
| E-mail transacional | Parcial para escala | Yahoo e alerta Ops validados; Outlook ainda precisa reteste real de cadastro. |
| Material comercial | Formalizado para piloto | Oferta, exclusoes, campos comerciais, demo e mensagem base estao documentados. |
| Onboarding de cliente | Pronto para executar | Checklist exclusivo do Plano Basico criado; falta usa-lo com cliente real. |
| Suporte inicial | Formalizado para piloto | Horario, severidade, metas de resposta e processo de incidente definidos. |

Fontes oficiais desta etapa:

- `docs/comercial/PACOTE_PILOTO_PLANO_BASICO.md`;
- `docs/implantacao/CHECKLIST_PLANO_BASICO_PILOTO.md`.

Valor, meio de cobranca manual e canal oficial continuam sendo preenchidos por
cliente na proposta. Isso evita prometer uma condicao que ainda nao foi decidida.

## Regra de ouro

Venda o que esta pronto, com nome claro e limite claro.

Promessa comercial:

> Sistema de gestao para pet shop com cadastro de clientes e pets, produtos,
> estoque, PDV/vendas e visao gerencial basica de vendas.

Nao prometer no Plano Basico inicial:

- financeiro completo, DRE, contas a pagar/receber ou conciliacao;
- compras/XML como parte obrigatoria do plano;
- veterinario completo;
- banho e tosa completo;
- campanhas, WhatsApp, IA avancada, e-commerce, app mobile, entregas,
  marketplaces ou fiscal/NF.

## Cliente ideal para os primeiros pilotos

Aceitar primeiro:

- pet shop simples;
- venda produto no balcao;
- precisa de cadastro de clientes, pets, produtos, estoque e venda;
- aceita implantacao acompanhada;
- nao depende de financeiro ERP completo no primeiro dia;
- nao exige fiscal/NF, veterinario ou banho e tosa como criterio de compra.

Evitar por enquanto:

- cliente que quer trocar um ERP financeiro completo de imediato;
- cliente que depende de NF/fiscal como rotina principal;
- clinica veterinaria complexa;
- banho e tosa com agenda, pacotes, recorrencia e comissao como centro do uso;
- cliente que exige automacoes de WhatsApp ou e-commerce como parte do basico.

## Fases de trabalho

### Fase 1: Preparar venda piloto

Objetivo: deixar Lucas com material e decisao comercial suficientes para vender
sem improviso.

- [ ] Definir preco mensal do Plano Basico.
- [ ] Definir se havera 30 dias gratis, implantacao paga ou ambos.
- [x] Definir politica de suporte; o canal oficial e preenchido por cliente.
- [x] Criar modelo de proposta comercial curta.
- [x] Criar mensagem pronta para prospect (o canal efetivo e definido por cliente).
- [x] Criar roteiro de demo de 15 minutos.
- [x] Criar FAQ de objecoes comuns no pacote comercial e neste guia.
- [x] Definir aceite explicito do que nao esta incluido.

Resultado esperado: Lucas consegue apresentar e vender o Plano Basico sem
prometer modulos beta.

### Fase 2: Validar e-mail e cadastro real

Objetivo: garantir que um novo cliente consiga confirmar conta sem atrito
critico.

- [ ] Criar usuario de teste com e-mail Outlook externo/controlado.
- [ ] Confirmar recebimento do e-mail de ativacao no Outlook.
- [ ] Confirmar que o link ativa a conta corretamente.
- [ ] Registrar resultado neste guia.
- [ ] Se falhar, abrir tarefa tecnica antes de vender para mais clientes.

Resultado esperado: cadastro real validado pelo menos em Gmail/Yahoo e Outlook.

### Fase 3: Vender para 2 a 5 pilotos

Objetivo: validar produto, suporte e onboarding com clientes reais sem abrir
escala ampla.

- [ ] Selecionar ate 5 clientes com perfil ideal.
- [ ] Registrar cada cliente na tabela "Clientes piloto".
- [ ] Fazer demo guiada.
- [ ] Confirmar escopo e limites por escrito.
- [ ] Fechar valor/condicao.
- [ ] Agendar implantacao.

Resultado esperado: primeiros clientes entram com expectativa correta.

### Fase 4: Implantar cada cliente

Objetivo: colocar o cliente usando o sistema com uma primeira venda validada.

Checklist oficial: `docs/implantacao/CHECKLIST_PLANO_BASICO_PILOTO.md`.

Resumo da implantacao:

- [ ] Criar empresa/tenant.
- [ ] Confirmar e-mail do usuario principal.
- [ ] Conferir plano `basico`.
- [ ] Configurar dados da empresa.
- [ ] Criar ou revisar usuarios.
- [ ] Revisar permissoes basicas.
- [ ] Cadastrar formas de pagamento.
- [ ] Cadastrar operadoras de cartao, se necessario.
- [ ] Cadastrar categorias/marcas/departamentos iniciais.
- [ ] Cadastrar produtos principais.
- [ ] Registrar entrada/ajuste inicial de estoque.
- [ ] Cadastrar cliente real ou cliente de teste.
- [ ] Cadastrar pet, se fizer sentido para o fluxo do cliente.
- [ ] Fazer venda teste no PDV.
- [ ] Conferir baixa de estoque.
- [ ] Conferir historico de venda.
- [ ] Conferir que modulos premium aparecem bloqueados ou como upsell.
- [ ] Registrar evidencia do onboarding.

Resultado esperado: cliente consegue operar cadastro, estoque e venda.

### Fase 5: Acompanhar os primeiros 7 dias

Objetivo: descobrir problemas reais cedo, antes de escalar.

- [ ] Confirmar login no primeiro dia.
- [ ] Confirmar primeira venda real.
- [ ] Conferir se houve erro 500, alerta Ops ou reclamacao critica.
- [ ] Revisar duvidas do cliente.
- [ ] Classificar cada problema como P0, P1, P2 ou melhoria.
- [ ] Corrigir P0/P1 antes de aceitar muitos clientes novos.
- [ ] Registrar aprendizados neste guia.

Resultado esperado: produto validado em uso real acompanhado.

### Fase 6: Liberar escala controlada

Objetivo: sair do piloto e vender com mais repeticao.

Requisitos para sair do piloto:

- [ ] Pelo menos 2 clientes usando o Plano Basico por 7 dias sem bloqueador P0.
- [ ] Outlook de confirmacao validado em cadastro real.
- [ ] Proposta comercial e FAQ prontos.
- [ ] Checklist de onboarding usado pelo menos 2 vezes.
- [ ] Suporte inicial definido e funcionando.
- [ ] Nenhuma promessa comercial depende de modulo beta.

Resultado esperado: vender com rotina repetivel, nao caso a caso.

## Go/No-Go antes de vender para um cliente

Go:

- [ ] Cliente se encaixa no perfil ideal.
- [ ] Cliente aceita escopo do Plano Basico.
- [ ] Cliente nao exige modulo beta como requisito.
- [ ] Producao esta saudavel.
- [ ] Ha agenda para onboarding acompanhado.
- [ ] Lucas sabe qual sera o canal de suporte.

No-Go:

- [ ] Cliente precisa de financeiro completo como condicao principal.
- [ ] Cliente exige fiscal/NF agora.
- [ ] Cliente quer veterinario ou banho e tosa completo como escopo contratado.
- [ ] Cliente nao aceita implantacao acompanhada.
- [ ] Ha incidente P0 aberto em producao.

## Roteiro de demo de 15 minutos

1. Apresentar a promessa em uma frase.
2. Mostrar cadastro de clientes e pets.
3. Mostrar cadastro/listagem de produtos.
4. Mostrar estoque ou ajuste simples.
5. Fazer uma venda no PDV.
6. Mostrar baixa de estoque e historico de venda.
7. Mostrar tela do plano e explicar que modulos avancados sao beta/adicionais.
8. Combinar proximos passos: cadastro, implantacao e suporte.

Mensagem central da demo:

> O Plano Basico resolve o dia a dia principal do pet shop: organizar cadastro,
> produto, estoque e venda. O restante entra por etapas, sem prometer como
> pronto aquilo que ainda esta em validacao.

## Mensagem base para prospect

```text
Oi, tudo bem?

Estou iniciando os primeiros pilotos do Sistema Pet, um sistema de gestao para
pet shop focado em cadastro de clientes e pets, produtos, estoque e vendas/PDV.

Neste primeiro momento estou liberando o Plano Basico com implantacao
acompanhada, para poucos clientes, justamente para garantir que a entrada seja
bem assistida.

Ele e indicado para pet shops que querem organizar produtos, estoque e vendas do
dia a dia. Modulos como financeiro completo, fiscal, veterinario, banho e tosa,
WhatsApp e e-commerce entram depois como etapas separadas.

Se fizer sentido, posso te mostrar uma demonstracao rapida de 15 minutos e ver
se o seu caso encaixa bem nesse primeiro grupo.
```

## Clientes piloto

Atualizar uma linha por cliente. Nao registrar senha, token, documento sensivel
ou dado privado desnecessario.

| Cliente | Contato | Perfil | Status | Data | Proxima acao | Observacoes |
|---|---|---|---|---|---|---|
| Exemplo Pet | WhatsApp/e-mail | Pet shop simples | Prospect | 2026-05-17 | Fazer demo | Linha exemplo; substituir quando houver cliente real. |

Status sugeridos:

- Prospect
- Demo agendada
- Demo feita
- Fechado
- Onboarding agendado
- Onboarding em andamento
- Ativo acompanhado
- Ativo estavel
- Nao aderente

## Evidencias de venda/onboarding

Registrar apenas evidencia operacional segura.

| Data | Cliente | Evento | Resultado | Evidencia segura |
|---|---|---|---|---|
| 2026-05-17 | Interno | Guia criado | Em preparacao | Documento central criado para venda controlada. |

Exemplos de evidencia segura:

- "Cadastro confirmado pelo cliente";
- "Primeira venda real feita com sucesso";
- "Health producao OK antes da implantacao";
- "Cliente entendeu que financeiro completo nao entra no Basico".

Nao registrar:

- senha;
- token;
- cookie;
- link privado com credencial;
- documento fiscal sensivel;
- dados pessoais alem do necessario.

## Rotina semanal

Toda semana, revisar:

- [ ] Quantos prospects existem.
- [ ] Quantas demos foram feitas.
- [ ] Quantos clientes entraram em onboarding.
- [ ] Quantos estao ativos sem bloqueador.
- [ ] Quais duvidas apareceram mais.
- [ ] Quais bugs P0/P1 apareceram.
- [ ] Se algum item da oferta precisa mudar.

## Ordem recomendada a partir de agora

1. Definir preco e condicao do Plano Basico.
2. Retestar e-mail de confirmacao no Outlook.
3. Montar proposta curta e FAQ.
4. Selecionar ate 5 clientes piloto.
5. Fazer a primeira demo.
6. Implantar o primeiro cliente usando o checklist.
7. Registrar evidencia e aprendizados.
8. Corrigir P0/P1 antes de escalar.

## Referencias

- `docs/PLANO_COMERCIAL_PRONTIDAO_MODULOS_2026-05.md`
- `docs/auditorias/plano-basico-tenant-checklist.md`
- `docs/MATURIDADE_GERAL_10_10_GUIA.md`
- `docs/PADRAO_EVIDENCIA.md`
