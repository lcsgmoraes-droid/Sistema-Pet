from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployTargetContractTests(unittest.TestCase):
    def test_deploy_validates_dns_before_updating_code(self) -> None:
        source = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(encoding="utf-8")

        validation_position = source.index("validate_deploy_target.py")
        update_position = source.index('mark_step "atualizar_codigo"')

        self.assertLess(validation_position, update_position)
        self.assertIn('DEPLOY_PUBLIC_DOMAIN="${DEPLOY_PUBLIC_DOMAIN:-corepet.com.br}"', source)
        self.assertIn("release-commit.txt", source)
        self.assertIn("validar_commit_publico", source)

    def test_operational_docs_use_domain_instead_of_stale_ip(self) -> None:
        instructions = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "PRODUCAO_DEPLOY_SSH.md").read_text(encoding="utf-8")

        for source in (instructions, guide):
            self.assertIn("petdeploy@corepet.com.br", source)
            self.assertNotIn("petdeploy@192.241.150.121", source)

    def test_remote_launcher_and_root_wrapper_validate_the_domain(self) -> None:
        launcher = (ROOT / "scripts" / "deploy_producao_remoto.ps1").read_text(
            encoding="utf-8"
        )
        wrapper = (ROOT / "scripts" / "install_prod_deploy_wrapper.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn('[string]$Dominio = "corepet.com.br"', launcher)
        self.assertIn('"petdeploy@$Dominio"', launcher)
        self.assertIn('domain = "corepet.com.br"', wrapper)
        self.assertLess(wrapper.index("socket.getaddrinfo"), wrapper.index("cd /opt/petshop"))


if __name__ == "__main__":
    unittest.main()
