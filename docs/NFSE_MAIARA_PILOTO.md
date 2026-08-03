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

## Comparacao comercial para um CNPJ

Precos publicos consultados em 2026-08-03:

| Opcao | Menor preco publico confirmado | API | Observacao |
| --- | ---: | --- | --- |
| Focus NFe Solo | R$ 89,90/mes | Sim | 1 CNPJ, 100 documentos e 30 dias de teste; cobertura especifica confirmada para Presidente Prudente |
| NFE.io Base mensal | R$ 190,00/mes | Sim | Ate 250 notas |
| Webmania PME | R$ 199,90/mes | Sim | 1 CNPJ e 500 notas |
| PlugNotas | Sob consulta | Sim | Sem preco publico que permita comprovar vantagem para este piloto |
| Integracao direta Simpliss | Sem mensalidade de gateway | Sim, via protocolo municipal | Maior custo de desenvolvimento, seguranca e manutencao; nao recomendada para o primeiro piloto |

Decisao: manter a Focus NFe. E a opcao publica mais barata com API e cobertura municipal
confirmada para a necessidade atual. O adaptador do CorePet continua isolando o fornecedor para
permitir troca futura.

Fontes de preco:

- Focus NFe: <https://2025.focusnfe.com.br/precos/>
- NFE.io NFS-e: <https://nfe.io/precos/emissao-nfse/>
- Webmania: <https://webmania.com.br/nota-fiscal-eletronica/>

Fontes tecnicas:

- Prefeitura: <https://www.presidenteprudente.sp.gov.br/servico/nfse.xhtml>
- Aviso municipal sobre o emissor proprio em 2026: <https://issprudente.sp.gov.br/contrib/Home/NotificacaoNovoLayout>
- Integracao e arquivos tecnicos da prefeitura: <https://issprudente.sp.gov.br/contrib/app/nfse/DocumentoIntegracaoNotaNacional/Index>
- Cobertura especifica da Focus para Presidente Prudente: <https://focusnfe.com.br/guides/nfse/municipios-integrados/presidente-prudente-sp/>
- API de emissao da Focus: <https://doc.focusnfe.com.br/reference/emitir_nfse>

## O que ja existe no CorePet

- configuracao separada por `tenant_id`;
- validacao dos dados obrigatorios da clinica e do tomador;
- adaptador da Focus NFe com tokens criptografados por tenant e alternativa operacional por
  variavel de ambiente;
- emissao vinculada a consulta veterinaria finalizada;
- referencia unica por consulta para impedir nota duplicada;
- consulta de status, PDF/XML e cancelamento;
- bloqueio adicional de producao por `NFSE_PRODUCTION_ENABLED=false`;
- tabelas protegidas por isolamento de tenant no banco.
- parametros de NFS-e centralizados na configuracao fiscal da empresa, sem duplicar CNPJ, regime,
  CNAE, ISS ou retencao na integracao;
- leitura e validacao do certificado A1 ja enviado ao CorePet, incluindo validade e conferencia do
  CNPJ;
- escolha entre cadastro manual na Focus ou compartilhamento consentido do A1 diretamente pelo
  backend;
- login e senha municipais criptografados e nunca devolvidos pela API.

## Dados que precisamos da Maiara e da contabilidade

Nao enviar certificado, senha ou token por chat e nunca salvar esses dados no Git.

1. CNPJ e razao social exatos da clinica.
2. Inscricao municipal ativa em Presidente Prudente.
3. Confirmacao se a empresa e optante pelo Simples Nacional e qual regime especial deve ser informado.
4. Item da lista de servicos da LC 116. Para medicina veterinaria, a referencia legal e normalmente `5.01`, mas o contador deve confirmar antes da primeira nota.
5. Aliquota de ISS e regra de retencao confirmadas pelo contador.
6. Certificado digital A1 valido e pertencente ao CNPJ. Ele pode ser reutilizado do cadastro seguro
   do CorePet ou enviado manualmente no painel da Focus.
7. Login e senha do portal municipal, armazenados de forma criptografada quando o compartilhamento
   automatico for escolhido.
8. Cadastro de homologacao separado do cadastro de producao, como exige o municipio.
9. Um tutor de teste autorizado, com CPF/CNPJ e endereco completo, para a primeira nota de homologacao.

## Fluxo da primeira nota

1. Preencher os dados cadastrais e os parametros de NFS-e em **Configuracao fiscal da empresa**.
2. Iniciar os 30 dias de teste em <https://2025.focusnfe.com.br/cadastro/>.
3. Informar os tokens master e de homologacao na tela segura de ativacao. Como alternativa
   operacional, configurar `FOCUS_NFE_MASTER_TOKEN` e `FOCUS_NFE_TOKEN_HOMOLOGACAO` fora do
   repositorio.
4. Escolher no CorePet entre:
   - reutilizar o A1 ja configurado, com confirmacao explicita antes do envio servidor a servidor; ou
   - cadastrar certificado e credenciais manualmente no painel da Focus.
5. Executar a pre-validacao; o status passa para `validating` somente quando nao houver pendencias.
6. Finalizar uma consulta de teste com tutor e valor de servico completos.
7. Emitir a NFS-e de homologacao pelo CorePet.
8. Sincronizar ate obter autorizacao ou erro claro da prefeitura.
9. Conferir PDF, XML, valores, item de servico e ISS com a contabilidade.
10. Testar cancelamento em homologacao.
11. Somente depois revisar a liberacao para producao.

## Decisao comercial pendente

O preco antigo do adicional CorePet e `R$ 59,90/mês`. Em 2026-08-03, o plano Solo publicado pela Focus com NFS-e custa `R$ 89,90/mês` para um CNPJ. Portanto, o valor do adicional precisa ser revisto, cobrado junto com o custo do emissor ou o CorePet tera de subsidiar o piloto. Nenhuma contratacao paga foi feita nesta implementacao.

Referencia: <https://2025.focusnfe.com.br/precos/>
