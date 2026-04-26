# Blueprint Banho & Tosa Enterprise

Data: 2026-04-24

Objetivo: desenhar um modulo completo de Banho & Tosa para o Sistema Pet, aproveitando clientes, pets, funcionarios, cargos/salarios, estoque, financeiro, entregas/taxi dog, campanhas, app e alertas veterinarios.

Minha recomendacao: Banho & Tosa deve nascer como modulo proprio no menu, nao como aba do veterinario. Ele usa informacao veterinaria, mas a operacao, agenda, custos, produtividade e venda sao de servico operacional.

## 1. Resultado que queremos

O gestor deve conseguir responder, por atendimento:

- Quanto custou esse banho?
- Quanto foi agua?
- Quanto foi energia?
- Quanto foi produto/insumo?
- Quanto foi mao de obra?
- Quanto foi taxi dog?
- Quanto foi comissao?
- Quanto sobrou de margem?
- Qual funcionario foi mais produtivo?
- Qual porte/pelagem da mais margem?
- Onde a agenda gargalou?
- Qual cliente/pet deve receber lembrete ou campanha de retorno?

O atendimento deve sair de "agenda solta" e virar uma ordem operacional rastreavel.

## 2. Personas

- Recepcao: agenda, confirma, faz check-in/check-out, cobra e fala com tutor.
- Banhista: executa banho, registra inicio/fim, usa produtos e ocorrencias.
- Tosador: executa tosa, registra inicio/fim, tipo de tosa e acabamento.
- Motorista/taxi dog: busca/entrega, registra rota, horario, km e status.
- Gestor: acompanha fila, custos, produtividade, margem e agenda.
- Tutor/app: solicita agendamento, acompanha status, recebe lembrete, avalia atendimento.
- Veterinario: nao opera banho/tosa, mas seus alertas clinicos protegem o atendimento.

## 3. Modulos/telas

Menu sugerido: `Banho & Tosa`.

Rotas sugeridas:

- `/banho-tosa`: dashboard operacional.
- `/banho-tosa/agenda`: agenda exclusiva.
- `/banho-tosa/fila`: kanban do dia.
- `/banho-tosa/atendimentos/:id`: ficha do atendimento.
- `/banho-tosa/servicos`: cadastro de servicos e precos.
- `/banho-tosa/parametros`: portes, pelagem, custos e equipamentos.
- `/banho-tosa/taxi-dog`: buscas/entregas.
- `/banho-tosa/pacotes`: pacotes, assinaturas e recorrencias.
- `/banho-tosa/relatorios`: margem, produtividade, ocupacao e gargalos.

## 4. Setup inicial obrigatorio do tenant

Antes de usar o modulo, o sistema deve guiar o cliente por uma configuracao inicial.

Empresa:

- Horario de funcionamento.
- Dias de atendimento.
- Tempo minimo entre atendimentos.
- Politica de atraso/no-show.
- Tolerancia para encaixe.
- Centro de custo/DRE de Banho & Tosa.

Recursos:

- Quantidade de banheiras.
- Quantidade de mesas de tosa.
- Quantidade de secadores/sopradores.
- Salas/boxes.
- Capacidade simultanea por recurso.
- Equipamento principal por etapa.

Custos gerais:

- Custo do litro de agua.
- Vazao media do chuveiro em litros/minuto.
- Custo do kWh.
- Potencia dos equipamentos em W/kW.
- Custo medio de lavanderia/toalha.
- Custo de descarte/higienizacao por atendimento.
- Percentual de impostos/taxas padrao, se aplicavel.

RH:

- Funcionarios que atuam como banhista, tosador, recepcao e motorista.
- Cargo/salario vindo do cadastro atual de cargos.
- Jornada produtiva mensal.
- Percentual de encargos.
- Modelo de comissao: por servico, percentual, fixo, equipe ou nenhum.

Servicos:

- Banho simples.
- Banho completo.
- Banho terapeutico.
- Hidratacao.
- Desembolo.
- Tosa higienica.
- Tosa maquina.
- Tosa tesoura.
- Corte de unha.
- Limpeza de ouvido.
- Escovacao dental.
- Remocao de subpelo.
- Servico avulso/customizado.

