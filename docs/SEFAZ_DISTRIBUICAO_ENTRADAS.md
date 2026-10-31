# Distribuição de NF-e de entrada pela SEFAZ

O CorePet acompanha NF-e modelo 55 emitidas **para o CNPJ da empresa** pelo serviço nacional `NFeDistribuicaoDFe`. A consulta usa `distNSU`: o NSU é a sequência de distribuição do CNPJ interessado, não o número da nota. A SEFAZ devolve `ultNSU` (ponto para continuar) e `maxNSU` (maior ponto conhecido naquele retorno). O CorePet guarda o último lote recebido antes de atualizar seu cursor. O visor de `maxNSU` mostra apenas o último retorno registrado, sem fazer consulta adicional. Em uma rejeição `656` de `distNSU`, a SEFAZ pode informar o NSU da última consulta feita para aquele CNPJ. Esse valor ajuda no diagnóstico, mas não comprova que o CorePet salvou os documentos daquele intervalo e não deve avançar seu cursor automaticamente.

## Antes de ativar

1. Confirmar se o certificado A1, o CNPJ e o ambiente de produção estão válidos em **Configurações > Integrações > SEFAZ**.
2. Confirmar com o escritório contábil se ele já usa `NFeDistribuicaoDFe/distNSU` para o **mesmo CNPJ de 14 dígitos**. Dois coletores precisam compartilhar a sequência e a cadência. Se ele usa, combinar um coletor principal ou obter o `ultNSU` e o histórico recente antes de ativar o CorePet.
3. Preservar o `ultimo_nsu` existente. Não usar reset nem “pular para hoje” como atalho: isso pode omitir documentos. A consulta pontual pela chave não inicia nem substitui a varredura sequencial.
4. Só depois da implantação em produção, ativar a importação automática para a empresa. O agendador consulta um lote por ciclo, respeita pelo menos uma hora sem novidades e espera após bloqueio `656`. Conferir no painel o horário, código de retorno, último NSU salvo e mensagens. Não repetir consultas durante o bloqueio.

O serviço pode fornecer primeiro apenas `resNFe`, um **resumo sem itens**. O CorePet o mostra como “Aguardando XML” e guarda o documento. O XML integral passa a ficar disponível após manifestação do destinatário ou pode ser importado por arquivo. O CorePet não envia Ciência, Confirmação da Operação nem outra manifestação automaticamente; a conferência fiscal continua com a empresa e o escritório. Eventos recebidos, como cancelamento, são guardados para análise, sem lançar ou reverter estoque por conta própria.

A distribuição não é em tempo real nem segue necessariamente a data de emissão. Para um CNPJ que começa a usar o serviço ou ficou mais de 60 dias sem acesso, pode não haver recuperação retroativa de todos os documentos. A janela usual de distribuição é de até 90 dias. Por isso, a data de início efetivo só pode ser confirmada depois do primeiro retorno de produção e da conciliação com o escritório; ativar a opção na tela, sozinho, não prova que todas as notas do dia chegaram.

## Fontes oficiais

- [Nota Técnica 2014.002 v1.40, distribuição DF-e](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=uWO2d%2FgTuWg%3D)
- [Nota Técnica 2014.002: NSU da última consulta no retorno 656](https://www.nfe.fazenda.gov.br/Portal/exibirArquivo.aspx?conteudo=U0LlsYVGBRU%3D)
- [Regras de consumo e bloqueio 656](https://www.nfe.fazenda.gov.br/portal/informe.aspx?AspxAutoDetectCookieSupport=1&Informe=0cu%2FyBLKrCs%3D&ehCTG=false)
- [Prazo de manifestação do destinatário em 2026](https://www.nfe.fazenda.gov.br/portal/informe.aspx?AspxAutoDetectCookieSupport=1&Informe=f9R6A+5SmSE%3D&ehCTG=false)
