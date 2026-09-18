---
tipo: integracao
atualizado: 2026-09-12
---

# Integração — Fiscal (SEFAZ + IntNFe)

Parte de [[Integracoes]]. Ver [[Produtos-Estoque]]. Fontes pré-existentes usadas e validadas contra o código: `docs/ATIVACAO_FISCAL_INTNFE.md`, `docs/FISCAL_INTNFE_PILOTO_HOMOLOGACAO.md`, `docs/GUIA_CONFIGURACAO_FISCAL_NFE_NFCE.md`, `docs/ESTUDO_BLING_E_ESTRUTURA_FISCAL_COREPET.md`.

⚠️ Estas são **duas integrações fiscais distintas** que coexistem no código. A relação exata entre elas (legado vs. novo, ou complementares por função) não está documentada explicitamente em nenhum docstring — ver [[Pendencias]].

## 1. SEFAZ (consulta/importação de XML de NF-e destinada ao CNPJ do tenant)

- **Arquivos:** `services/sefaz_service.py`, `services/sefaz_sync_coordinator.py`, `routes/sefaz_routes.py`.
- **Comunicação:** certificado digital A1 (PFX) + webservice SOAP/REST da SEFAZ, **polling por NSU** (não é webhook).
- **Autenticação:** `SEFAZ_ENABLED`, `SEFAZ_MODO`, `SEFAZ_CERT_PATH`, `SEFAZ_CERT_PASSWORD`, `SEFAZ_CNPJ`, `SEFAZ_UF`, `SEFAZ_TIMEOUT_SECONDS`, `SEFAZ_ULTIMO_NSU`.
- **Falhas/retry:** timeout 30s, retry adaptativo por tipo de erro.
- ⚠️ **Job de sincronização automática está inerte no código** (`_loop_sefaz_sync` retorna imediatamente, `main_background_jobs.py:251-260`) — preservado como histórico, não executa hoje. Ver [[Arquitetura]].
- **Finalidade:** importação de documentos fiscais destinados ao CNPJ (ex.: notas de entrada emitidas por fornecedores).

## 2. IntNFe (ativação do emitente próprio, CSC, numeração)

- **Arquivos:** `backend/app/intnfe/{certificate,client,csc,fiscal_profile,numbering,order_fiscal_context,repository,routes,service}.py`.
- **Comunicação:** REST com token de integrador.
- **Autenticação:** `INTNFE_INTEGRADOR_ID`/`INTNFE_INTEGRADOR_SECRET`, `INTNFE_ACTIVATION_ENABLED`, `INTNFE_ACTIVATION_TENANT_IDS`; `clientSecret` cifrado por empresa.
- **Webhook:** nenhum recebido.
- **Falhas/retry:** timeout 3s conexão / 15s leitura, **sem retry automático** (correção manual esperada).
- **Estado confirmado:** feature-flag desligada por padrão; trata-se da **ativação** do emissor (CSC, numeração, vínculo do certificado) — **emissão real de NF-e/NFC-e pelo IntNFe ainda não está implementada** no fluxo de venda, conforme `docs/ATIVACAO_FISCAL_INTNFE.md`.
- Histórico de homologação já documentado inclui correções pontuais anteriores (frete, `infIntermed`, CSC por ambiente) em `docs/DIAGNOSTICO_INTNFE_BLING_MULTICANAL_2026-09-11.md` e `docs/DIAGNOSTICO_INTNFE_NFE_HOMOLOGACAO_2026-09-09.md`.

## Fluxo geral (visão simplificada)
```text
[Ativação — IntNFe]                    [Emissão de NF real — via Bling, hoje]
Tenant configura certificado/CSC   +    Bling emite NF-e/NFC-e (ver [[Bling]])
     ↓                                        ↓
Vínculo fiscal ativo no CorePet         Documento fiscal sincronizado
```
❓ Este fluxo (emissão real via Bling enquanto IntNFe está em fase de ativação) é uma **inferência** baseada nos documentos e no código — necessita confirmação explícita do responsável sobre o roadmap de migração de emissão para IntNFe nativo.

## Dependências de funcionalidade
[[Produtos-Estoque]] (nota de entrada), PDV/Vendas (emissão de NFC-e via Bling hoje).

## Não identificado
- ❓ Prazo/critério para IntNFe passar a emitir NF-e/NFC-e diretamente, substituindo a dependência do Bling para esse fim.
