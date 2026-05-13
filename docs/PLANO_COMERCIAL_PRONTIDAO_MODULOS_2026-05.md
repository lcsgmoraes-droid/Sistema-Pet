# Plano Comercial e Prontidao de Modulos - Maio/2026

Objetivo: chegar ate o final de maio/2026 com uma oferta vendavel, segura e honesta
para terceiros, sem esperar o ERP inteiro ficar perfeito.

## Decisao Principal

Nao vamos esperar todas as refatoracoes e todos os modulos ficarem 100%.

Vamos vender primeiro um nucleo estavel, com escopo bem delimitado, e deixar
modulos mais amplos como adicionais, beta ou liberacao controlada.

O produto deve ser vendido pelo que esta pronto, nao pelo que esta em construcao.

## Linha de Corte Para Venda Inicial

### Plano Basico - candidato a venda inicial

Escopo:

- cadastro de pessoas/clientes;
- cadastro de pets;
- cadastro de produtos e toda a rotina de produtos/estoque;
- formas de pagamento padrao via onboarding;
- PDV/vendas completo;
- historico de cliente, timeline e historico financeiro ligado a vendas;
- financeiro aberto apenas na aba de vendas/recebimentos de venda;
- usuarios, roles e LGPD operacional;
- cadastros essenciais: categorias de produto, especies/racas, opcoes de racao,
  formas de pagamento e operadoras de cartao;
- configuracoes essenciais: empresa, parametros gerais e estoque;
- relatorios gerenciais de vendas;
- dashboards/resumos de resultado de venda, quando nao dependerem do financeiro operacional beta.

Promessa comercial:

> Sistema de gestao para pet shop com cadastro, produtos, estoque, vendas/PDV e visao gerencial de vendas.

Nao prometer ainda:

- DRE completa validada diariamente;
- contas a pagar/receber como financeiro oficial;
- conciliacao bancaria/cartao como modulo fechado;
- veterinario completo;
- banho e tosa completo;
- e-commerce completo;
- automacoes/IA como requisito central.

### Plano Nivel 2 - operacional compras/estoque

Escopo candidato:

- fornecedores;
- grupos de fornecedores;
- pedidos de compra;
- sugestao inteligente de compra;
- entrada por XML;
- notas de entrada;
- ajustes de estoque ligados a compra.

Status:

- forte candidato a adicional/plano intermediario;
- precisa checklist proprio de smoke antes de vender em escala;
- pode entrar para primeiros clientes se o fluxo principal ja estiver validado no dia a dia.

### Beta Financeiro/ERP

Escopo:

- contas a pagar;
- contas a receber;
- DRE;
- provisoes;
- comissoes;
- conciliacao bancaria/cartao;
- fluxo de caixa/projecao;
- financeiro operacional completo.

Status:

- beta controlado;
- nao deve ser vendido como financeiro oficial ainda;
- pode aparecer como "em validacao" para clientes piloto selecionados.

### Beta Veterinario

Escopo:

- agenda veterinaria;
- consultas;
- prontuario;
- exames;
- internacao;
- catalogos clinicos;
- relatorios veterinarios;
- parcerias.

Status:

- separar como produto/vertical propria;
- nao misturar promessa veterinaria no plano basico de pet shop;
- precisa checklist funcional e permissao por plano antes de vender.

### Beta Banho e Tosa

Escopo:

- agenda;
- servicos;
- recursos;
- atendimentos;
- custos;
- taxi dog;
- pacotes;
- recorrencias;
- retornos;
- relatorios;
- integracao com PDV.

Status:

- separar como vertical propria;
- liberar para piloto quando a jornada agenda -> atendimento -> cobranca -> retorno estiver validada.

### Outros Modulos/Adicionais

- Bling/integracoes: adicional controlado.
- E-commerce: beta/adicional.
- Campanhas/WhatsApp/IA: beta ou add-on futuro.
- Fiscal/NFe: apenas quando checklist fiscal estiver fechado.
- Conciliacao cartao/bancaria: beta financeiro.

## Politica de Liberacao no Sistema

Implementacao atual:

- novos tenants criados pelo cadastro normal nascem com `plan = "basico"`;
- tenants legados com `plan = "free"` continuam liberados para evitar corte
  acidental de uso real ja existente;
- modulos fora do Basico ficam controlados por `modulos_ativos` ou assinatura ativa;
- o menu do Plano Basico esconde modulos extras e remove "Fechamento Mensal";
- acesso direto por URL a modulo bloqueado cai na tela de venda/desbloqueio do modulo;
- a API tambem bloqueia rotas de modulos adicionais com `require_active_module`,
  evitando acesso direto por chamada manual ao backend.
- a tela publica `/planos` permite simular a compra do Plano Basico e leva para
  o cadastro com `plan=basico`, ainda sem pagamento online.

Modulos controlados fora do Basico:

- compras/entrada XML;
- financeiro ERP;
- comissoes;
- veterinario;
- banho e tosa;
- fiscal/NF;
- Bling/integracoes;
- RH operacional;
- IA avancada;
- campanhas;
- entregas;
- WhatsApp;
- e-commerce;
- app mobile;
- marketplaces.

## Checklist de Prontidao do Plano Basico

Um modulo entra no Plano Basico apenas se passar por estes criterios.

### 1. Tenant e seguranca

