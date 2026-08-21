# Validação do guia no Chrome

Data: 2026-08-21  
PR: a registrar após a abertura do Pull Request  
Commit: branch `codex/docs-configurando-taxas-cartao`  
Ambiente: produção, em tenant autorizado pelo responsável do sistema  
Responsável: Codex/Lucas  
Comando: validação manual da rota `/cadastros/financeiro/operadoras` no perfil autenticado do Chrome  
Resultado: aprovado; foram conferidos o caminho pelo menu, as sugestões de operadoras, a seleção conjunta e separada de bandeiras, as modalidades crédito e débito, a habilitação das parcelas e a operadora padrão  
Evidência: capturas sem e-mail, cookies ou valores reais de taxas em `docs/ajuda/configurando-taxas-de-cartao/imagens/`  
Impacto: nenhum cadastro foi alterado; todas as simulações foram encerradas com **Cancelar** e a operadora usada como exemplo permaneceu inativa e sem taxas configuradas  
Próxima ação: publicar o guia após revisão do Pull Request e manter esta pasta como parte do acervo de ajuda do CorePet

## Observações da validação

- O caminho visível no menu é **Cadastros → Operadoras de Cartão**.
- Visa e Mastercard podem ser selecionadas juntas quando possuem as mesmas condições.
- As bandeiras também podem ser configuradas separadamente.
- O indicador `1/2` representa uma de duas bandeiras configurada, e não metade da taxa.
- Crédito e débito mantêm tabelas independentes.
- Marcar uma parcela como configurada habilita os campos de taxa percentual, taxa fixa e prazo de recebimento.
- Deixar a bandeira padrão vazia mantém a opção de solicitá-la em cada venda.

