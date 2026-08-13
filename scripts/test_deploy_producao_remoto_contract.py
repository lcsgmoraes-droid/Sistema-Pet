from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployProducaoRemotoContractTests(unittest.TestCase):
    def test_dns_result_is_always_an_array_before_indexing(self) -> None:
        source = (ROOT / "scripts" / "deploy_producao_remoto.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("$enderecos = @(", source)
        self.assertIn('"HostKeyAlias=$($enderecos[0])"', source)


if __name__ == "__main__":
    unittest.main()
