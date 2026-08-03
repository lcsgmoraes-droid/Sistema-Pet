# Piloto de NFS-e - Maiara / Presidente Prudente

Atualizado em: 2026-08-03

## Decisao do piloto

- Tenant piloto: `Clinica Veterinaria Sao Jose`.
- Municipio de emissao: Presidente Prudente/SP, codigo IBGE `3541406`.
- Provedor municipal: Simpliss.
- Integrador escolhido para a primeira homologacao: Focus NFe.
- Ambiente inicial obrigatorio: homologacao.
- O CorePet continua independente do fornecedor por meio de um adaptador.
- Emissao de producao permanece bloqueada ate a homologacao ser aprovada.

Fontes tecnicas:

- Prefeitura: <https://www.presidenteprudente.sp.gov.br/servico/nfse.xhtml>
- Aviso municipal sobre o emissor proprio em 2026: <https://issprudente.sp.gov.br/contrib/Home/NotificacaoNovoLayout>
- Integracao e arquivos tecnicos da prefeitura: <https://issprudente.sp.gov.br/contrib/app/nfse/DocumentoIntegracaoNotaNacional/Index>
- Cobertura especifica da Focus para Presidente Prudente: <https://focusnfe.com.br/guides/nfse/municipios-integrados/presidente-prudente-sp/>
- API de emissao da Focus: <https://doc.focusnfe.com.br/reference/emitir_nfse>

## O que ja existe no CorePet

- configuracao separada por `tenant_id`;
- validacao dos dados obrigatorios da clinica e do tomador;
- adaptador da Focus NFe com token somente em variavel de ambiente;
- emissao vinculada a consulta veterinaria finalizada;
- referencia unica por consulta para impedir nota duplicada;
- consulta de status, PDF/XML e cancelamento;
- bloqueio adicional de producao por `NFSE_PRODUCTION_ENABLED=false`;
- tabelas protegidas por isolamento de tenant no banco.

## Dados que precisamos da Maiara e da contabilidade

Nao enviar certificado, senha ou token por chat e nunca salvar esses dados no Git.

1. CNPJ e razao social exatos da clinica.
2. Inscricao municipal ativa em Presidente Prudente.
3. Confirmacao se a empresa e optante pelo Simples Nacional e qual regime especial deve ser informado.
4. Item da lista de servicos da LC 116. Para medicina veterinaria, a referencia legal e normalmente `5.01`, mas o contador deve confirmar antes da primeira nota.
5. Aliquota de ISS e regra de retencao confirmadas pelo contador.
6. Certificado digital aceito pela prefeitura e respectivas credenciais. O cadastro deve ser feito diretamente no ambiente seguro do emissor.
7. Cadastro de homologacao separado do cadastro de producao, como exige o municipio.
8. Um tutor de teste autorizado, com CPF/CNPJ e endereco completo, para a primeira nota de homologacao.

## Fluxo da primeira nota

1. Preencher os dados fiscais do tenant e a configuracao de NFS-e.
2. Configurar `FOCUS_NFE_TOKEN_HOMOLOGACAO` fora do repositorio.
3. Executar a pre-validacao; o status passa para `validating` somente quando nao houver pendencias.
4. Finalizar uma consulta de teste com tutor e valor de servico completos.
5. Emitir a NFS-e de homologacao pelo CorePet.
6. Sincronizar ate obter autorizacao ou erro claro da prefeitura.
7. Conferir PDF, XML, valores, item de servico e ISS com a contabilidade.
8. Testar cancelamento em homologacao.
9. Somente depois revisar a liberacao para producao.

## Decisao comercial pendente

O preco antigo do adicional CorePet e `R$ 59,90/mês`. Em 2026-08-03, o plano Solo publicado pela Focus com NFS-e custa `R$ 89,90/mês` para um CNPJ. Portanto, o valor do adicional precisa ser revisto ou o CorePet tera de subsidiar o piloto. Nenhuma contratacao paga foi feita nesta implementacao.

Referencia: <https://2025.focusnfe.com.br/precos/>
