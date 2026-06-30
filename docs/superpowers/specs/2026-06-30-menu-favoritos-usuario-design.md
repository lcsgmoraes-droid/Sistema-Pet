# Favoritos Do Menu Por Usuario

## Objetivo

Permitir que cada usuario marque atalhos favoritos no menu lateral do Sistema Pet e veja esses atalhos em qualquer computador ao entrar com o mesmo usuario.

## Escopo

- Adicionar favoritos para itens principais e subitens do menu lateral.
- Mostrar os favoritos em uma faixa discreta no topo da area principal.
- Persistir os favoritos no backend por `tenant_id` e `user_id`.
- Respeitar permissoes e modulos: favorito sem acesso nao deve aparecer.
- Limitar a lista a 8 favoritos por usuario.

## Arquitetura

O backend tera uma tabela `usuario_menu_favoritos` com uma linha por favorito. Cada registro guarda `tenant_id`, `user_id`, `path`, `label`, `icon_key` e `position`. As rotas autenticadas em `/usuarios/me/menu-favoritos` carregam e salvam a lista completa do usuario atual.

No frontend, o `Layout` carrega os favoritos apos montar o menu permitido. O `SidebarMenu` recebe uma funcao para favoritar/desfavoritar e exibe uma estrela pequena ao lado dos itens. A faixa superior mostra somente favoritos que continuam presentes no menu filtrado por permissao.

## Comportamento

- Clicar na estrela vazia adiciona o item aos favoritos.
- Clicar na estrela preenchida remove o item dos favoritos.
- A ordem inicial segue a ordem de clique.
- Ao exceder 8 favoritos, o frontend bloqueia a inclusao e informa o usuario.
- Se a API falhar, o sistema mantem o menu funcionando e mostra um aviso simples.
- Se o usuario entrar em outro PC, a lista sera lida do backend.

## Testes

- Backend: contrato das rotas e modelo para validar persistencia por usuario/tenant e limite de 8.
- Frontend: testes de utilitarios do menu para montar favoritos visiveis, alternar itens e bloquear excesso.
- Build: `npm run build` no frontend, por haver alteracao em `frontend/src`.
