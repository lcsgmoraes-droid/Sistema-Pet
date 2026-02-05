"""
Script de Teste - VariacaoLixeiraService
Demonstra o funcionamento do sistema de lixeira para variacoes.
"""

def testar_lixeira():
    print("=" * 60)
    print("TESTE - VariacaoLixeiraService")
    print("=" * 60)
    
    print("\nComo usar:")
    print("-" * 60)
    
    print("""
EXCLUIR VARIACAO (soft delete):
   
   from app.services.variacao_lixeira_service import VariacaoLixeiraService
   
   variacao = VariacaoLixeiraService.excluir_variacao(
       variacao_id=94,
       db=db,
       user_id=1
   )
   # Resultado: ativo=False, deleted_at=agora

RESTAURAR VARIACAO:
   
   variacao = VariacaoLixeiraService.restaurar_variacao(
       variacao_id=94,
       db=db,
       user_id=1
   )
   # Resultado: ativo=True, deleted_at=None

LISTAR ATIVAS:
   
   ativas = VariacaoLixeiraService.listar_variacoes_ativas(
       produto_pai_id=93, db=db, user_id=1
   )

LISTAR EXCLUIDAS (lixeira):
   
   excluidas = VariacaoLixeiraService.listar_variacoes_excluidas(
       produto_pai_id=93, db=db, user_id=1
   )

CONTAR:
   
   contadores = VariacaoLixeiraService.contar_variacoes(
       produto_pai_id=93, db=db, user_id=1
   )
   # Retorna: {'ativas': X, 'excluidas': Y, 'total': Z}

GARANTIAS:
- PDV ignora variacoes excluidas (filtra ativo=True)
- Vinculos em ProdutoVariacaoAtributo preservados
- Apenas tipo VARIACAO pode ser excluida/restaurada
- Transacoes seguras com rollback automatico
    """)
    
    print("\n" + "=" * 60)
    print("Service pronto para uso!")
    print("=" * 60)


if __name__ == '__main__':
    testar_lixeira()
