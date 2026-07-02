# Pacote Inicial de Videos - Sistema Pet

Uso: organizar a primeira leva de criativos e demonstracoes do Sistema Pet.

Dados estruturados: `docs/marketing/base-demo/dados_base_demo_sistema_pet.json`.
Plano de captura: `docs/marketing/PLANO_CAPTURA_TELAS_DEMO.md`.
Apresentacao comercial: `docs/marketing/APRESENTACAO_COMERCIAL_DEMO_5_8_MIN.md`.
Manifesto de seed: `scripts/gerar_seed_base_demo_marketing.py`.
Aplicador dry-run/apply DEV: `scripts/aplicar_seed_base_demo_marketing.py`.
Tenant demo sugerido desta leva: `corepeterp@gmail.com`.

## Objetivo da primeira leva

Criar um conjunto pequeno, coerente e reutilizavel:

- 3 videos de venda para captar interesse.
- 5 demos curtas para mostrar produto real.
- 1 video de onboarding para novos usuarios.
- 1 video horizontal maior para apresentacao consultiva.

## Ordem recomendada

| Ordem | Video | Tipo | Duracao | Formato principal | Documento base |
|---|---|---|---:|---|---|
| 1 | Estoque que some | Venda | 20s | 9:16 | `ROTEIROS_CRIATIVOS_VENDA.md` |
| 2 | Recebimentos baguncados | Venda | 30s | 9:16 | `ROTEIROS_CRIATIVOS_VENDA.md` |
| 3 | Lucro real | Venda | 25s | 9:16 | `ROTEIROS_CRIATIVOS_VENDA.md` |
| 4 | Comparador de racao | Venda/demo | 25s a 45s | 9:16 e 16:9 | `ROTEIROS_CRIATIVOS_VENDA.md` |
| 5 | Vendas com rentabilidade | Demo | 60s | 16:9 | `ROTEIROS_DEMO_FUNCIONALIDADES.md` |
| 6 | Produto, PDV e estoque | Demo | 60s | 16:9 e 9:16 | `ROTEIROS_DEMO_FUNCIONALIDADES.md` |
| 7 | Financeiro antes da primeira venda | Demo | 75s | 16:9 | `ROTEIROS_DEMO_FUNCIONALIDADES.md` |
| 8 | Entregas e comissoes | Demo | 60s | 16:9 | `ROTEIROS_DEMO_FUNCIONALIDADES.md` |
| 9 | Configuracao inicial | Demo/onboarding | 60s | 16:9 e 9:16 | `ROTEIROS_DEMO_FUNCIONALIDADES.md` |
| 10 | Como configurar do zero | Onboarding | 3 a 5 min | 16:9 | `GUIA_IMPLANTACAO_INICIAL.md` |
| 11 | Visao geral Sistema Pet | Apresentacao | 5 a 8 min | 16:9 | `APRESENTACAO_COMERCIAL_DEMO_5_8_MIN.md` |

## Lote 1 - Criativos de venda

### Video 1 - Estoque que some

Entrega:

- 1 video vertical 9:16.
- 1 capa estatica.
- 1 legenda curta para post.
- 1 versao sem voz, apenas musica e legenda.

Gravar:

1. Produto com estoque.
2. Venda no PDV.
3. Tela de estoque/alertas.

Takes base: 07, 08 e 09 em `PLANO_CAPTURA_TELAS_DEMO.md`.

Mensagem:

```text
Seu estoque nao pode depender de memoria. Venda e estoque precisam caminhar juntos.
```

CTA:

```text
Controle seu estoque em tempo real com o Sistema Pet.
```

### Video 2 - Recebimentos baguncados

Entrega:

- 1 video vertical 9:16.
- 1 versao com gancho alternativo.
- 1 legenda curta para post.

Gravar:

1. Formas de pagamento.
2. Venda no PDV.
3. Contas a receber.

Takes base: 03, 05 e 06 em `PLANO_CAPTURA_TELAS_DEMO.md`.

Mensagem:

```text
PIX, dinheiro e cartao precisam nascer organizados desde o caixa.
```

CTA:

```text
Organize seus recebimentos.
```

### Video 3 - Lucro real

Entrega:

- 1 video vertical 9:16.
- 1 corte de 15s.
- 1 legenda curta para post.

Gravar:

1. Relatorio de vendas.
2. Dashboard financeiro ou DRE.
3. Indicadores de resultado.

Takes base: 04, 07, 11 e 19 em `PLANO_CAPTURA_TELAS_DEMO.md`.

Mensagem:

```text
Vender muito nao significa lucrar. O gestor precisa enxergar custo, venda e resultado.
```

CTA:

```text
Veja seu lucro com mais clareza.
```

## Lote 2 - Demos curtas

### Video 4 - Comparador de racao

Entrega:

- 1 video vertical 9:16 para criativo.
- 1 trecho horizontal para apresentacao.

Gravar:

1. `/calculadora-racao`.
2. Peso `12`, idade `36`.
3. `Comparar Todas`.
4. Melhor custo-beneficio, custo/dia e preco/kg.