Portes:

- Mini.
- Pequeno.
- Medio.
- Grande.
- Gigante.

Para cada porte:

- Faixa de peso.
- Tempo padrao de banho.
- Tempo padrao de secagem.
- Tempo padrao de tosa.
- Agua media.
- Energia media.
- Produtos padrao.
- Preco base por servico.

Pelagem/comportamento:

- Curta, media, longa, dupla, enrolada, embaraçada.
- Calmo, ansioso, agressivo, medo de secador, medo de tesoura.
- Aceita focinheira.
- Precisa dois profissionais.
- Precisa intervalo/pausa.

## 5. Entidades sugeridas

Prefixo sugerido: `banho_tosa_*` ou `bt_*`. Eu usaria `banho_tosa_*` nas tabelas para legibilidade e `bt` nas variaveis internas quando fizer sentido.

### 5.1 Configuracao

`banho_tosa_configuracoes`

- `id`
- `tenant_id`
- `horario_inicio`
- `horario_fim`
- `intervalo_slot_minutos`
- `custo_litro_agua`
- `vazao_chuveiro_litros_min`
- `custo_kwh`
- `custo_toalha_padrao`
- `custo_higienizacao_padrao`
- `dre_subcategoria_receita_id`
- `dre_subcategoria_custo_id`
- `ativo`

`banho_tosa_recursos`

- `id`
- `tenant_id`
- `nome`
- `tipo`: `banheira`, `mesa_tosa`, `secador`, `sala`, `veiculo`
- `capacidade_simultanea`
- `potencia_watts`
- `custo_manutencao_hora`
- `ativo`

### 5.2 Servicos e precos

`banho_tosa_servicos`

- `id`
- `tenant_id`
- `nome`
- `categoria`: `banho`, `tosa`, `higiene`, `tratamento`, `adicional`, `taxi_dog`
- `descricao`
- `duracao_padrao_minutos`
- `requer_banho`
- `requer_tosa`
- `requer_secagem`
- `permite_pacote`
- `ativo`

`banho_tosa_parametros_porte`

- `id`
- `tenant_id`
- `porte`
- `peso_min_kg`
- `peso_max_kg`
- `agua_padrao_litros`
- `energia_padrao_kwh`
- `tempo_banho_min`
- `tempo_secagem_min`
- `tempo_tosa_min`
- `multiplicador_preco`
- `ativo`

`banho_tosa_precos_servico`

- `id`
- `tenant_id`
- `servico_id`
- `porte_id`
- `tipo_pelagem`
- `preco_base`
- `tempo_estimado_minutos`
- `agua_estimada_litros`
- `energia_estimada_kwh`

### 5.3 Agenda

`banho_tosa_agendamentos`

- `id`
- `tenant_id`
- `cliente_id`
- `pet_id`
- `responsavel_agendamento_user_id`
- `profissional_principal_id`
- `banhista_id`
- `tosador_id`
- `data_hora_inicio`
- `data_hora_fim_prevista`
- `status`
- `origem`: `balcao`, `telefone`, `whatsapp`, `app`, `ecommerce`
- `observacoes`
- `restricoes_veterinarias_snapshot`
- `perfil_comportamental_snapshot`
- `valor_previsto`
- `sinal_pago`
- `taxi_dog_id`
- `created_at`
- `updated_at`

`banho_tosa_agendamento_servicos`

- `id`
- `tenant_id`
- `agendamento_id`
- `servico_id`
- `nome_servico_snapshot`
- `quantidade`
- `valor_unitario`
- `desconto`
- `tempo_previsto_minutos`

### 5.4 Atendimento

`banho_tosa_atendimentos`

- `id`
- `tenant_id`
- `agendamento_id`
- `cliente_id`
- `pet_id`
- `status`
- `checkin_em`
- `inicio_em`
- `fim_em`
- `entregue_em`
- `peso_informado_kg`
- `porte_snapshot`
- `pelagem_snapshot`
- `observacoes_entrada`
- `observacoes_saida`
- `ocorrencias`
- `venda_id`
- `conta_receber_id`
- `custo_snapshot_id`

