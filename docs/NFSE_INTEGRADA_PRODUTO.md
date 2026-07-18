# NFS-e integrada como adicional do CorePet

## Decisão comercial

- Valor: **R$ 59,90 por mês**.
- Contratação separada do plano principal.
- Disponível para clientes dos módulos **Veterinário** e **Banho & Tosa**.
- A emissão será feita por um emissor fiscal parceiro, mas dentro do fluxo do CorePet.
- O cliente não deverá precisar acessar outro sistema para emitir ou acompanhar a nota.

O adicional não deve ser vendido como emissão própria do CorePet. A comunicação correta é:

> Emissão de NFS-e integrada ao CorePet, operada por emissor fiscal parceiro.

## Jornada de ativação

1. O cliente encontra o adicional na página de planos ou em **Meu Plano**.
2. Clica em **Ativar emissão de NFS-e**.
3. Confirma o valor de R$ 59,90 por mês.
4. Preenche ou revisa os dados fiscais necessários:
   - CNPJ e razão social;
   - inscrição municipal;
   - município de emissão;
   - regime tributário;
   - código dos serviços e alíquota de ISS;
   - certificado ou credencial exigida pelo emissor e pelo município.
5. O CorePet verifica a compatibilidade do município com o emissor parceiro.
6. A configuração passa por uma emissão de homologação ou validação assistida.
7. Somente depois da validação o adicional fica com status **Ativo**.

Enquanto pagamento e homologação ainda forem assistidos, o botão pode abrir o atendimento com
uma mensagem pronta. Quando a cobrança estiver integrada, a mesma tela deverá iniciar o checkout
sem alterar a jornada apresentada ao cliente.

## Estados do adicional

- `inactive`: ainda não contratado;
- `pending_payment`: aguardando confirmação da contratação;
- `pending_configuration`: contratado, mas faltam dados fiscais;
- `validating`: configuração sendo homologada;
- `active`: emissão liberada;
- `suspended`: cobrança ou configuração fiscal precisa ser regularizada;
- `unsupported_city`: município ainda não atendido pelo emissor escolhido.

O sistema nunca deve apresentar o recurso como ativo apenas porque o pagamento foi confirmado.
Município, credenciais e código de serviço também precisam estar validados.

## Estrutura técnica necessária

### Assinatura

Criar um adicional independente do plano principal, identificado por `nfse_integrada`. Ele deve
registrar, por empresa:

- status;
- valor contratado;
- data de ativação;
- próxima cobrança;
- emissor parceiro;
- referência da assinatura no meio de pagamento;
- motivo de bloqueio ou pendência.

### Configuração por empresa

A configuração fiscal precisa ser isolada por `tenant_id` e guardar apenas referências seguras para
credenciais e certificados. Tokens, senhas e certificados não podem aparecer em respostas da API,
logs ou telas administrativas.

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

Se o adicional não estiver ativo, o CorePet continua registrando normalmente a venda e o atendimento.
O usuário deve ver a opção de contratar a emissão integrada, sem bloquear agenda, consulta ou PDV.

## Segurança e responsabilidade

- Cada emissão deve pertencer ao mesmo `tenant_id` da venda ou atendimento.
- Webhooks devem validar assinatura e identificar a empresa antes de atualizar uma nota.
- Reenvios precisam ser idempotentes para não gerar duas notas.
- Alterações e cancelamentos devem entrar no histórico de auditoria.
- O contador e a empresa continuam responsáveis pela classificação fiscal, alíquotas e códigos de
  serviço utilizados.

## Ordem de implementação

1. Escolher o emissor parceiro e validar cobertura de municípios.
2. Criar adicional, estados e configuração por empresa.
3. Implementar homologação de uma empresa e um CNPJ.
4. Conectar emissão ao Veterinário.
5. Conectar emissão ao Banho & Tosa.
6. Adicionar cobrança e ativação automática.
7. Liberar para novos CNPJs somente após monitorar o primeiro cliente real.

## Critérios para considerar pronto

- contratação e status visíveis no CorePet;
- configuração fiscal isolada por empresa;
- uma NFS-e emitida sem acessar o portal do parceiro;
- consulta, PDF, XML e cancelamento disponíveis;
- falhas traduzidas em mensagens claras;
- nenhuma emissão duplicada após repetição da requisição;
- venda ou atendimento continuam acessíveis mesmo se o emissor estiver indisponível;
- logs e auditoria suficientes para suporte e conciliação.
