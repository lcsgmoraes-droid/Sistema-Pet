# Painel de administração (adm)

Projeto de frontend separado em `adm/` (futuro `adm.corepet.com.br`), que vai aposentar o OPS.
Detalhes de uso, segurança e deploy: `adm/README.md`.

- Backend de login: `backend/app/adm_auth.py` (`/adm/auth/*`), tabela `platform_admins`
  (colunas `painel_adm_ativo`, `must_change_password`; migração `zzzzzf20261029a1`).
- Gestão de acessos (sem tela de cadastro): `backend/scripts/criar_admin_plataforma.py`.
- Lojas e módulos: `/admin/lojas` (ver `docs/OPS_LOJAS.md`).
- Testes: `backend/tests/unit/test_adm_auth.py`; frontend `cd adm && npm test`.
- Produção (DNS, nginx, variáveis `ADM_*`) ainda não feita: exige autorização.