`banho_tosa_etapas`

- `id`
- `tenant_id`
- `atendimento_id`
- `tipo`: `checkin`, `aguardando`, `banho`, `secagem`, `tosa`, `revisao`, `pronto`, `entregue`
- `responsavel_id`
- `recurso_id`
- `inicio_em`
- `fim_em`
- `duracao_minutos`
- `observacoes`

`banho_tosa_fotos`

- `id`
- `tenant_id`
- `atendimento_id`
- `tipo`: `entrada`, `antes`, `depois`, `ocorrencia`
- `url`
- `descricao`
- `created_by`

### 5.5 Insumos e custos

`banho_tosa_insumos_previstos`

- `id`
- `tenant_id`
- `servico_id`
- `porte_id`
- `produto_id`
- `quantidade_padrao`
- `unidade`
- `baixar_estoque`

`banho_tosa_insumos_usados`

- `id`
- `tenant_id`
- `atendimento_id`
- `produto_id`
- `quantidade_prevista`
- `quantidade_usada`
- `quantidade_desperdicio`
- `custo_unitario_snapshot`
- `movimentacao_estoque_id`
- `responsavel_id`

`banho_tosa_custos_snapshot`

- `id`
- `tenant_id`
- `atendimento_id`
- `valor_cobrado`
- `custo_insumos`
- `custo_agua`
- `custo_energia`
- `custo_mao_obra`
- `custo_comissao`
- `custo_taxi_dog`
- `custo_taxas_pagamento`
- `custo_rateio_operacional`
- `custo_total`
- `margem_valor`
- `margem_percentual`
- `detalhes_json`

### 5.6 Taxi dog

`banho_tosa_taxi_dog`

- `id`
- `tenant_id`
- `cliente_id`
- `pet_id`
- `agendamento_id`
- `tipo`: `busca`, `entrega`, `ida_volta`
- `status`
- `motorista_id`
- `endereco_origem`
- `endereco_destino`
- `janela_inicio`
- `janela_fim`
- `km_estimado`
- `km_real`
- `valor_cobrado`
- `custo_estimado`
- `custo_real`
- `rota_entrega_id`

### 5.7 Pacotes e recorrencia

`banho_tosa_pacotes`

- `id`
- `tenant_id`
- `nome`
- `descricao`
- `quantidade_creditos`
- `validade_dias`
- `preco`
- `servicos_permitidos`
- `ativo`

`banho_tosa_pacote_creditos`

- `id`
- `tenant_id`
- `pacote_id`
- `cliente_id`
- `pet_id`
- `creditos_total`
- `creditos_usados`
- `validade_inicio`
- `validade_fim`
- `status`

`banho_tosa_recorrencias`

- `id`
- `tenant_id`
- `cliente_id`
- `pet_id`
- `servico_id`
- `frequencia_dias`
- `proxima_data`
- `ativo`
- `canal_lembrete`

### 5.8 Qualidade

`banho_tosa_checklists`

- `id`
- `tenant_id`
- `atendimento_id`
- `item`
- `concluido`
- `responsavel_id`

`banho_tosa_avaliacoes`

- `id`
- `tenant_id`
- `atendimento_id`
- `cliente_id`
- `nota`
- `comentario`
- `canal`

## 6. Fluxo operacional

### 6.1 Agendamento

1. Recepcao escolhe tutor e pet.
2. Sistema puxa peso, porte, alergias, restricoes, perfil comportamental e historico.
3. Recepcao escolhe servicos.
4. Sistema sugere duracao, preco e custo estimado.
5. Sistema verifica capacidade de banheira, mesa, secador e profissional.
6. Sistema alerta conflito, restricao veterinaria ou comportamento de risco.
7. Se tiver taxi dog, cria janela de busca/entrega.
8. Agendamento fica `agendado` ou `confirmado`.

