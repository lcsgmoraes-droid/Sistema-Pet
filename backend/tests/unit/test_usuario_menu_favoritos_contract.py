from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_usuario_menu_favoritos_model_and_migration_contract():
    model = read_repo("backend/app/usuario_menu_favoritos_models.py")
    migration = read_repo(
        "backend/alembic/versions/uv20260630a1_create_usuario_menu_favoritos.py"
    )

    assert "__tablename__ = \"usuario_menu_favoritos\"" in model
    assert "class UsuarioMenuFavorito(BaseTenantModel)" in model
    assert "ForeignKey(\"users.id\")" in model
    assert "path = Column(String(255)" in model
    assert "label = Column(String(120)" in model
    assert "icon_key = Column(String(80)" in model
    assert "position = Column(Integer" in model
    assert "UniqueConstraint(" in model
    assert "\"tenant_id\"," in model
    assert "\"user_id\"," in model
    assert "\"path\"," in model

    assert "op.create_table(" in migration
    assert "\"usuario_menu_favoritos\"" in migration
    assert "sa.ForeignKeyConstraint([\"user_id\"], [\"users.id\"]" in migration
    assert "uq_usuario_menu_favoritos_tenant_user_path" in migration
    assert "ix_usuario_menu_favoritos_tenant_user_position" in migration


def test_usuario_menu_favoritos_routes_contract():
    routes = read_repo("backend/app/usuarios_routes.py")
    main_routers = read_repo("backend/app/main_routers.py")

    assert "UsuarioMenuFavorito" in routes
    assert "MAX_MENU_FAVORITOS = 8" in routes
    assert "@router.get(\"/me/menu-favoritos\"" in routes
    assert "def listar_meus_menu_favoritos" in routes
    assert "@router.put(\"/me/menu-favoritos\"" in routes
    assert "def salvar_meus_menu_favoritos" in routes
    assert "MenuFavoritosPayload" in routes
    assert "len(payload.items) > MAX_MENU_FAVORITOS" in routes
    assert "db.query(UsuarioMenuFavorito)" in routes
    assert "UsuarioMenuFavorito(" in routes

    assert "from app.usuario_menu_favoritos_models import UsuarioMenuFavorito" in main_routers
