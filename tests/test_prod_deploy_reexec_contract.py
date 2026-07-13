from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_producao_seguro.sh"


def test_deploy_reexecutes_new_script_after_git_update_once():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    condition = '[[ "$HEAD_BEFORE" != "$HEAD_AFTER" && "$DEPLOY_REEXECUTED" != "1" ]]'
    assert condition in script
    assert "DEPLOY_REEXECUTED=1" in script
    assert 'bash "$APP_DIR/scripts/deploy_producao_seguro.sh"' in script
    assert script.index(condition) < script.index(
        'changed_files="$(git diff --name-only "$HEAD_BEFORE" "$HEAD_AFTER"'
    )


def test_deploy_reexec_preserves_original_release_context():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'DEPLOY_STARTED_AT="${DEPLOY_STARTED_AT:-' in script
    assert 'DEPLOY_ORIGINAL_HEAD="$HEAD_BEFORE"' in script
    assert 'DEPLOY_ORIGINAL_BACKUP_DIR="$backup_dir"' in script
    assert 'HEAD_BEFORE="$DEPLOY_ORIGINAL_HEAD"' in script
    assert 'backup_dir="$DEPLOY_ORIGINAL_BACKUP_DIR"' in script
    assert 'git cat-file -e "$DEPLOY_ORIGINAL_HEAD^{commit}"' in script
    assert '"$APP_DIR"/backups/deploy_*' in script


def test_reexecuted_deploy_does_not_overwrite_predeploy_evidence():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    reexec_branch = script.index('if [[ "$DEPLOY_REEXECUTED" == "1" ]]')
    fresh_branch = script.index("else", reexec_branch)
    branch_end = script.index("\nfi", fresh_branch)
    fresh_setup = script[fresh_branch:branch_end]

    assert "head_before.txt" in fresh_setup
    assert "docker_ps_before.txt" in fresh_setup
    assert "head_before.txt" not in script[reexec_branch:fresh_branch]
