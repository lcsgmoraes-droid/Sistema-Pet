# Teste direto do SentimentAnalyzer
import sys
sys.path.insert(0, r"c:\Users\Lucas\OneDrive\Área de Trabalho\Programa\Sistema Pet\backend")

print("\n" + "="*50)
print("TESTE SENTIMENT ANALYZER")
print("="*50)

try:
    from app.whatsapp.sentiment import SentimentAnalyzer
    print("\n✓ Import OK")
    
    analyzer = SentimentAnalyzer()
    print("✓ Instância criada")
    
    result = analyzer.analyze("Estou muito irritado!")
    print(f"\n✓ Análise OK")
    print(f"  Score: {result['score']}")
    print(f"  Label: {result['label']}")
    print(f"  Emotions: {result['emotions']}")
    print(f"  Should handoff: {result['should_handoff']}")
    
except Exception as e:
    print(f"\n✗ ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
