---
tipo: eixo
atualizado: 2026-09-12
---

# Funcionalidades

Um dos 4 grandes eixos. Ver [[README]]. Mapeamento a partir do menu real do frontend (`frontend/src/components/layout/menuStructure.js` + `menuConfig.js`, confirmado por agente de exploração), não presumido.

## Como o menu é montado (confirmado)

- Itens definidos em `menuConfig.js` (`createLayoutMenuItems`), ordenados/agrupados por `menuStructure.js` (`applyLayoutMenuStructure`), renderizados em `SidebarMenu.jsx`.
- Cada item some do menu se a **permissão** do usuário não cobrir OU se o **módulo** correspondente não estiver contratado pelo tenant (`ModulosContext`) — ver [[Autorizacao]].
- Rotas reais ficam agrupadas em `frontend/src/app/routes/*.jsx`, todas carregadas via lazy-loading (`lazyPages.js`).

## Mapa do menu → documento

### Visão geral
| Item | Rota | Doc |
|---|---|---|
| Dashboard | `/dashboard` | ❓ sem doc dedicado — dashboard agrega dados de várias funcionalidades |
| Lembretes | `/lembretes` | ❓ sem doc dedicado (ligado a [[Produto]] — recorrência) |

### Atendimento
| Item | Rota | Doc |
|---|---|---|
| Pessoas (Clientes) | `/clientes` | [[Cliente]] (entidade); funcionalidade sem doc próprio de tela — ver [[Pendencias]] |
| Pets | `/pets` | [[Pet]] |
| Veterinário | `/veterinario` | [[Veterinario]] |
| Banho & Tosa | `/banho-tosa` | [[Banho-e-Tosa]] |
| Calculadora de Ração | `/calculadora-racao` | ❓ sem doc dedicado |

### Vendas e relacionamento
| Item | Rota | Doc |
|---|---|---|
| PDV/Vendas | `/pdv` | [[PDV-Vendas]] |
| E-commerce | `/ecommerce` | [[E-commerce]] |
| Campanhas | `/campanhas` | [[Campanhas]] |
| Bling | `/vendas/bling` | [[Bling]] |
| Entregas | `/entregas` | [[Entregas]] |

### Estoque e suprimentos
| Item | Rota | Doc |
|---|---|---|
| Produtos/Estoque | `/produtos`, `/estoque` | [[Produtos-Estoque]] |
| Compras | `/compras` | [[Compras]] |
| NF de Saída | `/notas-fiscais/saida` | ver [[Fiscal-IntNFe-SEFAZ]] |

### Financeiro
| Item | Rota | Doc |
|---|---|---|
| Financeiro | `/financeiro` | [[Financeiro]] |
| Comissões | `/comissoes` | [[Comissoes]] |

### Gestão
| Item | Rota | Doc |
|---|---|---|
| Alertas do gestor | `/alertas-gestor` | ❓ sem doc dedicado |
| Cadastros | `/cadastros` | ❓ sem doc dedicado (cargos, departamentos, marcas, categorias, bancos, formas de pagamento etc. — cadastros auxiliares) |
| RH | `/rh` | ❓ sem doc dedicado (funcionários) |
| IA | `/ia` | ver [[OpenAI-IA]] (chat, fluxo de caixa preditivo, bot WhatsApp, comparador de rações) |
| Administração | `/admin` | ver [[Role-Permission]] (usuários, roles & permissões, LGPD) |
| Configurações | `/configuracoes` | ❓ sem doc dedicado (fiscal, parâmetros gerais, grupos de empresas, entregas, custo da moto, estoque, integrações) |

### Painel interno da plataforma (não é módulo de tenant)
`/ops/*` — backoffice da própria CorePet (staff), autenticação separada (`PlatformAuthContext`). ❓ Sem doc dedicado nesta fase — ver [[Asaas]] para o billing que esse painel provavelmente gerencia.

## Autenticação e controle de acesso no frontend (confirmado)

- Guard de rota: `ProtectedRoute.jsx` (permissão obrigatória, qualquer uma, ou todas).
- Guard de item de menu: `Layout.jsx` (`hasPermission`/`hasAnyPermission`), cruzado com módulo ativo do tenant.
- Cliente HTTP central: `frontend/src/api.js` — Bearer token, refresh automático em 401, logout em falha de refresh.
- Detalhe completo em [[Autorizacao]] e [[Autenticacao]].

## Stores de estado (confirmado)

Apenas uma store Zustand real: `frontend/src/stores/whatsappStore.ts` (atendimento WhatsApp). Todo o resto do estado global usa React Context: `AuthContext`, `PlatformAuthContext`, `ModulosContext`, `ThemeContext`.

## Cobertura desta análise

Das ~25 áreas de menu identificadas, **10 têm documento de funcionalidade dedicado** nesta primeira fase (os módulos mais centrais e mais referenciados pelas integrações). As demais estão listadas acima com rota confirmada, mas sem aprofundamento de frontend/backend/segurança específico — ver [[Matriz-de-Cobertura]] para a visão tabular completa e [[Pendencias]] para o que falta detalhar.

## Não identificado

- Nome interno do pacote frontend ainda é `petshop-pro-frontend` (`frontend/package.json`), enquanto a marca do produto já é "CorePet" (`index.html`) — rebranding em andamento/parcial, confirmado pelo agente de frontend.
