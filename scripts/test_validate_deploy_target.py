from __future__ import annotations

import unittest

from validate_deploy_target import DeployTargetError, validate_target


class ValidateDeployTargetTests(unittest.TestCase):
    def test_accepts_host_that_serves_public_domain(self) -> None:
        result = validate_target(
            domain="corepet.com.br",
            local_ips={"179.198.116.52", "172.18.0.1"},
            resolved_ips={"179.198.116.52"},
            health_url="https://corepet.com.br/api/health",
        )

        self.assertEqual(result.matched_ips, {"179.198.116.52"})

    def test_rejects_host_different_from_public_domain(self) -> None:
        with self.assertRaisesRegex(DeployTargetError, "servidor errado"):
            validate_target(
                domain="corepet.com.br",
                local_ips={"192.241.150.121", "172.18.0.1"},
                resolved_ips={"179.198.116.52"},
                health_url="https://corepet.com.br/api/health",
            )

    def test_rejects_health_check_for_another_domain(self) -> None:
        with self.assertRaisesRegex(DeployTargetError, "health check"):
            validate_target(
                domain="corepet.com.br",
                local_ips={"179.198.116.52"},
                resolved_ips={"179.198.116.52"},
                health_url="https://mlprohub.com.br/api/health",
            )


if __name__ == "__main__":
    unittest.main()
