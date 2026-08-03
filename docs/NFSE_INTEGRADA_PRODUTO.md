# NFS-e integrada ao CorePet por emissor externo

## Decisão comercial

- Não existe adicional CorePet de **R$ 59,90** para NFS-e.
- A conta, o plano e o pagamento do emissor fiscal são contratados diretamente pelo cliente.
- No piloto da Maiara, a Focus NFe cobra diretamente o plano Solo de **R$ 89,90 por mês**.
- Na oferta pública atual, a integração com emissor fiscal externo aparece somente no plano
  **Pet Venda Ativa**, sempre com a indicação de contratação separada do emissor.
- A emissão será feita pelo parceiro, mas poderá acontecer dentro do fluxo do CorePet.
- O cliente não deverá precisar acessar outro sistema para emitir ou acompanhar a nota.

O recurso não deve ser vendido como emissão própria nem como mensalidade fiscal cobrada pelo
CorePet. A comunicação correta é:

> Integração com emissor fiscal externo. Conta e mensalidade do emissor contratadas separadamente.

## Piloto Maiara / Presidente Prudente

Em 2026-08-03, o primeiro piloto foi definido para o tenant `Clinica Veterinaria Sao Jose`,
em Presidente Prudente/SP. O integrador escolhido para homologação foi a Focus NFe, com o
Simpliss como provedor municipal. Detalhes técnicos, pendências fiscais e trava de produção estão
em `docs/NFSE_MAIARA_PILOTO.md`.

O plano Focus Solo custa R$ 89,90 por mês para um CNPJ e 100 documentos. A conta será da Maiara e
o pagamento será feito diretamente à Focus; o CorePet não cobrará nem subsidiará essa mensalidade.

## Jornada de ativação

1. O cliente acessa a configuração de NFS-e no CorePet.
2. Abre o link oficial da Focus e cria uma conta própria, com cobrança direta pelo emissor.
3. No fluxo padrão, cadastra a empresa emitente no painel da Focus, envia o certificado A1 e
   informa as credenciais municipais.
4. Obtém no painel da Focus os tokens de homologação e produção e os salva no CorePet.
5. Preenche ou revisa os dados fiscais necessários:
   - CNPJ e razão social;
   - inscrição municipal;
   - município de emissão;
   - regime tributário;
   - código dos serviços e alíquota de ISS;
   - certificado ou credencial exigida pelo emissor e pelo município.
   Esses dados ficam na configuração cadastral/fiscal da empresa e são apenas lidos pelo adaptador
   de NFS-e; não devem existir cópias divergentes dentro da integração.
6. O CorePet verifica a compatibilidade do município com o emissor parceiro.
7. A configuração passa por uma emissão de homologação ou validação assistida.
8. Somente depois da validação a integração fica com status **Ativa**.

O login na Focus não configura nem avisa o CorePet automaticamente. O vínculo acontece quando o
cliente informa os tokens no CorePet. Se a Focus disponibilizar o Token Principal de Produção antes
do cadastro do emitente, o CorePet também pode oferecer cadastro automático via API com autorização
explícita para compartilhar o A1.

## Estados da integração

- `pending_configuration`: faltam conta, tokens ou dados fiscais;
- `validating`: configuração sendo homologada;
- `active`: emissão liberada;
- `suspended`: conta externa ou configuração fiscal precisa ser regularizada;
- `unsupported_city`: município ainda não atendido pelo emissor escolhido.

O sistema nunca deve apresentar o recurso como ativo apenas porque os tokens foram informados.
Município, credenciais, certificado e código de serviço também precisam estar validados.

## Estrutura técnica necessária

### Vínculo com o emissor externo

Registrar, por empresa:

- status;
- data de ativação;
- emissor parceiro;
- modo de onboarding, manual ou automático;
- estado seguro dos tokens de homologação e produção;
- referência da empresa no emissor, quando disponível;
- motivo de bloqueio ou pendência.

### Configuração por empresa

A configuração fiscal precisa ser isolada por `tenant_id` e guardar apenas referências seguras para
credenciais e certificados. Tokens, senhas e certificados não podem aparecer em respostas da API,
logs ou telas administrativas.

Se o certificado A1 já estiver no CorePet, a ativação pode oferecer duas escolhas: reutilizar o
arquivo existente com consentimento explícito e envio direto do backend ao emissor, ou fazer o
cadastro manual no painel do parceiro. O navegador recebe somente o estado seguro da validação e
nunca o arquivo, a senha ou credenciais municipais.

### Camada de integração

O CorePet deve conversar com uma interface comum de emissor, sem espalhar regras de um fornecedor
pelo restante do sistema. Operações mínimas:

- validar empresa e município;
- emitir NFS-e;
- consultar NFS-e;
- cancelar NFS-e;
- obter PDF e XML;
- receber atualizações por webhook;
- evitar emissão duplicada usando uma chave única por venda ou atendimento.

Assim será possível trocar de fornecedor futuramente sem refazer os fluxos de Veterinário e
Banho & Tosa.

## Fluxos de emissão

### Veterinário

A emissão poderá partir do fechamento da consulta, procedimento, vacinação ou venda de serviço.
Antes de emitir, a tela deve mostrar tomador, serviços, valores, descontos, código do serviço e ISS.

### Banho & Tosa

A emissão poderá partir da conclusão do atendimento ou da venda no PDV. Pacotes precisam distinguir
o recebimento antecipado do momento fiscal definido com a contabilidade do cliente.

### Operação assistida

Se a integração não estiver ativa, o CorePet continua registrando normalmente a venda e o atendimento.
O usuário deve ver as pendências de configuração sem bloquear agenda, consulta ou PDV.

## Segurança e responsabilidade

- Cada emissão deve pertencer ao mesmo `tenant_id` da venda ou atendimento.
- Webhooks devem validar assinatura e identificar a empresa antes de atualizar uma nota.
- Reenvios precisam ser idempotentes para não gerar duas notas.
- Alterações e cancelamentos devem entrar no histórico de auditoria.
- O contador e a empresa continuam responsáveis pela classificação fiscal, alíquotas e códigos de
  serviço utilizados.

## Ordem de implementação

1. Escolher o emissor parceiro e validar cobertura de municípios.
2. Criar estados e configuração por empresa.
3. Implementar homologação de uma empresa e um CNPJ.
4. Conectar emissão ao Veterinário.
5. Conectar emissão ao Banho & Tosa.
6. Liberar para novos CNPJs somente após monitorar o primeiro cliente real.

## Critérios para considerar pronto

- onboarding e status visíveis no CorePet;
- configuração fiscal isolada por empresa;
- uma NFS-e emitida sem acessar o portal do parceiro;
- consulta, PDF, XML e cancelamento disponíveis;
- falhas traduzidas em mensagens claras;
- nenhuma emissão duplicada após repetição da requisição;
- venda ou atendimento continuam acessíveis mesmo se o emissor estiver indisponível;
- logs e auditoria suficientes para suporte e conciliação.
