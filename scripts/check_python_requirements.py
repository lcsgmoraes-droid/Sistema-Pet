"""Fail when the active Python environment diverges from a requirements file."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys

from packaging.requirements import InvalidRequirement, Requirement


def load_requirements(path: Path) -> list[Requirement]:
    requirements: list[Requirement] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        try:
            requirements.append(Requirement(line))
        except InvalidRequirement as exc:
            raise ValueError(f"{path}:{line_number}: requisito invalido: {line}") from exc
    return requirements


def find_divergences(requirements: list[Requirement]) -> list[str]:
    divergences: list[str] = []
    for requirement in requirements:
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = version(requirement.name)
        except PackageNotFoundError:
            divergences.append(f"{requirement.name}: nao instalado ({requirement})")
            continue
        if requirement.specifier and not requirement.specifier.contains(
            installed, prereleases=True
        ):
            divergences.append(
                f"{requirement.name}: instalado {installed}, esperado {requirement.specifier}"
            )
    return divergences


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: check_python_requirements.py <requirements.txt>", file=sys.stderr)
        return 2

    requirements_path = Path(sys.argv[1]).resolve()
    divergences = find_divergences(load_requirements(requirements_path))
    if divergences:
        print("Ambiente Python fora de sincronia:", file=sys.stderr)
        for divergence in divergences:
            print(f"- {divergence}", file=sys.stderr)
        return 1

    print(f"Ambiente Python sincronizado: {requirements_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
