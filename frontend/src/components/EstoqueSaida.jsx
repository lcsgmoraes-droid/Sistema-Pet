import { useState, useEffect } from "react";
import api from "../api";
import { toast } from "react-hot-toast";

const EstoqueSaida = () => {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tipoOperacao, setTipoOperacao] = useState("saida"); // saida, ajuste, transferencia
  const [formData, setFormData] = useState({
    produto_id: "",
    quantidade: "",
    motivo: "",
    observacoes: "",
    destino: "", // Para transferências
  });

  useEffect(() => {
    carregarProdutos();
  }, []);

  const carregarProdutos = async () => {
    try {
      const response = await api.get(`/produtos/`);
      setProdutos(response.data);
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      let motivoFinal = formData.motivo;
      if (tipoOperacao === "transferencia" && formData.destino) {
        motivoFinal = `Transferência para ${formData.destino}`;
      }

      const payload = {
        produto_id: parseInt(formData.produto_id),
        quantidade: parseFloat(formData.quantidade),
        motivo: motivoFinal,
        observacoes: formData.observacoes || undefined,
      };

      await api.post(`/estoque/saida`, payload);

      const mensagens = {
        saida: "✅ Saída de estoque realizada com sucesso!",
        ajuste: "✅ Ajuste de estoque realizado com sucesso!",
        transferencia: "✅ Transferência realizada com sucesso!",
      };

      toast.success(mensagens[tipoOperacao]);

      // Limpar formulário
      setFormData({
        produto_id: "",
        quantidade: "",
        motivo: "",
        observacoes: "",
        destino: "",
      });

      carregarProdutos();
    } catch (error) {
      console.error("Erro ao dar saída:", error);
      toast.error(error.response?.data?.detail || "Erro ao processar operação");
    } finally {
      setLoading(false);
    }
  };

  const produtoSelecionado = produtos.find((p) => p.id === parseInt(formData.produto_id));

  const getMotivosSugeridos = () => {
    switch (tipoOperacao) {
      case "saida":
        return [
          "Venda",
          "Uso interno",
          "Quebra",
          "Validade vencida",
          "Perda",
          "Amostra grátis",
          "Consumo próprio",
        ];
      case "ajuste":
        return [
          "Inventário - ajuste de contagem",
          "Correção de lançamento",
          "Divergência detectada",
          "Acerto de estoque físico",
        ];
      case "transferencia":
        return [];
      default:
        return [];
    }
  };

  const getTitulo = () => {
    const titulos = {
      saida: "📤 Saída de Estoque",
      ajuste: "⚙️ Ajuste de Estoque",
      transferencia: "🔄 Transferência de Estoque",
    };
    return titulos[tipoOperacao];
  };

  const getDescricao = () => {
    const descricoes = {
      saida: "Registre a saída de produtos do estoque",
      ajuste: "Corrija o estoque para corresponder à contagem física",
      transferencia: "Transfira produtos entre filiais ou depósitos",
    };
    return descricoes[tipoOperacao];
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">{getTitulo()}</h1>
        <p className="text-gray-600">{getDescricao()}</p>
      </div>

      {/* Seletor de Tipo de Operação */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <div className="flex gap-3">
          <button
            onClick={() => setTipoOperacao("saida")}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-colors ${
              tipoOperacao === "saida"
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            📤 Saída
          </button>
          <button
            onClick={() => setTipoOperacao("ajuste")}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-colors ${
              tipoOperacao === "ajuste"
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            ⚙️ Ajuste
          </button>
          <button
            onClick={() => setTipoOperacao("transferencia")}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-colors ${
              tipoOperacao === "transferencia"
                ? "bg-green-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            🔄 Transferência
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Produto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Produto *</label>
            <select
              value={formData.produto_id}
              onChange={(e) => setFormData({ ...formData, produto_id: e.target.value })}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Selecione um produto</option>
              {produtos.map((produto) => (
                <option key={produto.id} value={produto.id}>
                  {produto.codigo} - {produto.nome} (Estoque: {produto.estoque_atual || 0})
                </option>
              ))}
            </select>
          </div>

          {/* Informações do Produto Selecionado */}
          {produtoSelecionado && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Informações do Produto</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Estoque Atual:</span>
                  <span
                    className={`ml-2 font-semibold ${
                      (produtoSelecionado.estoque_atual || 0) <=
                      (produtoSelecionado.estoque_minimo || 0)
                        ? "text-red-600"
                        : "text-green-600"
                    }`}
                  >
                    {produtoSelecionado.estoque_atual || 0}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Estoque Mínimo:</span>
                  <span className="ml-2 font-semibold">
                    {produtoSelecionado.estoque_minimo || 0}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Custo Médio:</span>
                  <span className="ml-2 font-semibold">
                    R$ {produtoSelecionado.custo_medio?.toFixed(2) || "0.00"}
                  </span>
                </div>
              </div>

              {(produtoSelecionado.estoque_atual || 0) <=
                (produtoSelecionado.estoque_minimo || 0) && (
                <div className="mt-3 pt-3 border-t border-blue-300">
                  <span className="text-orange-600 font-semibold">
                    ⚠️ Atenção: Estoque abaixo do mínimo!
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Quantidade */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quantidade *</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={produtoSelecionado?.estoque_atual || undefined}
              value={formData.quantidade}
              onChange={(e) => setFormData({ ...formData, quantidade: e.target.value })}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0.00"
            />
            {produtoSelecionado && formData.quantidade && (
              <p className="text-sm text-gray-500 mt-1">
                Estoque após operação:{" "}
                <span className="font-semibold">
                  {(
                    (produtoSelecionado.estoque_atual || 0) - parseFloat(formData.quantidade || 0)
                  ).toFixed(2)}
                </span>
              </p>
            )}
          </div>

          {/* Destino (apenas para transferências) */}
          {tipoOperacao === "transferencia" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Destino da Transferência *
              </label>
              <input
                type="text"
                value={formData.destino}
                onChange={(e) => setFormData({ ...formData, destino: e.target.value })}
                required={tipoOperacao === "transferencia"}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Ex: Filial Centro, Depósito 2, etc."
              />
            </div>
          )}

          {/* Motivo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Motivo *</label>
            {tipoOperacao !== "transferencia" ? (
              <>
                <select
                  value={formData.motivo}
                  onChange={(e) => setFormData({ ...formData, motivo: e.target.value })}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Selecione o motivo</option>
                  {getMotivosSugeridos().map((motivo) => (
                    <option key={motivo} value={motivo}>
                      {motivo}
                    </option>
                  ))}
                  <option value="outro">Outro motivo...</option>
                </select>
                {formData.motivo === "outro" && (
                  <input
                    type="text"
                    value={formData.observacoes}
                    onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-2"
                    placeholder="Descreva o motivo..."
                  />
                )}
              </>
            ) : (
              <input
                type="text"
                value={`Transferência para ${formData.destino}`}
                disabled
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600"
              />
            )}
          </div>

          {/* Observações (exceto quando motivo = outro) */}
          {formData.motivo !== "outro" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Observações</label>
              <textarea
                value={formData.observacoes}
                onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                rows="3"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Informações adicionais..."
              />
            </div>
          )}

          {/* Resumo */}
          {formData.quantidade && produtoSelecionado && (
            <div
              className={`border rounded-lg p-4 ${
                tipoOperacao === "saida"
                  ? "bg-orange-50 border-orange-200"
                  : tipoOperacao === "ajuste"
                    ? "bg-purple-50 border-purple-200"
                    : "bg-green-50 border-green-200"
              }`}
            >
              <h3
                className={`font-semibold mb-2 ${
                  tipoOperacao === "saida"
                    ? "text-orange-900"
                    : tipoOperacao === "ajuste"
                      ? "text-purple-900"
                      : "text-green-900"
                }`}
              >
                Resumo da Operação
              </h3>
              <div className="text-sm space-y-1">
                <div>
                  <span className="text-gray-600">Produto:</span>
                  <span className="ml-2 font-semibold">{produtoSelecionado.nome}</span>
                </div>
                <div>
                  <span className="text-gray-600">Quantidade:</span>
                  <span className="ml-2 font-semibold">{formData.quantidade}</span>
                </div>
                <div>
                  <span className="text-gray-600">Estoque Atual:</span>
                  <span className="ml-2 font-semibold">
                    {produtoSelecionado.estoque_atual || 0}
                  </span>
                </div>
                <div className="pt-2 border-t">
                  <span className="text-gray-600">Estoque Final:</span>
                  <span
                    className={`ml-2 font-bold text-lg ${
                      (produtoSelecionado.estoque_atual || 0) -
                        parseFloat(formData.quantidade || 0) <=
                      (produtoSelecionado.estoque_minimo || 0)
                        ? "text-red-600"
                        : "text-green-600"
                    }`}
                  >
                    {(
                      (produtoSelecionado.estoque_atual || 0) - parseFloat(formData.quantidade || 0)
                    ).toFixed(2)}
                  </span>
                </div>
                {tipoOperacao === "transferencia" && formData.destino && (
                  <div className="pt-2 border-t">
                    <span className="text-gray-600">Destino:</span>
                    <span className="ml-2 font-semibold">{formData.destino}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Alertas */}
          {produtoSelecionado && formData.quantidade && (
            <>
              {parseFloat(formData.quantidade) > (produtoSelecionado.estoque_atual || 0) && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <span className="text-red-700 font-semibold">
                    ❌ Erro: Quantidade superior ao estoque disponível!
                  </span>
                </div>
              )}
              {(produtoSelecionado.estoque_atual || 0) - parseFloat(formData.quantidade) <
                (produtoSelecionado.estoque_minimo || 0) && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <span className="text-yellow-800 font-semibold">
                    ⚠️ Aviso: Esta operação deixará o estoque abaixo do mínimo!
                  </span>
                </div>
              )}
            </>
          )}

          {/* Botões */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={
                loading ||
                (produtoSelecionado &&
                  formData.quantidade &&
                  parseFloat(formData.quantidade) > (produtoSelecionado.estoque_atual || 0))
              }
              className={`flex-1 py-3 px-6 rounded-lg font-semibold transition-colors ${
                tipoOperacao === "saida"
                  ? "bg-blue-600 hover:bg-blue-700"
                  : tipoOperacao === "ajuste"
                    ? "bg-purple-600 hover:bg-purple-700"
                    : "bg-green-600 hover:bg-green-700"
              } text-white disabled:bg-gray-400 disabled:cursor-not-allowed`}
            >
              {loading
                ? "⏳ Processando..."
                : tipoOperacao === "saida"
                  ? "✅ Confirmar Saída"
                  : tipoOperacao === "ajuste"
                    ? "✅ Confirmar Ajuste"
                    : "✅ Confirmar Transferência"}
            </button>
            <button
              type="button"
              onClick={() =>
                setFormData({
                  produto_id: "",
                  quantidade: "",
                  motivo: "",
                  observacoes: "",
                  destino: "",
                })
              }
              className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
            >
              🔄 Limpar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EstoqueSaida;
