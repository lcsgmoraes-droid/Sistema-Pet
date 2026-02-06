"""
Script para Configurar Google Maps API Key
"""

import os
from pathlib import Path

def configurar_google_maps():
    """Configura Google Maps API Key em todos os arquivos necessários"""
    
    print("=" * 70)
    print("🗺️  CONFIGURAR GOOGLE MAPS API KEY")
    print("=" * 70)
    print()
    
    # Solicitar chave
    print("📋 Cole sua Google Maps API Key:")
    print("   (Começa com 'AIza...')")
    print()
    api_key = input("   API Key: ").strip()
    
    if not api_key:
        print("\n❌ Nenhuma chave fornecida!")
        return False
    
    if not api_key.startswith("AIza"):
        print("\n⚠️  Aviso: A chave não começa com 'AIza'. Tem certeza?")
        confirma = input("   Continuar? (s/n): ").strip().lower()
        if confirma != 's':
            return False
    
    # Arquivos para atualizar
    base_path = Path(__file__).parent
    arquivos = [
        base_path / "backend" / ".env",
        base_path / ".env.development",
        base_path / ".env.staging",
        base_path / ".env.production",
        base_path / ".env.local-prod",
        base_path / "docker-compose.development.yml",
    ]
    
    print(f"\n🔄 Atualizando {len(arquivos)} arquivos...")
    print()
    
    atualizados = 0
    for arquivo in arquivos:
        if not arquivo.exists():
            print(f"   ⏭️  Pulando {arquivo.name} (não existe)")
            continue
        
        try:
            # Ler conteúdo
            with open(arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Atualizar linha da API key
            linhas = conteudo.split('\n')
            modificado = False
            
            for i, linha in enumerate(linhas):
                if linha.strip().startswith('GOOGLE_MAPS_API_KEY'):
                    if '=' in linha:
                        linhas[i] = f'GOOGLE_MAPS_API_KEY={api_key}'
                        modificado = True
                    elif linha.strip().startswith('- GOOGLE_MAPS_API_KEY'):
                        # Docker compose format
                        linhas[i] = f'      - GOOGLE_MAPS_API_KEY={api_key}'
                        modificado = True
            
            if modificado:
                # Salvar
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(linhas))
                print(f"   ✅ {arquivo.name}")
                atualizados += 1
            else:
                print(f"   ⏭️  {arquivo.name} (não encontrou linha GOOGLE_MAPS_API_KEY)")
                
        except Exception as e:
            print(f"   ❌ Erro ao atualizar {arquivo.name}: {e}")
    
    print()
    print("=" * 70)
    print(f"✅ Concluído! {atualizados} arquivo(s) atualizado(s)")
    print("=" * 70)
    print()
    print("🔄 Próximos passos:")
    print("   1. Reinicie o backend: docker restart petshop-backend")
    print("   2. Acesse 'Entregas em Aberto' e veja as rotas otimizadas!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        configurar_google_maps()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