Mensagem:

```text
Preco de pacote nao conta a historia inteira. Compare racoes pelo custo do dia a dia.
```

### Video 5 - Vendas com rentabilidade

Entrega:

- 1 video horizontal 16:9.
- 1 corte vertical com zoom nos indicadores.

Gravar:

1. `/financeiro/vendas`.
2. Aba Lista de Vendas.
3. Totais de venda bruta, liquida, custo, lucro, margem, imposto e comissao.
4. Exemplos de venda baixada, aberta, ecommerce e campanha.

Mensagem:

```text
Cada venda mostra canal, taxas, custo, imposto, comissao e margem.
```

### Video 6 - Produto, PDV e estoque

Entrega:

- 1 video horizontal 16:9 para treinamento.
- 1 corte vertical 9:16 para rede social.

Gravar:

1. Introducao Guiada.
2. Etapas obrigatorias.
3. Itens condicionais por modulo.
4. Central de Ajuda.

Mensagem:

```text
O usuario novo nao precisa adivinhar por onde comecar.
```

### Video 7 - Financeiro antes da primeira venda

Entrega:

- 1 video horizontal 16:9.
- 1 corte de 30s para prospeccao.

Gravar:

1. Formas de pagamento.
2. Banco/conta.
3. Categoria financeira.
4. Venda no PDV.
5. Contas a receber.

Mensagem:

```text
O financeiro precisa estar configurado antes da primeira venda.
```

### Video 8 - Entregas e comissoes

Entrega:

- 1 video horizontal 16:9.
- 2 cortes curtos: entrega e comissao.

Gravar:

1. `/entregas/rotas` com Carlos Entregador Demo.
2. Rota pendente e rota em andamento.
3. `/comissoes` com Beatriz Vendedora Demo.
4. `/comissoes/abertas` com 8 comissoes pendentes.

Mensagem:

```text
Entrega e comissao tambem precisam entrar na conta da operacao.
```

### Video 9 - Configuracao inicial

Entrega:

- 1 video horizontal 16:9 para treinamento.
- 1 corte vertical 9:16 para rede social.

Gravar:

1. Introducao Guiada ou Central de Ajuda.
2. Etapas obrigatorias.
3. Financeiro antes da venda.
4. Itens condicionais por modulo.

Mensagem:

```text
O usuario novo nao precisa adivinhar por onde comecar.
```

## Lote 3 - Conteudo longo

### Video 10 - Como configurar o Sistema Pet do zero

Entrega:

- 1 video horizontal de 3 a 5 minutos.
- Marcadores de tempo por etapa.
- Descricao para YouTube ou base de ajuda.

Estrutura:

1. Empresa e usuarios.
2. Financeiro obrigatorio.
3. Impostos/configuracao fiscal.
4. Cadastros base.
5. Produtos e estoque.
6. Venda no PDV.
7. Compras/XML.
8. Modulos opcionais.

### Video 11 - Visao geral Sistema Pet

Entrega:

- 1 video horizontal de apresentacao comercial.
- 3 cortes curtos por dor: lucro real, comparador de racao e entregas.

Roteiro completo:

- Usar `docs/marketing/APRESENTACAO_COMERCIAL_DEMO_5_8_MIN.md`.

Estrutura resumida:

1. Vendas com rentabilidade.
2. Produtos e estoque.
3. Comparador de racao.
4. Recebimentos, contas a pagar, fluxo e DRE.
5. Entregas e comissoes.
6. Dashboard financeiro como alerta executivo.
7. CTA para demonstracao.

## Checklist de publicacao

Para cada video:

- Nome do arquivo segue `GUIA_PRODUCAO_VIDEO_IA.md`.
- Tela gravada existe no sistema atual.
- Base demo nao tem dados reais.
- Manifesto de seed demo foi gerado antes de gravar.
- Aplicador dry-run foi executado com `--tenant-email corepeterp@gmail.com`.
- `--apply` foi usado somente em DEV/demo confirmado, nunca em producao.
- Gancho aparece nos primeiros 3 segundos.
- Legenda esta legivel no celular.
- CTA aparece no final.
- Versao final foi assistida inteira.
- Capa estatica foi gerada quando o canal exigir.
- Link ou arquivo foi registrado no controle interno.

## Controle de status

| Video | Roteiro | Base demo | Gravado | Editado | Publicado |
|---|---|---|---|---|---|
| Estoque que some | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Recebimentos baguncados | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Lucro real | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Comparador de racao | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Vendas com rentabilidade | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Produto, PDV e estoque | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Financeiro antes da primeira venda | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Entregas e comissoes | Pronto | Dados validados | Pendente | Pendente | Pendente |
| Configuracao inicial | Pronto | Precisa revisar tela de ajuda | Pendente | Pendente | Pendente |
| Como configurar do zero | Pronto | Precisa revisar tela de ajuda | Pendente | Pendente | Pendente |
| Visao geral Sistema Pet | Pronto | Dados validados para vendas/financeiro/produtos/entregas/comissoes | Pendente | Pendente | Pendente |