- Rota usa usuario/tenant autenticado.
- Dados sao filtrados por `tenant_id`.
- Inserts gravam `tenant_id`.
- SQL bruto tenant-scoped usa `execute_tenant_safe` ou ORM com contexto.
- Nao ha dependencia de dados globais editaveis pelo usuario.
- Smoke com dois tenants confirma isolamento.

### 2. Jornada funcional

Fluxo minimo:

1. Criar empresa nova.
2. Confirmar readiness:

```powershell
python backend/app/scripts/run_tenant_onboarding.py --signup-readiness-check --include-products
```

3. Confirmar que o tenant nasce com:
   - formas de pagamento;
   - estrutura DRE base;
   - categorias financeiras base;
   - departamentos/categorias de produtos.
4. Cadastrar cliente.
5. Cadastrar pet.
6. Cadastrar produto.
7. Ajustar/entrada de estoque.
8. Vender no PDV.
9. Baixar estoque corretamente.
10. Ver venda em relatorio gerencial.
11. Editar dado do tenant e confirmar que nao altera template global.

### 3. UX minima

- Menu nao deve mostrar modulos beta para plano basico, salvo com selo claro de beta.
- Tela principal do fluxo nao pode depender de modulo ainda instavel.
- Erros precisam ser compreensiveis para usuario final.
- Fluxos principais precisam funcionar em desktop comum.

### 4. Suporte operacional

- Criacao de tenant nova precisa falhar fechado se onboarding falhar.
- Health/ready da producao precisa estar verde.
- Backup e rollback definidos antes de migrations.
- Logs nao devem expor senha, token, DATABASE_URL ou dados sensiveis.

## Gates Go/No-Go Antes da Primeira Venda

### Go

- `backend/tests/multi_tenant` verde.
- `import app.main` ok.
- `--signup-readiness-check --include-products` verde.
- Smoke transacional de dois tenants verde.
- Produção health/ready verde.
- Plano Basico visualmente separado dos betas.
- Primeiro cliente sabe exatamente o escopo comprado.

### No-Go

- Novo tenant nasce sem templates obrigatorios.
- Modulo beta aparece como funcional completo no plano basico.
- PDV ou estoque falha em jornada principal.
- Dados de um tenant aparecem em outro.
- Migrations pendentes sem checklist/backup.
- Erro 500 em tela basica recorrente.

## Refatoracoes: Antes ou Depois da Venda?

Antes da venda inicial:

- corrigir apenas riscos que afetem Plano Basico;
- bloquear/ocultar betas se necessario;
- garantir onboarding e isolamento;
- garantir smoke do fluxo basico.

Depois da venda inicial:

- limpar SQL bruto legado por lotes;
- refatorar financeiro/DRE;
- modularizar veterinario;
- modularizar banho e tosa;
- evoluir feature flags/plans;
- padronizar UX de modulos avancados;
- tratar warnings de encoding Windows.

Conclusao: refatoracao geral nao deve bloquear a venda do Plano Basico, desde que o
escopo vendido esteja protegido e validado.

## Estrategia Comercial Recomendada

### Fase 1 - Piloto pago controlado

Periodo alvo: segunda quinzena de maio/2026.

Clientes:

- 2 a 5 empresas;
- perfil simples: pet shop com venda/produto/estoque;
- sem promessa de financeiro completo.

Oferta:

- Plano Basico com suporte proximo;
- compras/XML como adicional se o cliente realmente precisar;
- financeiro/veterinario/banho e tosa como beta controlado.

### Fase 2 - Plano Nivel 2

Liberar compras/XML formalmente quando o checklist do modulo passar:

- fornecedor;
- produto vinculado a fornecedor;
- pedido de compra;
- entrada XML;
- atualizacao de estoque;
- relatorio/consulta de compra;
- isolamento tenant.

### Fase 3 - Verticais

Separar:

- Pet Shop Basico;
- Pet Shop + Compras;
- Veterinario;
- Banho e Tosa;
- Financeiro/ERP.

Cada vertical deve ter checklist proprio e liberacao gradual.

## Proxima Sequencia de Implementacao

1. Criar matriz tecnica de modulos e planos no codigo ou configuracao.
2. Revisar menu/permissoes para esconder ou marcar beta fora do plano.
3. Criar smoke test documentado do Plano Basico.
4. Rodar smoke do Plano Basico em staging/local.
5. Corrigir apenas bloqueadores P0/P1 do Plano Basico.
6. Preparar checklist de primeira implantacao de cliente.
7. Rodar piloto pago controlado.

## Diretriz Para Codigo Novo

Todo codigo novo deve respeitar:

- `docs/CONTRATO_MULTITENANT_E_ONBOARDING.md`;
- nenhum dado tenant-scoped sem `tenant_id`;
- nenhum SQL bruto tenant-scoped sem helper seguro;
- nenhum modulo beta exposto como produto final;
- nenhuma promessa comercial sem smoke test correspondente.

## Estado de Confianca Atual

Base multitenant/onboarding para novos tenants: boa e validada.

Plano Basico: forte candidato para venda controlada, apos checklist de menu/permissoes
e smoke ponta a ponta do fluxo comercial.

ERP financeiro completo: beta.

Veterinario e Banho e Tosa: verticais futuras/beta, nao escopo principal da primeira venda.
