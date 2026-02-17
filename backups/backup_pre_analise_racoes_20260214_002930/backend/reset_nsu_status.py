#!/usr/bin/env python3
"""
Script para resetar o status de um NSU específico na planilha
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import get_session
from app.conciliacao_models import ConciliacaoImportacao

def reset_nsu_status(nsu: str):
    """Reseta o status de um NSU para 'nao_conciliado'"""
    db = next(get_session())
    
    try:
        # Buscar importações com esse NSU
        importacoes = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.tipo_importacao == 'vendas'
        ).all()
        
        updated = 0
        for importacao in importacoes:
            if not importacao.resumo or 'dados_parseados' not in importacao.resumo:
                continue
            
            dados_parseados = importacao.resumo.get('dados_parseados', [])
            modificado = False
            
            for nsu_data in dados_parseados:
                if nsu_data.get('nsu') == nsu:
                    nsu_data['status_conciliacao'] = 'nao_conciliado'
                    modificado = True
                    print(f"✅ NSU {nsu} resetado para 'nao_conciliado' na importação #{importacao.id}")
            
            if modificado:
                importacao.resumo['dados_parseados'] = dados_parseados
                db.commit()
                updated += 1
        
        if updated == 0:
            print(f"❌ NSU {nsu} não encontrado em nenhuma importação")
        else:
            print(f"✅ Total de {updated} importação(ões) atualizada(s)")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    nsu = "14162149357054"
    reset_nsu_status(nsu)
