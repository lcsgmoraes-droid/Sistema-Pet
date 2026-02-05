import os
import re

def fix_logger_imports(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'from app.core.logger import' in content:
                        new_content = content.replace('from app.core.logger import', 'from app.utils.logger import')
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        count += 1
                        print(f"✅ {filepath}")
                except Exception as e:
                    print(f"❌ Erro em {filepath}: {e}")
    
    print(f"\n✅ {count} arquivos corrigidos!")

if __name__ == "__main__":
    fix_logger_imports("app")
