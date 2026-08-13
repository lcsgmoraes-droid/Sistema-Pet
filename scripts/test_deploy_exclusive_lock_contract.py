from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployExclusiveLockContractTests(unittest.TestCase):
    def test_deploy_uses_flock_instead_of_a_marker_file(self) -> None:
        source = (ROOT / "scripts" / "deploy_producao_seguro.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("require_cmd flock", source)
        self.assertIn("flock -n 9", source)
        self.assertIn('exec 9>"$DEPLOY_MUTEX_FILE"', source)
        self.assertIn("DEPLOY_LOCK_HELD", source)
        self.assertIn("DEPLOY_OWNS_LOCK", source)
        self.assertNotIn('rm -f "$DEPLOY_MUTEX_FILE"', source)


if __name__ == "__main__":
    unittest.main()