### 6.2 Check-in

1. Pet chega ou taxi dog marca chegada.
2. Recepcao confere pet e tutor.
3. Sistema registra `checkin_em`.
4. Fotos de entrada podem ser anexadas.
5. Alertas veterinarios aparecem antes de iniciar.
6. Atendimento nasce ou muda para `chegou`.

### 6.3 Execucao

Status/etapas:

- `aguardando`
- `em_banho`
- `em_secagem`
- `em_tosa`
- `em_revisao`
- `pronto`

Cada etapa registra:

- responsavel
- inicio
- fim
- recurso usado
- insumo usado
- ocorrencia

### 6.4 Check-out e entrega

1. Atendimento fica `pronto`.
2. Recepcao revisa valores e descontos.
3. Sistema gera venda/recebimento no PDV ou conta a receber, conforme regra da empresa.
4. Se taxi dog entrega, status fica `taxi_entrega_agendada`.
5. Ao tutor retirar/receber, status vira `entregue`.
6. Sistema envia NPS e sugere proximo agendamento.

## 7. Status padrao

- `agendado`
- `confirmado`
- `taxi_busca_agendada`
- `a_caminho`
- `chegou`
- `aguardando`
- `em_banho`
- `em_secagem`
- `em_tosa`
- `em_revisao`
- `pronto`
- `taxi_entrega_agendada`
- `entregue`
- `cancelado`
- `no_show`

Regras:

- `entregue`, `cancelado` e `no_show` sao finais.
- Reabrir atendimento final exige permissao de gestor e justificativa.
- Mudanca de etapa deve ser idempotente para evitar duplicidade em clique duplo.
- Baixa de estoque deve ser idempotente por atendimento/produto.

## 8. Formula de custo

Custo total:

```text
custo_insumos
+ custo_agua
+ custo_energia
+ custo_mao_obra
+ custo_comissao
+ custo_taxi_dog
+ custo_taxas_pagamento
+ custo_rateio_operacional
= custo_total
```

Margem:

```text
margem_valor = valor_cobrado - custo_total
margem_percentual = margem_valor / valor_cobrado * 100
```

### 8.1 Insumos

```text
custo_insumos = soma((quantidade_usada + desperdicio) * custo_unitario_snapshot)
```

Fonte:

- produto do estoque atual.
- custo medio/lote quando existir.
- fallback para `preco_custo`.

Exemplos:

- shampoo ml.
- condicionador ml.
- perfume ml.
- algodao.
- laco/gravata.
- luva.
- toalha descartavel.
- antipulgas.

### 8.2 Agua

```text
litros_usados = vazao_chuveiro_litros_min * minutos_banho
custo_agua = litros_usados * custo_litro_agua
```

Se o usuario nao medir tempo real, usa o padrao por porte/servico.

### 8.3 Energia

```text
kwh = (potencia_watts / 1000) * (minutos_uso / 60)
custo_energia = kwh * custo_kwh
```

Equipamentos:

- secador.
- soprador.
- maquina de tosa.
- chuveiro eletrico, se aplicavel.
- lavadora/secadora de toalhas, se rateada.

### 8.4 Mao de obra

```text
custo_hora_funcionario = custo_mensal_funcionario / horas_produtivas_mes
custo_mao_obra = soma(custo_hora_funcionario * minutos_na_etapa / 60)
```

Custo mensal do funcionario:

```text
salario_base
+ INSS patronal
+ FGTS
+ provisao ferias
+ provisao 13
+ beneficios, quando cadastrados
```

Fonte inicial:

- `Cargo.salario_base`
- `Cargo.inss_patronal_percentual`
- `Cargo.fgts_percentual`
- `Cargo.gera_ferias`
- `Cargo.gera_decimo_terceiro`

### 8.5 Comissao

Modelos:

- percentual sobre valor do servico.
- valor fixo por servico.
- percentual sobre margem.
- comissao por etapa: banho, tosa, taxi dog.
- divisao entre equipe.

### 8.6 Taxi dog

```text
custo_taxi_dog = custo_km * km_real + custo_motorista + rateio_manutencao
```

