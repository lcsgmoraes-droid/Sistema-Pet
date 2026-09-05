# Cadastro rápido de produtos no app

No perfil **Funcionário**, abra **Novo produto**. Leia o código de barras pela
câmera ou digite o código e toque em **Consultar código**.

- Se o produto já existir, o app mostra nome, código interno, preço e eventual
  status inativo. O cadastro existente é preservado.
- Se não existir, informe nome e preço de venda. Custo e descrição são opcionais;
  a unidade começa em UN. Toque em **Cadastrar produto**.
- O SKU/código interno é opcional: o app consulta a disponibilidade do valor
  digitado, incluindo produtos inativos. Vazio gera um SKU automático. O servidor
  verifica novamente ao salvar, e o índice único do ERP impede colisões.
- Em **Fotos**, use **Tirar foto** ou **Galeria**, confira o enquadramento e adicione
  até cinco fotos. A primeira vira principal; elas aparecem na galeria do ERP.
- O produto é salvo no cadastro de Produtos do ERP, com estoque zero e anúncios
  no app/loja online desativados. Categoria, marca e dados fiscais podem ser
  completados pelo ERP.
- Se o envio das fotos falhar, o produto continua salvo. Use **Tentar enviar fotos
  novamente** para enviar as pendentes, sem criar outro produto ou duplicar fotos.
- Para informar estoque, use a operação existente **Balanço de estoque**.

O preço de venda é obrigatório porque essa já é uma regra do ERP para produtos
simples. O fluxo usa o mesmo serviço de criação e o acesso operacional do app.
Clientes sem esse perfil não podem consultar ou cadastrar por essas rotas.

## Validação manual em desenvolvimento

1. No perfil Funcionário, abrir Novo produto e consultar um código ainda ausente.
2. Informar nome, preço e, opcionalmente, custo/unidade. Salvar e localizar pelo
   código interno em Produtos no ERP; abrir o cadastro para completar os dados.
3. Ler novamente o mesmo código. Conferir que aparece o produto existente.
4. Conferir também um produto inativo, GTIN e código alternativo.
5. Negar a câmera e seguir digitando o código. Simular falta de conexão na busca
   e ao salvar: o app deve mostrar erro e manter os dados para nova tentativa.
6. Verificar digitação de preços com vírgula fixa e separador de milhar.
7. Testar SKU livre, ocupado por inativo, com espaços/letras minúsculas e vazio.
8. Preencher descrição; tirar uma foto e selecionar outra na galeria. Remover
   antes de salvar e conferir a ordem, principal e imagens no ERP.
9. Simular falha durante envio de fotos. Conferir produto já salvo, fotos
   pendentes e reenvio. Sair ou iniciar outro cadastro deve avisar sobre pendências.

## Entrega

Mudança em TypeScript e backend, sem dependência ou configuração nativa nova.
Depois da autorização de produção, publicar primeiro o backend pelo fluxo
oficial e então a atualização OTA do app. Preservar versões/runtime dos binários
instalados e seguir `docs/GUIA_RELEASE_APP_MOBILE_EAS.md`.

Uma resposta de consulta sem produto é HTTP 200 com `null`; erros de rede, acesso
ou rota indisponível não significam código disponível. O servidor consulta
novamente antes de gravar, inclui inativos, compara códigos alternativos completos
e serializa cadastros rápidos da empresa em PostgreSQL para impedir duplicação
entre aparelhos ou novas tentativas após timeout.

## Ficha de entrega — 2026-09-05

- Responsável de negócio: Lucas. Executor: Codex. Prioridade: P2.
- Risco: médio, pois cria registros no catálogo. Domínios: produtos e app.
- PR: cadastro rápido de produtos pelo app, na branch de tarefa atual.

### 1. Necessidade e aceite

Funcionários precisam cadastrar um produto sem voltar ao computador. O aceite
é consultar por câmera ou digitação, reconhecer duplicados e gravar o mínimo
no mesmo catálogo do ERP, incluindo descrição e fotos opcionais. Estoque inicial, tributação, variações e kits
continuam nos fluxos existentes. O formulário permite digitação sem câmera,
acomoda teclado e apresenta valores em formato brasileiro.

### 2. Regras e dados

Nome, código de barras e preço de venda positivo são obrigatórios. Custo,
descrição de até 1.000 caracteres e fotos são opcionais. SKU pode ser informado
ou automático e respeita o limite de 50 caracteres do ERP. Não há migration;
o usuário
criador permanece em `user_id` do produto. Empresa vem da sessão autenticada.
Campos fora do cadastro rápido são rejeitados. Consulta e gravação consideram
inativos, GTIN comercial/tributário, SKU e códigos alternativos completos.

