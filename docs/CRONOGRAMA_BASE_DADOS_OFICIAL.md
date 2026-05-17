# Cronograma - Base Oficial de Dados e Atualizacoes

Atualizado em: 2026-05-17

Este documento organiza a evolucao da base inicial do Sistema Pet. A ideia e
ter uma biblioteca oficial, versionada e atualizavel, que o usuario possa usar
para iniciar o sistema com bons cadastros e depois importar novidades sem perder
as alteracoes proprias.

## O que ja existe

O onboarding de novo tenant ja cria uma base minima e obrigatoria:

- formas de pagamento;
- contas bancarias iniciais;
- especies;
- racas;
- linhas de racao;
- portes de animal;
- fases/publicos de racao;
- tipos de tratamento;
- sabores/proteinas;
- apresentacoes/pesos;
- categorias DRE;
- subcategorias DRE;
- categorias financeiras;
- tipos de despesa;
- departamentos de produto;
- categorias de produto.

Tambem existe seed veterinario base por tenant, com:

- insumos/produtos de consumo veterinario;
- catalogo de medicamentos;
- protocolos de vacina;
- procedimentos veterinarios com insumos vinculados.

## Objetivo 10/10

Criar uma biblioteca oficial de dados do Sistema Pet com atualizacao assistida:

- o sistema oferece pacotes oficiais por area;
- o usuario escolhe importar, ignorar ou atualizar;
- cada item tem codigo estavel, versao e origem;
- alteracoes feitas pelo cliente nao sao sobrescritas sem confirmacao;
- o sistema mostra o que e novo, o que mudou e o que pode conflitar.

## Pacotes de dados

Pacotes iniciais recomendados:

- `core-br`: DRE, formas de pagamento, categorias financeiras e cadastros
  operacionais obrigatorios.
- `pet-catalogo-br`: especies, racas, portes, fases, sabores, apresentacoes e
  taxonomias de produto.
- `produtos-pet-br`: produtos base com dados, imagens, categorias, atributos,
  codigos e sugestoes comerciais.
- `veterinario-br`: insumos, procedimentos, medicamentos, bulas resumidas,
  protocolos de vacina, exames comuns e materiais clinicos.
- `banho-tosa-br`: servicos, pacotes, adicionais e produtos de apoio.
- `campanhas-br`: campanhas sugeridas, cupons modelo e regras de fidelidade.

## Modelo de atualizacao

Cada item oficial deve ter:

- `source_bundle`: pacote de origem;
- `source_version`: versao do pacote;
- `template_code`: codigo estavel;
- `target_table`: tabela de destino;
- `target_id`: item criado no tenant;
- `status`: ativo, ignorado, substituido ou personalizado;
- `hash_payload`: hash do conteudo oficial importado;
- `last_seen_version`: ultima versao oferecida ao tenant.

Regra central:

- template oficial pertence ao sistema;
- copia importada pertence ao tenant;
- atualizacao oficial nunca apaga customizacao do cliente sem comparacao e
  confirmacao.

## Fluxo para o usuario

Tela futura: `Biblioteca de Dados`.

Abas sugeridas:

- Disponiveis: pacotes ainda nao importados.
- Atualizacoes: itens novos ou alterados em pacotes ja importados.
- Importados: historico por pacote e versao.
- Conflitos: itens que o cliente alterou e precisam de decisao.

Acoes:

- importar pacote completo;
- importar itens selecionados;
- atualizar apenas itens nao personalizados;
- comparar versao oficial x versao do cliente;
- ignorar uma atualizacao;
- restaurar item oficial como copia nova.

## Produtos com dados e imagens

Objetivo: permitir que um tenant novo comece com uma boa base de produtos.

Fases:

- [ ] Definir campos oficiais do produto base.
- [ ] Definir politica de imagens: URL oficial, cache local ou upload por
      pacote.
- [ ] Criar pacote `produtos-pet-br` com produtos comuns de pet shop.
- [ ] Criar importacao opcional de produtos, nunca automatica no cadastro.
- [ ] Marcar origem oficial em cada produto importado.
- [ ] Permitir atualizacao de preco/categoria/atributo sem sobrescrever estoque
      ou preco que o cliente ja ajustou.
- [ ] Criar preview antes de importar.

Campos recomendados:

- nome;
- codigo oficial;
- codigo de barras quando houver;
- categoria/departamento;
- marca;
- linha;
- especie/fase/porte;
- unidade;
- descricao curta;
- imagem;
- atributos nutricionais ou comerciais;
- preco sugerido opcional;
- custo sugerido opcional;
- tags.

## Veterinario ampliado

Objetivo: transformar o seed veterinario atual em uma base clinica muito mais
forte, mas sempre com aviso de que e apoio operacional, nao prescricao automatica.

Fases:

- [ ] Ampliar insumos/produtos de consumo veterinario.
- [ ] Ampliar procedimentos por categoria: consulta, vacina, exame, cirurgia,
      internacao, curativo, coleta e retorno.
- [ ] Ampliar medicamentos com principio ativo, concentracao, especie indicada,
      posologia de referencia, alertas e contraindicacoes.
- [ ] Criar campo de bula/resumo tecnico com fonte e data de revisao.
- [ ] Criar protocolos de vacina por especie e faixa etaria.
- [ ] Criar lista de exames comuns e materiais necessarios.
- [ ] Criar trilha de revisao humana para medicamentos/bulas antes de liberar
      para clientes.
- [ ] Criar tela de atualizacao para o cliente aceitar novas entradas.

Regras de seguranca:

- medicamento/bula deve ser apresentado como referencia operacional;
- nao prometer diagnostico ou prescricao automatica;
- registrar fonte e data da ultima revisao;
- permitir desativar item no tenant sem apagar o template oficial;
- manter logs de importacao/atualizacao.

## Implementacao tecnica sugerida

1. Evoluir `template_bundles` e `template_items` para suportar pacotes maiores e
   versoes independentes por area.
2. Criar metadados de importacao por item com hash do payload.
3. Criar servico de diff: novo, igual, alterado, personalizado, conflito.
4. Criar endpoints read-only para listar pacotes disponiveis.
5. Criar endpoint de preview de importacao.
6. Criar endpoint de aplicar importacao com auditoria.
7. Criar UI `Biblioteca de Dados`.
8. Migrar o seed veterinario para pacote oficial versionado.
9. Criar pacote opcional de produtos com imagens.
10. Criar rotina de manutencao para adicionar novos itens ao pacote oficial.

## Proxima acao recomendada

Antes de implementar, fechar a primeira versao do desenho:

- pacote core continua automatico no onboarding;
- produtos com imagens entram como importacao opcional;
- veterinario ampliado entra como pacote opcional/recomendado para clinicas;
- atualizacoes oficiais aparecem como sugestao, nunca sobrescrevem o cliente sem
  confirmacao.