Pode reaproveitar:

- configuracao de entrega.
- motoristas/entregadores.
- rotas e Google Maps.

Minha recomendacao: criar agenda/logistica propria de taxi dog para servicos, mas permitir gerar/reutilizar rota de entrega quando fizer sentido.

## 9. Integracoes com o sistema existente

Clientes e pets:

- Reusar `Cliente`.
- Reusar `Pet`.
- Puxar alergias, restricoes, medicamentos continuos e perfil comportamental.
- Registrar historico de banho/tosa no pet.

Veterinario:

- Consumir `PerfilComportamental`.
- Consumir alertas de alergia/restricao.
- Alertar pos-cirurgia, medicacao ou condicao que impeça banho.

Funcionarios/RH:

- Reusar `Cliente` com `tipo_cadastro = funcionario`.
- Reusar `Cargo`.
- Reusar salario/encargos para custo/hora.
- Conectar com comissoes.

Estoque:

- Reusar `Produto`.
- Criar movimentacao de saida por atendimento.
- Baixa idempotente.
- Insumos previstos x usados.

Financeiro/DRE:

- Receita de servico entra como Banho & Tosa.
- Custos entram em CMV/custo direto de servicos.
- Taxi dog pode ser receita e custo separado.
- Gerar contas a receber/pagar conforme regra.

PDV:

- Check-out pode gerar venda de servico.
- Atendimento pode virar item de venda.
- Pacote pode consumir creditos em vez de cobrar valor cheio.

Entregas/taxi dog:

- Reusar entregadores, custo por km e rotas quando aplicavel.
- Taxi dog deve ter status proprio para nao confundir entrega de pedido com transporte de pet.

Campanhas:

- Lembrete de retorno.
- Aniversario do pet com cupom.
- Pet sem banho ha X dias.
- Pacote perto de vencer.
- NPS baixo gera tarefa interna.

App/ecommerce:

- Tutor visualiza agendamento.
- Tutor solicita horario.
- Tutor recebe status: chegou, em banho, pronto.
- Tutor avalia.
- Pagamento online fica para fase posterior, seguindo a regra ja definida: app/ecommerce nao gera pedido/venda sem pagamento aprovado.

## 10. MVP recomendado

Fase 1 - Operacao base:

- Cadastro de servicos.
- Cadastro de parametros por porte.
- Configuracao de agua, energia e recursos.
- Agenda exclusiva.
- Check-in/check-out.
- Kanban do dia.
- Etapas com inicio/fim.
- Insumos previstos/usados.
- Baixa de estoque.
- Calculo de custo/margem por atendimento.
- Historico no pet.

Fase 2 - Gestao e taxi dog:

- Taxi dog vinculado.
- Dashboards de ocupacao/produtividade/margem.
- Comissoes por profissional.
- Relatorios por pet, porte, servico e funcionario.
- Regras de no-show/cancelamento.

Fase 3 - Recorrencia e app:

- Pacotes.
- Assinaturas.
- Creditos.
- Lembretes automaticos.
- NPS.
- Solicitacao de agendamento pelo app.
- Status do atendimento no app.

Fase 4 - Otimizacao enterprise:

- Sugestao automatica de slot por capacidade.
- Preco sugerido por custo/margem.
- Previsao de gargalo.
- IA operacional para resumo de ocorrencias.
- Benchmark de margem por servico/porte.

## 11. Testes obrigatorios

Backend:

- custo de agua por tempo real e estimado.
- custo de energia por equipamento.
- custo de mao de obra por funcionario/cargo.
- custo de insumos por produto/lote.
- status final nao reabre sem permissao.
- baixa de estoque idempotente.
- atendimento multi-tenant isolado.
- pacote nao fica negativo.
- taxi dog nao duplica custo.

Frontend:

- criar agendamento.
- alterar horario.
- detectar conflito.
- iniciar atendimento.
- avancar etapas.
- registrar insumo.
- finalizar e entregar.
- visualizar dashboard.

E2E:

