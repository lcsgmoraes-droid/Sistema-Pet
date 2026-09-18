---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — vet_consultas

Ver [[Pet]], [[Cliente]], [[vet_agendamentos]], [[vet_prescricoes]], [[vet_exames]], [[vet_procedimentos_consulta]], [[vet_fotos_clinicas]].

## Definição
Prontuário central do módulo veterinário — sinais vitais, anamnese, exame físico, diagnóstico (com tradução simplificada por IA) e conduta, com hash de imutabilidade ao finalizar.

## Confirmado no código
- Modelo: `veterinario_models.py:305-402` (`ConsultaVet`).
- Colunas: sinais vitais (temperatura, FC, FR, TPC, mucosas, hidratação, dor 0-10, SpO2, pressão, glicemia), anamnese, exame físico, diagnóstico (+ `diagnostico_simples` traduzido por IA), conduta, `asa_score` (1-5), `hash_prontuario` (SHA-256 ao finalizar), `finalizado_em`.
- `status`: em_andamento | finalizada | cancelada.
- Relationships com `cascade="all, delete-orphan"` para `prescricoes`, `exames`, `procedimentos`, `fotos_clinicas` — apagar a consulta apaga todos os registros filhos.
- Criada a partir do agendamento (ou avulsa) com validação de que `pet_id` pertence ao `cliente_id` informado.

## Relacionamentos
- FKs de saída: `pet_id → pets.id`, `cliente_id → clientes.id` (tutor), `veterinario_id → clientes.id`, `user_id → users.id`, `finalizado_por_id → users.id`.
- Referenciada por (hub — muitas): [[vet_agendamentos]]`.consulta_id`/`.consulta_origem_id`, [[vet_prescricoes]]`.consulta_id`, [[vet_vacinas_registros]]`.consulta_id`, [[vet_exames]]`.consulta_id`, [[vet_internacoes]]`.consulta_id`, [[vet_orcamentos]]`.consulta_id`, [[vet_peso_registros]]`.consulta_id`, [[vet_fotos_clinicas]]`.consulta_id`, [[vet_procedimentos_consulta]]`.consulta_id`.

## Utilizado por
- `veterinario_consultas_routes.py` (CRUD completo do prontuário).

## Não identificado
- Nada notável — é o hub confirmado do módulo clínico.
