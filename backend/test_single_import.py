"""
Teste rápido: importar apenas 1 cliente específico para debug
"""
from importador_producao import ImportadorProducao

# Criar importador
imp = ImportadorProducao(
    database_url="postgresql://postgres:postgres@localhost:5433/petshop_dev",
    dry_run=False
)

# Ler CSV
registros = imp.ler_csv('glo_pessoa.csv', limite=25)

# Pegar apenas o registro 21 (primeiro após os 20 duplicados)
registro = registros[20]

print("\n=== DADOS DO REGISTRO ===")
for k, v in list(registro.items())[:15]:
    print(f"{k:25} = {v}")

# Adicionar contatos
imp.carregar_contatos()
pes_id = registro.get('pes_int_codigo')
if pes_id in imp.contatos:
    registro['telefone'] = imp.contatos[pes_id].get('telefone')
    registro['celular'] = imp.contatos[pes_id].get('celular')

# Validar
resultado = imp.validar_cliente(registro)

print("\n=== RESULTADO VALIDAÇÃO ===")
print(f"Válido: {resultado.valido}")
print(f"Erros: {resultado.erros}")
print(f"Avisos: {resultado.avisos}")

if resultado.valido:
    print("\n=== DADOS LIMPOS (PARA INSERIR) ===")
    for k, v in resultado.dados_limpos.items():
        if v is not None:
            tamanho = len(str(v)) if v else 0
            print(f"{k:20} = {str(v)[:50]:50} ({tamanho} chars)")
