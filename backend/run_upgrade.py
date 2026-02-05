import subprocess
import sys
import os

os.chdir(r"C:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

print("=" * 60)
print("PASSO 2: APLICANDO MIGRATION efc4e939587f")
print("=" * 60)

result = subprocess.run(
    ["alembic", "upgrade", "head"],
    capture_output=True,
    text=True,
    timeout=120
)

print(result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

if result.returncode == 0:
    print("\n" + "=" * 60)
    print("✅ UPGRADE CONCLUÍDO COM SUCESSO")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("❌ ERRO NO UPGRADE")
    print("=" * 60)

sys.exit(result.returncode)
