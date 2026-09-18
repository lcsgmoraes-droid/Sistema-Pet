---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Banho e Tosa

Ver [[Funcionalidades]], [[Pet]]. Fonte pré-existente aproveitada: `docs/BLUEPRINT_BANHO_TOSA_ENTERPRISE_2026-04-24.md`, `docs/PENTE_FINO_VETERINARIO_BANHO_TOSA_2026-04-24.md`.

## Identificação
- **Menu:** Atendimento → Banho & Tosa (submenu: Serviços, Parâmetros, Recursos, Agenda, Fila do dia, Pacotes, Reagendar, Taxi dog, Relatórios)
- **Rota frontend:** `/banho-tosa`
- **Módulo de rota:** `frontend/src/app/routes/BathGroomingRoutes.jsx`
- **Módulo de plano (SaaS):** habilitado por tenant via flag `banho_tosa` (ver [[Arquitetura#Módulos ligáveis por tenant]])

## Objetivo
Gestão completa do serviço de banho e tosa: agenda com capacidade, execução por etapas, pacotes de crédito, recorrência, avaliações, custos reais e taxi dog (busca/entrega do pet).

## Backend (confirmado — ~30 arquivos `banho_tosa_*`)
`banho_tosa_routes.py`, `banho_tosa_api/` (rotas), `banho_tosa_agenda_capacity.py`, `banho_tosa_agenda_slots.py`, `banho_tosa_custos_reais.py`, `banho_tosa_pacotes.py`, `banho_tosa_retornos.py`, `banho_tosa_taxi_fluxo.py`, `banho_tosa_fechamento.py` (fechamento financeiro do serviço), `banho_tosa_fotos_storage.py`.

## Banco de dados
`backend/app/banho_tosa_model_parts/*`: `BanhoTosaAgendamento`, `Atendimento`, `Etapa`, `Foto`, `Pacote`(`Credito`/`Movimento`), `Recorrencia`, `Avaliacao`, `Configuracao`, `Recurso`, `Servico`, `PrecoServico`, `CustoSnapshot`, `TaxiDog`, `RetornoTemplate`.

## Integrações
Notificações de agendamento ([[WhatsApp-WAHA]], potencialmente).

## Dependências
[[Pet]] (sujeito do serviço), [[Cliente]] (tutor), [[PDV-Vendas]] (fechamento financeiro do serviço vira venda/lançamento).

## Não identificado
- ⚠️ Detalhe de armazenamento de fotos do atendimento (`banho_tosa_fotos_storage.py`) não foi auditado quanto a segurança de upload nesta rodada — ver [[API-Security]] (seção de uploads cobre produto e XML, não fotos de banho-tosa explicitamente).
