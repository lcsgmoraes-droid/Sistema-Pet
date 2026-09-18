---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — usuario_menu_favoritos

Ver [[Usuario]].

## Definição
Item do menu lateral favoritado por um usuário (feature usada no menu documentado em `SidebarMenu.jsx`, ver estrela de favorito).

## Confirmado no código
- Modelo: `usuario_menu_favoritos_models.py:9-34` (`UsuarioMenuFavorito`).
- Colunas: `path` (rota do menu), `label`, `icon_key` (opcional), `position` (ordenação manual).
- `UniqueConstraint(tenant_id, user_id, path)`, índice composto `(tenant_id, user_id, position)`.

## Relacionamentos
- FK de saída: `user_id → users.id` (relationship unidirecional, sem `back_populates` no lado `User`).

## Utilizado por
- `usuarios_routes.py` (listagem ordenada por `position`, criação — rota de "favoritar item do menu").

## Não identificado
- Nada notável.
