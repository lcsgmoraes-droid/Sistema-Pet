# Ficha de entrega: valor informado no PDV

## Identificação

- Data: 2026-10-22.
- Responsável de negócio: Lucas. Executor: Codex.
- Prioridade: P1. Risco médio: cálculo compartilhado entre venda e seus demonstrativos.
- Domínios: PDV, estoque, descontos, rentabilidade, comissão e emissão fiscal.
- PR: correção na branch `feat/20261019-1708-cadastro-e-central-ifood`.

## 1. Necessidade e requisitos

O vídeo apresentado mostra ração a R$ 13,00/kg. Digitar R$ 20,00 convertia
o peso para 1,538 kg e recalculava o subtotal como R$ 19,99. O aceite é manter
R$ 20,00 no campo, total, salvamento, reabertura e documentos, com peso de
1,538 kg e preço de catálogo de R$ 13,00. Alterar o peso ou preço explicitamente
continua recalculando a linha.

## 2. Regras de negócio e dados

- Valor digitado é líquido do desconto do item. A conversão considera desconto
  fixo ou percentual antes de calcular o peso.
- Peso permanece com três casas; valores monetários com duas. A divisão no
  frontend usa centavos inteiros para acompanhar o arredondamento do backend.
- Backend preserva subtotal + desconto somente se dividir esse bruto pelo preço
  produzir a mesma quantidade após arredondar para três casas. Divergências
  incompatíveis continuam recalculadas; valores inválidos continuam validados.
- Focar e sair da quantidade sem alterá-la preserva o valor informado.
- Sem migration, importação ou alteração retroativa de vendas.

## 3. Arquitetura e integrações

O carrinho distingue edição por valor de edição por quantidade. A mesma base
validada acompanha normalização, rateio, devolução, análise, rentabilidade e
demonstrativo de comissão. O preview do desconto usa o cálculo do salvamento.
IntNFe reutiliza a prova da quantidade no contrato atual e o ajuste existente
do preço unitário fiscal para fechar o total; a regra legada continua separada.
Clientes da análise sem subtotal continuam compatíveis.

## 4. Segurança e privacidade

Sem mudanças de autenticação, permissões, isolamento entre empresas ou segredos.
Fixtures são fictícias. Nenhuma operação em dados reais ou emissão externa.

## 5. Desenvolvimento e qualidade

- Frontend: testes reais dos handlers de digitação, Enter, blur, Escape,
  quantidade, payload, reedição, desconto e análise, com cálculos reais.
- Backend: normalização, totais, descontos, rateio, devolução, roundtrip em
  colunas DECIMAL usando SQLite, rentabilidade, comissão e payload NF-e/NFC-e.
- Exemplos: 20/13; 29/19,90; 34,90/29,90; 189,90/178,90;
  129,99/130; limite de meio grama 2,05/0,16; entradas incompatíveis.
- Comandos: `node --test` nas suítes PDV, pagamento e novas regressões;
  `python -m pytest` nas suítes de descontos, fiscal, custo original,
  rentabilidade e demonstrativo; ESLint nos arquivos frontend alterados;
  `npm run build`; `FLUXO_UNICO.bat check`; `git diff --check`.
- Resultado: 251 testes frontend e 172 backend passaram, além do script de
  preço manual; ESLint/Prettier e build passaram. O build mantém o aviso de
  tamanho de chunks, sem erro.
- Verificação adicional conhecida: `test_pdv_margem_comissao_config_contract.py`
  procura código no antigo agregador `formas_pagamento_routes.py`; uma asserção
  falha por essa referência anterior à correção. O cálculo real da análise é
  exercitado nos testes de descontos.

## 6. Ambientes e homologação

Validação local com testes isolados; sem homologação em tenant real, envio
fiscal ou deploy. Aceite visual com Lucas e homologação operacional pendentes.
Nenhuma variável nova. O build local permanece fora do Git.

## 7. Publicação e rollback

Entrega frontend + backend, por PR. Produção exige autorização explícita,
release-check e deploy seguro com rebuild do backend e frontend. Sem migrations.
Smoke recomendado: digitar 20,00 em item de 13,00/kg, salvar e reabrir, confirmar
subtotal20,00 e peso1,538. Reverter pelo Git e pelo deploy seguro se houver
divergência financeira; nenhuma correção manual no banco faz parte da entrega.

## 8. Observabilidade e sustentação

Indicador de sucesso: mesmo valor no carrinho, persistência e documentos.
Descompasso que não corresponda ao arredondamento do peso continua sujeito
às validações existentes. Reincidência deve incluir valor, preço, quantidade,
desconto e etapa em que ocorreu, sem dados pessoais.

## 9. Mudança, comunicação e treinamento

Fluxo do operador permanece igual. Orientação: informar o valor desejado e
conferir o peso calculado. Sem nova configuração ou treinamento específico.

## 10. Fechamento

Critérios automatizados cobertos; revisão por PR, aceite do Lucas e publicação
pendentes. Esta ficha não autoriza deploy de produção.