- tutor + pet + agendamento + check-in + banho + tosa + estoque + financeiro + entrega.
- pacote com credito.
- taxi dog ida/volta.
- alerta veterinario bloqueando/avisando atendimento.

## 12. Ordem de implementacao sugerida

1. Criar modelos, migracao e servico puro de calculo de custo.
2. Criar testes unitarios de calculo/status/idempotencia.
3. Criar rotas backend do modulo.
4. Criar frontend de configuracao inicial.
5. Criar agenda e kanban.
6. Criar ficha de atendimento.
7. Integrar estoque.
8. Integrar financeiro/PDV.
9. Integrar taxi dog.
10. Criar dashboards.
11. Integrar pacotes/recorrencias.
12. Integrar app/status/NPS.

## 13. Decisoes que eu ja tomaria

- Banho & Tosa sera modulo proprio.
- Usar `Cliente`/`Pet`/`Funcionario`/`Cargo` existentes.
- Usar produtos do estoque para insumos.
- Criar status proprio de taxi dog para servico.
- Fazer custo por snapshot no atendimento, para nao mudar historico quando custo do produto/salario mudar depois.
- Comecar com custo estimado, mas permitir substituir por uso real.
- Guardar alertas veterinarios em snapshot no agendamento/atendimento.
- Nao depender de app/ecommerce para o MVP; primeiro resolver operacao interna.

## 14. Pendencias antes de codar

- Confirmar nomes finais do modulo/menu.
- Confirmar se taxi dog sera cobrado como item separado ou embutido no servico.
- Confirmar se pacote/assinatura entra no MVP ou fase 2.
- Confirmar se o atendimento pode ser iniciado sem pagamento ou se alguma empresa exigira sinal.
- Definir categorias DRE padrao.
- Definir se havera controle por sala/box desde o MVP ou so por profissional.

## 15. Progresso de implementacao

Atualizado em 2026-04-26.

Implementado no primeiro bloco:

