# Ficha de entrega — NF-e de pedidos Amazon

## Identificação

| Campo | Valor |
|---|---|
| Data | 2026-10-26 |
| Responsável de negócio | Lucas |
| Executor técnico | Codex |
| Versão | Branch `codex/amazon-corepet-fiscal`, PR correspondente |
| Prioridade e risco | P1; alto, pois solicita emissão fiscal e transmite dados pessoais |
| Domínios | Integrações, fiscal e Central NF-e |

## 1. Necessidade e requisitos

Pedido Amazon importado no EcommerceAI deve preparar uma NF-e no CorePet,
emitir após autorização da conta e encaminhar o XML autorizado à Amazon quando
o aplicativo tiver acesso. Aceite: SKU exato vinculado, dados completos,
documento autorizado disponível na Central e aceite Amazon distinguido de envio.
Pedido incompleto, histórico ou resultado incerto exige revisão/reconciliação.
Cancelamentos antigos e automação de recebimentos/estoque ficam fora do escopo.

## 2. Regras de negócio e dados

CorePet é autoridade de produtos, tributação, numeração, emissor e XML.
EcommerceAI é autoridade dos fatos comerciais Amazon e da coordenação da fila.
A identidade tenant/canal/seller/pedido sobrevive à reconexão. Descontos seguem
política explícita; valores de origem e ajuste ficam auditados. Novas tabelas
têm unicidade, isolamento e histórico; nenhuma Venda fictícia é criada.

## 3. Arquitetura e integrações

Contrato: [INTEGRACAO_ECOMMERCEAI_FISCAL.md](../INTEGRACAO_ECOMMERCEAI_FISCAL.md).
Entidade fiscal independente evita efeitos financeiros e de estoque da emissão
por Venda. IntNFe recebe snapshot e chave idempotente persistidos. Resultado
incerto recupera a mesma tentativa dentro da janela segura; não renova chave.
EcommerceAI envia os bytes conferidos por Delivery API; timeout consulta a chave,
e indisponibilidade/permissão preserva download XML/DANFE.

## 4. Segurança e privacidade

Operador autentica com tenant e permissão. Máquina usa o Bearer existente e
escopos fiscais separados, concedidos somente por aprovação humana explícita.
Conexões antigas mantêm os poderes antigos. CPF, endereço, itens e XML são
dados pessoais fiscais; não devem aparecer em logs ou fixtures reais. EcommerceAI
exige criptografia configurada antes de buscar/persistir os dados fiscais.
Usar segredos já configurados da integração, sem versioná-los. Retenção segue os
controles fiscais dos sistemas; desativar automação não apaga documentos.

## 5. Desenvolvimento e qualidade

Implementação dividida em contratos, persistência, serviços, fronteiras HTTP,
fila durável e telas com componentes existentes. Testes usam dados fictícios e
provedores simulados. Cobertura inclui tenant/escopos, revisão/hash, cortes de
ativação, concorrência/leases, timeout, assinatura XML, dados divergentes,
rateio de descontos/frete, documentos, Central e aceite Amazon parcial.

Validações frontend: testes Node/harness e E2E `amazon-fiscal.spec.js` no
CorePet; Vitest `corepetFiscalPanel`/`corepetFiscalApi` e regressões de integração
no EcommerceAI; lint, checagem de tipos e builds locais. Backend: suítes
`test_ecommerceai_fiscal` e `test_corepet_fiscal_*`, regressões fiscais, RLS e
migrações. O payload sintético produzido pelo adaptador Ecom também foi aceito
pelo schema real do CorePet, preservando destinatário, itens e totais.

## 6. Ambientes e homologação

Validação exclusivamente local, com emissor e Amazon simulados. Nenhuma NF real
foi emitida nestes testes. Homologação operacional real permanece pendente de
publicação autorizada, credenciais/permissões e configuração da conta. Sucesso
local não comprova disponibilidade da API restrita da Amazon para uma conta real.

## 7. Publicação e rollback

Entrega backend/frontend com migrações aditivas nos dois sistemas. Publicar
CorePet primeiro, migrar seu banco e verificar a API; publicar backend e frontend
EcommerceAI com a nova dependência `lxml` e verificar o scheduler. Automação fica
desativada até configurar seller/CNPJ, SKUs, política e consentimentos.
Antes de produção, cumprir `FLUXO_UNICO.bat release-check`, PR e o launcher remoto
oficial CorePet; cumprir o fluxo de release versionado do EcommerceAI.

Smoke: conexão/escopos, conta correta, preparação de pedido novo, mesma identidade
na repetição, situação fiscal e documentos; testar upload somente com acesso
Amazon confirmado. Abortar por erro de isolamento, duplicação ou integridade.
Rollback: desativar novos disparos/envios e voltar aos binários anteriores,
preservando tabelas, chaves, snapshots e documentos. Não apagar histórico nem
refazer pedidos com novas chaves. A migração não deve remover dados fiscais.

## 8. Observabilidade e sustentação

Fila exibe bloqueios e estados independentes de autorização fiscal e upload.
Auditoria registra consentimento, revisão, emissão e envio; logs operacionais
identificam trabalho/tipo de falha sem PII. Sucesso é NF autorizada com XML
verificado e estado Amazon confirmado. Em 403, conferir papéis restritos e usar
XML manual. Em timeout/NotFound, consultar a mesma chave; após a janela segura,
exigir reconciliação humana. Falha que afete emissão é incidente fiscal P1.

## 9. Mudança, comunicação e treinamento

Operação: no CorePet, Integrações → EcommerceAI → NF-e de pedidos Amazon;
autorizar escopos, cadastrar conta e mapear SKUs. No EcommerceAI, Integrações →
Amazon · Notas fiscais pelo CorePet; configurar a mesma empresa/política e ativar.
Revisar pendências pela fila. “NF autorizada” e “Aceito pela Amazon” são etapas
distintas. Treinamento necessário: configuração inicial e tratamento das exceções.

## 10. Fechamento

Código e testes locais preparados para revisão técnica. Publicação, homologação
com a conta real e ativação dependem da autorização explícita de Lucas. A ficha
e o contrato não autorizam comandos em produção nem concedem acesso novo.
