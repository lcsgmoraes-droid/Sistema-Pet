---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — comissoes_configuracao

Ver [[Cliente]], [[comissoes_itens]], [[comissoes_vendas]].

## Definição
Configuração de percentual de comissão por categoria/produto/serviço e funcionário.

## Confirmado no código
- Modelo ORM: `comissoes_models.py:648-683` (`ComissaoConfiguracao`). Não herda `BaseTenantModel` — usa mixin `TenantScoped` + `Base` cru (docstring própria explica isso).
- Colunas: referência polimórfica `tipo` ('categoria'/'produto'/'servico') + `referencia_id` (Integer sem FK — polimorfismo intencional), `percentual`, `tipo_calculo`, flags de desconto (`desconta_taxa_cartao`, `desconta_impostos`, `desconta_custo_entrega`).
- FK de saída: `funcionario_id → clientes.id` — funcionários são modelados como [[Cliente]], mesmo padrão de fornecedores.

## Relacionamentos
- FK de saída: `funcionario_id → clientes.id`.
- `referencia_id` referencia informalmente categoria/produto/serviço conforme `tipo`.

## Utilizado por
- ⚠️ **A classe ORM não é usada em nenhuma rota/service confirmado.** O acesso real de produção à tabela `comissoes_configuracao` é feito via SQL cru pela classe `ComissoesConfig` (métodos estáticos em `comissoes_models.py:46-411`, usada em `comissoes_configuracoes_routes.py`, `comissoes_config_service.py`, `comissoes_diagnostico_routes.py`, `comissoes_parceiros_routes.py`, `comissoes_demonstrativo_admin_routes.py`).

## Não identificado
- 🟠 Duas camadas de acesso paralelas para a mesma tabela: a ORM (schema "oficial") parece nunca ser chamada; todo acesso real passa por SQL manual via `ComissoesConfig`. Vale decidir com o time se a classe ORM deve ser removida ou se o acesso deveria migrar pra ela.
