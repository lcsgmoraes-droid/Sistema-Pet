# Testes e2e (Playwright)

Testes de regressao em navegador real para os fluxos criticos do CorePet:
login, Pessoas, Produtos e PDV. Validam o comportamento documentado em
`Documentacao/` rodando contra uma stack de verdade (dev ou ensaio), nao
mocks.

## Como rodar

Precisa de uma stack rodando (backend + frontend) e de um usuario de teste
ja existente nela. Nunca aponte isso para producao.

```bash
E2E_BASE_URL=http://localhost:5173 \
E2E_USER_EMAIL=seu-usuario-de-teste@exemplo.com \
E2E_USER_PASSWORD=senha-do-usuario-de-teste \
npm run test:e2e
```

Sem essas 3 variaveis, os testes sao pulados (skip), nunca falham por falta
delas - seguro de deixar no CI sem configurar nada.

`E2E_HEADED=1` abre o navegador visivel (default: headless).

## Por que nao tem credenciais no codigo

O usuario de teste usado para validar esta suite manualmente pertence a uma
copia de producao restaurada em banco de ensaio (dado real de cliente,
mesmo que só em ambiente de teste). Credencial nenhuma de login entra em
arquivo versionado - sempre via variavel de ambiente, de preferencia de um
tenant criado so pra isso.

## O que cada teste cobre

- `login.spec.js` - login por e-mail chega numa tela autenticada.
- `pessoas.spec.js` - cria uma pessoa (nome + celular), confirma que aparece
  na listagem.
- `produtos.spec.js` - cria um produto, confirma na listagem, registra uma
  entrada de estoque.
- `pdv.spec.js` - fluxo completo: cria pessoa + produto, da entrada de
  estoque, abre o caixa se necessario, busca o produto no PDV, adiciona ao
  carrinho, vincula o cliente e salva a venda.

## Observacao de acessibilidade (achado durante a validacao manual)

O campo "Preço de Venda" do formulario de produto
(`src/pages/produtos/...`) nao tem `name`/`id` e o `label` correspondente
nao usa `htmlFor` - a associacao e so visual. Os helpers desta suite
localizam o campo por texto do label + proximo input
(`tests/e2e/helpers.js`), o que funciona mas e fragil a mudanca de layout.
Vale corrigir na origem quando alguem mexer nesse formulario de novo.
