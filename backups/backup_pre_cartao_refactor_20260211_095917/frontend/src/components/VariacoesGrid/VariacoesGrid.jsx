/**
 * Componente para cadastro inline de variações de produto
 * Sprint 2: Produtos com Variação
 * 
 * Uso:
 * <VariacoesGrid 
 *   variacoes={variacoes} 
 *   onChange={setVariacoes}
 *   produtoBase={dadosProduto}
 * />
 */
import { useState } from 'react';
import { Trash2, Plus } from 'lucide-react';
import './VariacoesGrid.css';

export default function VariacoesGrid({ variacoes = [], onChange, produtoBase }) {
  const [editando, setEditando] = useState(null);

  const adicionarVariacao = () => {
    const novaVariacao = {
      id: `temp-${Date.now()}`, // ID temporário até salvar no backend
      nome_complementar: '',
      sku: `${produtoBase.codigo}-VAR${variacoes.length + 1}`,
      codigo_barras: '',
      preco_custo: produtoBase.preco_custo || 0,
      preco_venda: produtoBase.preco_venda || 0,
      estoque_inicial: 0,
      estoque_minimo: produtoBase.estoque_minimo || 0,
    };

    onChange([...variacoes, novaVariacao]);
  };

  const removerVariacao = (index) => {
    const novasVariacoes = variacoes.filter((_, i) => i !== index);
    onChange(novasVariacoes);
  };

  const atualizarVariacao = (index, campo, valor) => {
    const novasVariacoes = [...variacoes];
    novasVariacoes[index] = {
      ...novasVariacoes[index],
      [campo]: valor
    };
    onChange(novasVariacoes);
  };

  return (
    <div className="variacoes-grid">
      <div className="variacoes-header">
        <h3>Variações do Produto</h3>
        <button
          type="button"
          onClick={adicionarVariacao}
          className="btn btn-sm btn-primary"
        >
          <Plus size={16} />
          Adicionar Variação
        </button>
      </div>

      {variacoes.length === 0 ? (
        <div className="empty-state">
          <p>Nenhuma variação cadastrada</p>
          <p className="text-sm text-gray-500">
            Clique em "Adicionar Variação" para criar variações deste produto
          </p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="variacoes-table">
            <thead>
              <tr>
                <th>Nome Complementar*</th>
                <th>SKU*</th>
                <th>Código Barras</th>
                <th>Custo</th>
                <th>Preço Venda*</th>
                <th>Estoque Inicial</th>
                <th>Estoque Mínimo</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {variacoes.map((variacao, index) => (
                <tr key={variacao.id || index}>
                  <td>
                    <input
                      type="text"
                      value={variacao.nome_complementar}
                      onChange={(e) => atualizarVariacao(index, 'nome_complementar', e.target.value)}
                      placeholder="Ex: 1kg, 3kg, 15kg"
                      className="form-input"
                      required
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      value={variacao.sku}
                      onChange={(e) => atualizarVariacao(index, 'sku', e.target.value)}
                      placeholder="SKU único"
                      className="form-input"
                      required
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      value={variacao.codigo_barras}
                      onChange={(e) => atualizarVariacao(index, 'codigo_barras', e.target.value)}
                      placeholder="EAN13"
                      className="form-input"
                      maxLength="13"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={variacao.preco_custo}
                      onChange={(e) => atualizarVariacao(index, 'preco_custo', parseFloat(e.target.value) || 0)}
                      step="0.01"
                      min="0"
                      className="form-input"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={variacao.preco_venda}
                      onChange={(e) => atualizarVariacao(index, 'preco_venda', parseFloat(e.target.value) || 0)}
                      step="0.01"
                      min="0"
                      className="form-input"
                      required
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={variacao.estoque_inicial}
                      onChange={(e) => atualizarVariacao(index, 'estoque_inicial', parseInt(e.target.value) || 0)}
                      min="0"
                      className="form-input"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={variacao.estoque_minimo}
                      onChange={(e) => atualizarVariacao(index, 'estoque_minimo', parseInt(e.target.value) || 0)}
                      min="0"
                      className="form-input"
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => removerVariacao(index)}
                      className="btn btn-sm btn-danger"
                      title="Remover variação"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {variacoes.length > 0 && (
        <div className="variacoes-summary">
          <p>
            <strong>{variacoes.length}</strong> variação(ões) cadastrada(s)
          </p>
          <p className="text-sm text-gray-600">
            Estoque total: <strong>
              {variacoes.reduce((sum, v) => sum + (v.estoque_inicial || 0), 0)}
            </strong> unidades
          </p>
        </div>
      )}
    </div>
  );
}
