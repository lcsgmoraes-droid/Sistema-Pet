# Fusao automatica de pessoas duplicadas

## Objetivo

Detectar pessoas duplicadas por nome 100% igual apos normalizacao, fundir automaticamente os casos seguros e manter sugestoes de revisao para os casos com conflito.

## Regras

- Considerar todas as pessoas do tenant, independentemente de `tipo_cadastro`.
- Nome igual deve ser comparado normalizado: sem acentos, sem diferenca de caixa e sem espacos repetidos.
- Fusao automatica so ocorre quando nao houver conflito nos campos fortes de identidade/contato.
- Havendo conflito de CPF, CNPJ, CRMV, email, telefone ou celular, o par vira sugestao manual.
- A fusao usa o servico existente para preservar historico, vinculos, credito e referencias.
- O cadastro principal deve priorizar registro ativo, com mais historico, mais dados preenchidos e menor ID como desempate.

## Implementacao

1. Criar testes unitarios para normalizacao, decisao segura/conflitante e escolha do cadastro principal.
2. Criar servico `pessoa_duplicate_service` com funcoes puras e rotina de varredura por tenant.
3. Adicionar endpoints para listar sugestoes e executar fusoes automaticas seguras.
4. Expor na tela de Cadastros um alerta discreto com varredura automatica e atalho para revisar sugestoes.
5. Validar com teste unitario e revisao do diff.

## Fora do escopo imediato

- Criar modelo multi-segmento para uma pessoa ser cliente e fornecedor ao mesmo tempo.
- Agendar job recorrente no servidor.