- Modelos e migracao base do modulo Banho & Tosa.
- Registro dos modelos no Alembic e importacao do router no FastAPI.
- Motor puro de calculo de custo/margem por atendimento.
- Testes unitarios para agua, energia, insumos, mao de obra, comissao, taxi dog, snapshot de margem e bloqueio de reabertura de status final.
- Rotas iniciais para configuracao, servicos, parametros por porte, simulacao de custo e dashboard.
- Entrada no menu lateral e rotas frontend `/banho-tosa`, `/banho-tosa/servicos`, `/banho-tosa/parametros`, `/banho-tosa/agenda` e `/banho-tosa/fila`.
- Tela inicial com dashboard, cadastro de servicos, parametros gerais/portes e simulador de margem.
- Agenda basica com tutor, pet, servico, conflito de horario por pet/profissional e check-in.
- Fila inicial com avancos de status ate pronto/entregue e sincronizacao do status final com o agendamento.
- Refatoracao das rotas backend em arquivos menores por responsabilidade.
- Cadastro de recursos/equipamentos operacionais.
- Ficha operacional inicial do atendimento com etapas, inicio/fim, recurso usado e duracao.
- Apoio de funcionarios/responsaveis nas etapas para preparar produtividade e custo real de mao de obra.
- Snapshot operacional de custo real por atendimento, usando etapas, responsaveis, cargos/salarios, encargos, agua, energia, recursos, taxas e rateios.
- Parametrizacao de horas produtivas mensais, toalha e higienizacao padrao por atendimento.
- Painel de margem dentro da ficha operacional, com recalculo manual e recalculo silencioso apos mudancas em etapas/insumos.
- Registro de insumos reais usados no atendimento com custo por produto e opcao segura de baixar estoque no momento do lancamento.
- Busca de produtos/insumos propria do modulo, sem depender do endpoint veterinario.
- Refatoracao dos schemas e models em partes menores, mantendo agregadores compativeis para evitar arquivos grandes.
- Registro de ocorrencias estruturadas por atendimento, com tipo, gravidade, descricao, responsavel e data/hora.
- Registro de fotos por URL para entrada/antes/depois/ocorrencia.
- Agenda com recurso/box selecionavel, validacao de capacidade simultanea e bloqueio de conflito por pet, equipe e recurso.
- Painel de capacidade do dia por recurso, com janela operacional, ocupacao percentual, pico simultaneo e alertas de agenda sem recurso.
- Estorno controlado de insumo com baixa de estoque: impede editar quantidade/custo apos baixa, cria movimentacao de entrada e libera remocao apenas depois do estorno.
- Alertas veterinarios consumidos no Banho & Tosa: snapshots de alergias, condicoes, medicamentos e restricoes aparecem na agenda, fila e ficha operacional.
- Endpoint de sugestao automatica de slots livres por data, duracao e recurso, considerando capacidade simultanea e ocupacao do dia.
- Tela de agenda com sugestoes clicaveis para preencher horario/recurso e grade visual por horario x recurso.
- Upload dedicado de fotos do atendimento, com armazenamento local em `/uploads/banho_tosa`, conversao para WebP, miniaturas e remocao segura dos arquivos ao excluir a foto.
- Fluxo inicial de taxi dog vinculado ao agendamento, com motorista, janela, origem/destino, km, valor/custo, avancos de status e recalculo do custo real do atendimento quando ja existe check-in.
- Relatorio operacional do modulo com resumo financeiro, margem por servico/porte, produtividade por responsavel, ocupacao por recurso, desperdicio de insumos e alertas de parametrizacao.
- Fechamento inicial do atendimento com geracao de venda em aberto no PDV, vinculo `atendimento -> venda`, canal `banho_tosa` e botao na ficha operacional para cobranca pelo caixa.
- Indicador no dashboard de atendimentos prontos sem venda gerada, para reduzir risco de entrega sem cobranca.
- Sincronizacao de fechamento do atendimento com venda, pagamentos e contas a receber, incluindo alertas de cobranca pendente e indicador de vendas abertas no dashboard.
- Tela operacional `/banho-tosa/fechamentos` para listar pendencias de cobranca, gerar venda, sincronizar contas e abrir o PDV por atendimento.
- Modelos, migracao, rotas e tela `/banho-tosa/pacotes` para cadastrar pacotes, liberar creditos por tutor/pet, acompanhar saldo, validade e status.
- Consumo de credito de pacote dentro da ficha do atendimento, com estorno controlado, bloqueio de saldo negativo e bloqueio de venda duplicada quando o atendimento ja foi quitado por pacote.
- Rotas base de recorrencia de Banho & Tosa para preparar lembretes/retornos por tutor, pet, servico, intervalo e canal, sem depender ainda de app/ecommerce ou pagamento online.
- Central `/banho-tosa/retornos` com sugestoes de contato por recorrencia vencendo/vencida, pacote vencendo/saldo baixo e pets sem banho recente.
- Acao para avancar recorrencia para o proximo ciclo e enfileirar lembretes idempotentes no app a partir das sugestoes de retorno.
- Templates configuraveis de campanha de retorno, com segmento por tipo, canal app/e-mail, variaveis de mensagem e disparo idempotente pela central de retornos.
- App do tutor com tela de Banho & Tosa para acompanhar agenda/status do atendimento e registrar NPS apos entrega do pet.
- Indicadores de NPS/avaliacoes no dashboard e no relatorio operacional para acompanhar qualidade percebida do servico.
- Base padrao editavel para iniciar operacao com parametros medios de custos, portes, servicos, recursos e templates de retorno.
- Tooltips explicativos nos principais campos de parametrizacao para facilitar implantacao assistida com cliente.

Proximo bloco sugerido:

- Automatizar gatilhos pos-PDV para sincronizar fechamento sem acao manual, quando o fluxo de eventos do PDV estiver consolidado.
- Preparar automacoes pos-atendimento: pedido de avaliacao por push/e-mail e retorno inteligente conforme NPS.
- Preparar testes assistidos em ambiente de producao/homologacao com agenda, check-in, fotos, taxi dog, custos reais e relatorio operacional.
