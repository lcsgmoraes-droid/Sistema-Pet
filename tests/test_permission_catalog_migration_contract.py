import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "zxd20260826a1_seed_permission_catalog.py"
)
MODULE_ACCESS_MIGRATION = (
    ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "zxm20260828a1_module_access_permissions.py"
)
APP_ROOT = ROOT / "backend" / "app"
DEFAULT_ROLES = APP_ROOT / "services" / "default_roles_service.py"
PERMISSION_PATTERN = re.compile(
    r'(?:require_permission|require_permission_dependency)\(\s*["\']([^"\']+)["\']'
)


def _catalog() -> dict[str, str]:
    catalog = {}
    for migration, variable_name in (
        (MIGRATION, "PERMISSION_CATALOG"),
        (MODULE_ACCESS_MIGRATION, "MODULE_PERMISSIONS"),
    ):
        tree = ast.parse(migration.read_text(encoding="utf-8"))
        assignment = next(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == variable_name
                for target in node.targets
            )
        )
        catalog.update(dict(ast.literal_eval(assignment.value)))
    return catalog


def _permission_literals(source: str) -> set[str]:
    literals = set(PERMISSION_PATTERN.findall(source))
    literals.update(
        re.findall(
            r'["\']([a-z_]+\.(?:criar|editar|excluir|visualizar|manage))["\']',
            source,
        )
    )
    return literals


def _all_dotted_literals(source: str) -> set[str]:
    return set(re.findall(r'["\']([a-z_]+\.[a-z_]+)["\']', source))


def test_permission_catalog_is_in_the_official_alembic_chain():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxd20260826a1"' in source
    assert 'down_revision = "zxc20260826a1"' in source
    assert "ON CONFLICT (code) DO UPDATE" in source
    assert "EXCLUDED.description" in source


def test_permission_catalog_covers_default_roles_and_protected_routes():
    catalog_codes = set(_catalog())
    required_codes = _all_dotted_literals(DEFAULT_ROLES.read_text(encoding="utf-8"))

    for path in APP_ROOT.rglob("*.py"):
        required_codes.update(_permission_literals(path.read_text(encoding="utf-8")))

    assert required_codes
    assert required_codes <= catalog_codes


def test_permission_catalog_has_unique_codes_and_meaningful_descriptions():
    catalog = _catalog()
    source = MIGRATION.read_text(encoding="utf-8")
    catalog_literal = ast.literal_eval(
        next(
            node.value
            for node in ast.parse(source).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "PERMISSION_CATALOG"
                for target in node.targets
            )
        )
    )

    module_catalog_literal = ast.literal_eval(
        next(
            node.value
            for node in ast.parse(
                MODULE_ACCESS_MIGRATION.read_text(encoding="utf-8")
            ).body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "MODULE_PERMISSIONS"
                for target in node.targets
            )
        )
    )

    assert len(catalog) == len(catalog_literal) + len(module_catalog_literal)
    assert all("." in code for code in catalog)
    assert all(len(description.strip()) >= 8 for description in catalog.values())


def test_e2e_permissions_are_part_of_a_fresh_database():
    catalog_codes = set(_catalog())

    assert {
        "clientes.criar",
        "produtos.criar",
        "produtos.editar",
        "produtos.visualizar",
        "vendas.criar",
        "vendas.visualizar",
    } <= catalog_codes