### 3. Arquitetura e integrações

Rotas novas sob `/api/app/funcionario/produtos`, com tela e serviço mobile próprios.
A criação reutiliza `ProdutoService`; não chama a rota administrativa com token
de cliente. API usa a sessão e o timeout já existentes no app. Uma falha mantém
o formulário; uma nova tentativa verifica duplicidade antes de gravar. O envio
de fotos usa multipart, timeout de 60 segundos e o storage normal de produtos.
Hash do arquivo evita duplicação em reenvios; a primeira foto é principal.
Não há integração externa adicional nem mudança em dependências nativas.

### 4. Segurança e privacidade

Autenticação mobile e perfil operacional são obrigatórios em todas as rotas.
Consultas e gravações têm tenant explícito. Testes verificam negação de acesso
e ausência de exposição/conflito com outra empresa. Nenhum segredo ou nova
configuração é necessário; não registrar tokens ou dados pessoais em logs.
Finalidade e retenção seguem o cadastro de produtos existente. Upload tem
limites de tamanho/quantidade, validação real de imagem, proteção contra imagens
de dimensões excessivas e reencodificação WebP. Arquivos são separados por empresa
e produto. Falha de gravação no banco remove arquivos sem registro.

### 5. Qualidade

- 46 testes de API com banco SQLite isolado: criação, reenvio, inativos, GTIN,
  SKU, descrição, galeria, acesso, imagens inválidas, falha de storage/banco,
  isolamento e recuperação do envio.
- 40 testes existentes de estoque/PDV, SKU, EAN e tipo de produto passaram.
- 7 testes mobile de moeda, mensagens, fotos pendentes, negação/cancelamento de
  câmera, limite/remoção e resposta atrasada de SKU passaram.
- `npm run typecheck`, Ruff e exportação Expo para Android/iOS passaram.
- Exportação local em `runtime/qa-produto-rapido-fotos`, fora do Git.

### 6. Ambiente e homologação

`FLUXO_UNICO.bat check` e `dev-up` executados. Dados dos testes são fictícios,
descartáveis e separados do banco operacional. A checagem da câmera em aparelho
real e o aceite visual por Lucas permanecem pendentes; usar o roteiro acima.
Não foi emitido um registro de homologação humana, pois ainda não ocorreu.

### 7. Publicação e rollback

Entrega de backend + OTA + documentação. Identificação pelo commit do PR.
Sem mudanças nativas, versões ou runtime. Publicar backend antes da OTA, após
o gate de release e a autorização do Lucas. Validar health e fazer um cadastro
autorizado. Em falha, reverter o PR/OTA pelo fluxo oficial; preservar os produtos
já gravados, que são registros normais do ERP e continuam editáveis.

### 8. Sustentação

O indicador de sucesso é o produto consultável no ERP após salvar no app.
Erros usam os logs HTTP e de criação do serviço existente; não há novo alerta.
Falhas de conexão deixam os campos preenchidos. A alternativa operacional
é o cadastro pelo ERP. Erros recorrentes de gravação devem ser investigados
antes de novas tentativas em lote; prioridade conforme impacto na operação.

### 9. Comunicação

Este guia explica o novo atalho ao perfil Funcionário. Comunicar o caminho
**Funcionário > Novo produto** quando a publicação estiver concluída, incluindo
estoque zero e complementação no ERP. Não exige treinamento adicional além
do roteiro deste documento.

### 10. Fechamento

Implementação e testes automatizados concluídos. Segurança, dados, documentação,
publicação e rollback avaliados. Lucas autorizou a publicação em 05/09/2026.
A validação de câmera e aparência em aparelho real permanece no roteiro acima.

### Preparação da publicação autorizada

- PR #1303 integrado à `main` que já contém caixa/alertas (#1305) e limites de
  estoque (#1304), preservando os registros de publicação dessas entregas.
- Cadastro rápido não acrescenta migration nem altera dependências nativas.
- Histórico EAS consultado: o canal `production` atende runtimes `1.0.3` e `1.0.4`,
  ambos com Android e iOS. Manter esses alvos ao publicar a OTA.
- Executar o gate completo no código integrado; depois juntar o PR, publicar o
  backend pelo launcher oficial e verificar saúde/commit antes das OTAs.
