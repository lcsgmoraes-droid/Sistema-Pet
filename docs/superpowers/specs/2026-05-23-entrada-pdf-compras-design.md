# Entrada por PDF em compras - design

## Contexto

Alguns fornecedores enviam pedidos ou romaneios em PDF, nao em XML de NF-e. O sistema ja tem a Central NF-e Entradas com fluxo maduro para vincular produtos, conferir custos, processar estoque e gerar contas a pagar. A nova entrada por PDF deve reaproveitar esse fluxo, mudando apenas a origem do arquivo.

## Decisoes

- A primeira versao fica na propria Central NF-e Entradas, com um botao `Importar PDF`.
- O usuario escolhe o fornecedor antes de enviar o PDF, porque o arquivo de pedido nao traz uma identificacao fiscal confiavel do emissor.
- O backend extrai os itens do PDF e cria uma `NotaEntrada` com serie `PDF`, mantendo compatibilidade com a tela atual.
- O processamento de estoque, vinculos de produtos, conferencia de custo e contas a pagar seguem o mesmo caminho usado pela entrada XML.
- A tela mostra um aviso claro: PDF nao e documento fiscal e nao traz chave NF-e, CFOP, NCM, impostos, lote ou validacoes SEFAZ. Para produtos ja cadastrados, os dados fiscais existentes do sistema devem ser preservados.
- Ao processar uma entrada PDF, o sistema nao deve apagar dados fiscais existentes do produto quando o item importado nao trouxer essas informacoes.

## Fluxo

1. Usuario abre `Compras > Central NF-e Entradas`.
2. Clica em `Importar PDF`.
3. Seleciona fornecedor e arquivo PDF.
4. Backend extrai pedido, data, itens, quantidades, valores e parcelas quando existirem.
5. Sistema cria a entrada com origem PDF e tenta vincular produtos pelos mesmos criterios disponiveis para XML.
6. Usuario revisa divergencias, vinculos e custos.
7. Usuario processa a entrada para atualizar estoque e gerar financeiro.

## Fora de escopo nesta etapa

- OCR para PDF escaneado/imagem.
- Validacao fiscal SEFAZ.
- Leitura generica de qualquer layout de fornecedor.
- Cadastro automatico de fornecedor a partir do PDF.

## Validacao

- Teste unitario do parser com o layout do arquivo `PEDIDO 2.pdf`.
- Teste de compatibilidade do XML sintetico usado para reaproveitar o fluxo atual.
- Teste para garantir que dados fiscais do produto nao sejam sobrescritos por campos vazios vindos do PDF.
- Build do frontend e testes focados do backend.
