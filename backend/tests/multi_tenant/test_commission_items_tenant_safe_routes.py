import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ROUTE_FILES = (
    PROJECT_ROOT / "app" / "comissoes_avancadas_routes.py",
    PROJECT_ROOT / "app" / "comissoes_diagnostico_routes.py",
    PROJECT_ROOT / "app" / "routers" / "relatorios_comissoes.py",
)


def _string_parts(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_string_parts(value) for value in node.values)
    if isinstance(node, ast.FormattedValue):
        return ""
    return ""


def _direct_db_execute_calls_touching_commission_items(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assigned_sql: dict[str, str] = {}
    unsafe_lines: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            sql = _string_parts(node.value)
            if not sql:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned_sql[target.id] = sql

        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "execute":
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "db":
            continue
        if not node.args:
            continue

        first_arg = node.args[0]
        sql = ""
        if (
            isinstance(first_arg, ast.Call)
            and getattr(first_arg.func, "id", None) == "text"
        ):
            text_arg = first_arg.args[0] if first_arg.args else None
            if isinstance(text_arg, ast.Name):
                sql = assigned_sql.get(text_arg.id, "")
            elif text_arg is not None:
                sql = _string_parts(text_arg)
        elif isinstance(first_arg, ast.Name):
            sql = assigned_sql.get(first_arg.id, "")

        if "comissoes_itens" in sql.lower():
            unsafe_lines.append(node.lineno)

    return unsafe_lines


def test_commission_item_routes_do_not_use_direct_raw_sql():
    failures = {
        path.relative_to(PROJECT_ROOT).as_posix(): lines
        for path in ROUTE_FILES
        if (lines := _direct_db_execute_calls_touching_commission_items(path))
    }

    assert failures == {}
