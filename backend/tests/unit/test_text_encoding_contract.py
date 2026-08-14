from pathlib import Path
import re


APP_ROOT = Path(__file__).resolve().parents[2] / "app"
ALLOWED_RECOVERY_FILES = {"estoque_saida_full/parsers.py"}
BROKEN_TEXT = re.compile(
    r"Ã[\u0080-\u00bfƒŠŒŽšœžŸ]"
    r"|ð[\u0080-\u00bfƒŠŒŽšœžŸ]"
    r"|â[€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]"
    r"|�"
    r"|[A-Za-zÀ-ÿ]\?{2,}[A-Za-zÀ-ÿ]"
)


def test_backend_nao_contem_textos_com_codificacao_quebrada():
    falhas = []
    for path in APP_ROOT.rglob("*.py"):
        relative = path.relative_to(APP_ROOT).as_posix()
        if relative in ALLOWED_RECOVERY_FILES:
            continue

        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if BROKEN_TEXT.search(line):
                falhas.append(f"{relative}:{line_number}")

    assert not falhas, "Textos com codificação suspeita:\n" + "\n".join(falhas)
