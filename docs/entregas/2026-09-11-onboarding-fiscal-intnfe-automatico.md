# Ficha de entrega — onboarding fiscal IntNFe automático

## Objetivo

Permitir que cada empresa do CorePet prepare a emissão fiscal dentro do próprio
sistema, com o mínimo de digitação e sem copiar credenciais técnicas. A última
numeração permanece manual porque pode vir de qualquer sistema emissor anterior.

## Entregue

- vínculo do emitente criado pelo CorePet com um clique;
- sincronização automática do cadastro fiscal após o vínculo e após alterações
  nos dados da empresa;
- campo de código IBGE do município, preenchido pela consulta de CNPJ quando a
  fonte devolver essa informação;
- uso do e-mail de respostas da empresa nas comunicações fiscais;
- envio protegido do certificado A1 em `.pfx` ou `.p12`, sem guardar o arquivo,
  a senha, o nome do arquivo ou a impressão digital no CorePet;
- situação e alerta diário de vencimento do A1;
- checklist de preparação de NF-e e NFC-e;
- CSC informado dentro do CorePet, separado por homologação e produção;
- série e último número configurados manualmente, com seleção explícita de
  modelo e ambiente e regra de somente avançar;
- normalização de dados de transportadora vindos do Bling;
- estrutura independente do conector para identificar canal, referência externa,
  destino, intermediador, frete, transportadora e pagamento de pedidos do PDV,
  Mercado Livre, Amazon, Shopee e TikTok Shop;
- guia do usuário atualizado em Markdown, Word e PDF.

O acesso pode ser liberado para todas as empresas usando a configuração vazia ou
`*` na lista de tenants permitidos. A flag da integração e as credenciais do
integrador continuam obrigatórias no ambiente.

## Validação

- 116 testes de backend para vínculo, cliente HTTP, numeração, CSC, A1 e cadastro
  fiscal;
- 30 testes de backend para contexto fiscal de pedidos e normalização de notas;
- 2 testes de frontend para o alerta de certificado;
- lint do frontend e build Vite de produção aprovados;
- cadeia de migrations conferida com `zzo20260911a1` como head;
- documento de seis páginas renderizado e inspecionado visualmente;
- nenhuma credencial conhecida nem certificado rastreado pelo Git.

## Limites e próximos passos

O fluxo configura o emitente, mas a emissão automática a partir de uma venda do
CorePet ainda precisa do adaptador final que transforma o pedido no payload da
IntNFe. Antes da liberação fiscal real, executar no tenant piloto: vínculo,
sincronização, A1, numeração, CSC quando houver NFC-e e uma NF-e de homologação.
Depois, validar pedidos do PDV e de cada marketplace, incluindo venda
interestadual, intermediador, transportadora e formas de pagamento.

Produção exige revisão e autorização explícita antes do deploy. A publicação deve
aplicar a migration antes do backend e manter um rollback por desativação da flag.
