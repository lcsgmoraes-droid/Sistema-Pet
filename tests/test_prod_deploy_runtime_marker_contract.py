from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_producao_seguro.sh"


def test_deploy_tracks_the_commit_served_by_the_runtime():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert (
        'RUNTIME_RELEASE_MARKER="${RUNTIME_RELEASE_MARKER:-${RUNTIME_DIST}/.release-commit}"'
        in script
    )
    assert (
        'runtime_release_commit="$(tr -d \'[:space:]\' <"$RUNTIME_RELEASE_MARKER")"'
        in script
    )
    assert '[[ "$runtime_release_mismatch" == "0" ]]' in script
    assert 'printf \'%s\\n\' "$HEAD_AFTER" >"$NEXT_RUNTIME_RELEASE_MARKER"' in script


def test_noop_deploy_updates_marker_and_interrupted_deploy_forces_rebuild():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'printf \'%s\\n\' "$HEAD_AFTER" >"$RUNTIME_RELEASE_MARKER"' in script
    assert (
        'if [[ "$HEAD_BEFORE" == "$HEAD_AFTER" || "$runtime_release_commit" != "$HEAD_BEFORE" ]]; then'
        in script
    )
    assert (
        "Artefato publicado nao corresponde ao commit atual; rebuild obrigatorio"
        in script
    )
