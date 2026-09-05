# Cadastro rápido de produtos no app

No perfil **Funcionário**, abra **Novo produto**. Leia o código de barras pela
câmera ou digite o código e toque em **Consultar código**.

- Se o produto já existir, o app mostra nome, código interno, preço e eventual
  status inativo. O cadastro existente é preservado.
- Se não existir, informe nome e preço de venda. Custo é opcional e a unidade
  começa em UN. Toque em **Cadastrar produto**.
- O produto é salvo no cadastro de Produtos do ERP, com um código interno
  automático, estoque zero e anúncios no app/loja online desativados. Fotos,
  categoria, marca e dados fiscais podem ser completados pelo ERP.
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
no mesmo catálogo do ERP. Estoque inicial, fotos, tributação, variações e kits
continuam nos fluxos existentes. O formulário permite digitação sem câmera,
acomoda teclado e apresenta valores em formato brasileiro.

### 2. Regras e dados

Nome, código e preço de venda positivo são obrigatórios. Custo é opcional.
SKU é automático. Não há migration, importação ou novo dado pessoal; o usuário
criador permanece em `user_id` do produto. Empresa vem da sessão autenticada.
Campos fora do cadastro rápido são rejeitados. Consulta e gravação consideram
inativos, GTIN comercial/tributário, SKU e códigos alternativos completos.

### 3. Arquitetura e integrações

Rotas novas sob `/api/app/funcionario/produtos`, com tela e serviço mobile próprios.
A criação reutiliza `ProdutoService`; não chama a rota administrativa com token
de cliente. API usa a sessão e o timeout já existentes no app. Uma falha mantém
o formulário; uma nova tentativa verifica duplicidade antes de gravar.
Não há integração externa adicional.

### 4. Segurança e privacidade

Autenticação mobile e perfil operacional são obrigatórios nas duas rotas.
Consultas e gravações têm tenant explícito. Testes verificam negação de acesso
e ausência de exposição/conflito com outra empresa. Nenhum segredo ou nova
configuração é necessário; não registrar tokens ou dados pessoais em logs.
Finalidade e retenção seguem o cadastro de produtos existente.

### 5. Qualidade

- 27 testes de API com banco SQLite isolado: criação, reenvio, inativos, GTIN,
  UPC/EAN com zeros, código alternativo completo, campos inválidos e acesso.
- 40 testes existentes de estoque/PDV, SKU, EAN e tipo de produto passaram.
- 3 testes mobile de moeda e mensagens de erro passaram.
- `npm run typecheck`, Ruff e exportação Expo para Android/iOS passaram.
- Exportação local em `runtime/qa-produto-rapido`, fora do Git.

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
publicação e rollback avaliados. Decisão: pronta para revisão, com validação em
aparelho e autorização de produção pendentes do Lucas antes da publicação.
