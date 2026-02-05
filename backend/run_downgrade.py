import subprocess
import sys

# Executar downgrade via subprocess para evitar problemas de import
result = subprocess.run(
    ["alembic", "downgrade", "cb4a6a716db2"],
    cwd=r"C:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend",
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
    
sys.exit(result.returncode)
