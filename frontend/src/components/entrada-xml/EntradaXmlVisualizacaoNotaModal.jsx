import PropTypes from "prop-types";
import CardFiscal from "../CardFiscal";

function formatarValorFiscal(valor, casas = 4) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function obterCustoAquisicaoItem(item) {
  return Number(
    item?.custo_aquisicao_unitario ??
      item?.custo_aquisicao_unitario_nf ??
      item?.composicao_custo?.custo_aquisicao_unitario ??
      item?.custo_unitario_efetivo ??
      item?.custo_unitario_efetivo_nf ??
      item?.valor_unitario ??
      0,
  );
}

function StatusBadge({ status }) {
  const styles = {
    pendente: "bg-yellow-200 text-yellow-800",
    processada: "bg-green-200 text-green-800",
    cancelada: "bg-red-200 text-red-800",
    erro: "bg-red-300 text-red-900",
  };
  const labels = {
    pendente: "Pendente",
    processada: "Conciliada",
    cancelada: "Cancelada",
    erro: "Erro",
  };

  return (
    <span
      className={`px-3 py-1 rounded-full text-sm font-semibold ${styles[status] || "bg-gray-200"}`}
    >
      {labels[status] || String(status || "").toUpperCase()}
    </span>
  );
}

StatusBadge.propTypes = {
  status: PropTypes.string,
};

StatusBadge.defaultProps = {
  status: "",
};

function EntradaXmlVisualizacaoNotaModal({
  aberto,
  notaSelecionada,
  resumoConferenciaAtual,
  metaConferenciaAtual,
  onClose,
  onAbrirConferencia,
  onAbrirDetalhes,
  onAjustarCustos,
}) {
  if (!aberto || !notaSelecionada) return null;

  const itens = notaSelecionada.itens || [];
  const temProdutosVinculados = Number(notaSelecionada.produtos_vinculados || 0) > 0;
  const podeAbrirProcessamento =
    ["pendente", "processada"].includes(notaSelecionada.status) && temProdutosVinculados;
  const textoBotaoProcessamento =
    notaSelecionada.status === "processada"
      ? "Lancar movimentos pendentes"
      : "Revisar acoes e processar";

  return (
    <div className="fixed inset-0 z-50 bg-black/50">
      <div className="bg-white w-full h-full overflow-hidden flex flex-col">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded-md bg-white/15 hover:bg-white/25 text-sm font-semibold transition-colors"
              >
                Voltar
              </button>
              <div>
                <h2 className="text-xl font-bold">NF-e {notaSelecionada.numero_nota}</h2>
                <p className="text-blue-100 text-sm mt-1">Serie: {notaSelecionada.serie}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
              title="Fechar"
            >
              X
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Dados da Nota</h3>
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Data Emissao:</span>
                  <span className="font-semibold">
                    {new Date(notaSelecionada.data_emissao).toLocaleDateString("pt-BR")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span>
                    <StatusBadge status={notaSelecionada.status} />
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Valor Total:</span>
                  <span className="font-bold text-green-600">
                    R$ {Number(notaSelecionada.valor_total || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-gray-700 mb-2">Fornecedor</h3>
              <div className="space-y-1.5 text-sm">
                <div>
                  <span className="text-gray-600">Nome:</span>
                  <div className="font-semibold">{notaSelecionada.fornecedor_nome}</div>
                </div>
                <div>
                  <span className="text-gray-600">CNPJ:</span>
                  <div className="font-mono text-xs">{notaSelecionada.fornecedor_cnpj}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mb-4 p-3 bg-gray-50 rounded">
            <div className="text-xs text-gray-600 mb-1">Chave de Acesso</div>
            <div className="font-mono text-xs break-all">{notaSelecionada.chave_acesso}</div>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-blue-600">{itens.length}</div>
              <div className="text-xs text-gray-600">Total Itens</div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-green-600">
                {notaSelecionada.produtos_vinculados}
              </div>
              <div className="text-xs text-gray-600">Vinculados</div>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-orange-600">
                {notaSelecionada.produtos_nao_vinculados}
              </div>
              <div className="text-xs text-gray-600">Nao Vinculados</div>
            </div>
          </div>

          {resumoConferenciaAtual && (
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div
                    className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${metaConferenciaAtual?.cls || "bg-gray-100 text-gray-700 border-gray-200"}`}
                  >
                    {metaConferenciaAtual?.label || "Nao conferida"}
                  </div>
                  <p className="text-sm text-gray-700 mt-2">
                    Entrada prevista em estoque:{" "}
                    <strong>
                      {formatarValorFiscal(resumoConferenciaAtual.quantidade_total_conferida, 2)}
                    </strong>
                    {resumoConferenciaAtual.itens_com_divergencia > 0 && (
                      <>
                        {" "}
                        | Divergencias:{" "}
                        <strong>{resumoConferenciaAtual.itens_com_divergencia}</strong>
                      </>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => onAbrirConferencia(notaSelecionada.id)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold"
                >
                  Conferencia
                </button>
              </div>
            </div>
          )}

          <div>
            <h3 className="font-semibold text-gray-700 mb-2">Itens da Nota</h3>
            <div className="space-y-2">
              {itens.map((item) => (
                <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex justify-between items-start mb-1.5">
                    <div className="flex-1">
                      <div className="font-semibold text-gray-800 text-sm">{item.descricao}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        Codigo: {item.codigo_produto} | NCM: {item.ncm}
                      </div>
                    </div>
                    {item.vinculado ? (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
                        Vinculado
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs font-semibold rounded">
                        Nao Vinculado
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs mt-2">
                    <div>
                      <span className="text-gray-600">Qtd:</span>
                      <div className="font-semibold">{item.quantidade}</div>
                    </div>
                    <div>
                      <span className="text-gray-600">Unit:</span>
                      <div className="font-semibold">
                        R$ {Number(item.valor_unitario || 0).toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-600">Custo Aq.:</span>
                      <div className="font-semibold text-amber-700">
                        R$ {formatarValorFiscal(obterCustoAquisicaoItem(item), 4)}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-600">Total:</span>
                      <div className="font-semibold text-green-600">
                        R$ {Number(item.valor_total || 0).toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-600">CFOP:</span>
                      <div className="font-semibold">{item.cfop}</div>
                    </div>
                  </div>

                  <CardFiscal
                    nota={notaSelecionada}
                    item={item}
                    composicao={item.composicao_custo}
                  />

                  {(item.lote || item.data_validade) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 text-xs">
                      {item.lote && (
                        <div className="bg-purple-50 border border-purple-200 rounded p-2">
                          <span className="text-gray-600">Lote:</span>
                          <div className="font-semibold text-purple-800">{item.lote}</div>
                        </div>
                      )}
                      {item.data_validade && (
                        <div className="bg-orange-50 border border-orange-200 rounded p-2">
                          <span className="text-gray-600">Validade:</span>
                          <div className="font-semibold text-orange-800">
                            {new Date(item.data_validade).toLocaleDateString("pt-BR")}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {item.vinculado && item.produto_nome && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <span className="text-xs text-gray-600">Produto vinculado: </span>
                      <span className="text-sm font-semibold text-blue-600">
                        {item.produto_nome}
                      </span>
                    </div>
                  )}

                  {item.tem_divergencia && (
                    <div className="mt-3 rounded-lg border border-orange-200 bg-orange-50 p-3 text-xs text-orange-900">
                      <div className="font-semibold mb-1">Divergencia registrada</div>
                      <div>
                        Estoque: {formatarValorFiscal(item.quantidade_conferida, 2)} | Avaria:{" "}
                        {formatarValorFiscal(item.quantidade_avariada, 2)} | Faltante:{" "}
                        {formatarValorFiscal(item.quantidade_faltante, 2)}
                      </div>
                      {item.observacao_conferencia && (
                        <div className="mt-1">Obs.: {item.observacao_conferencia}</div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t p-4 md:p-6 bg-gray-50 flex flex-wrap justify-between items-center gap-3">
          <div className="text-sm text-gray-600">
            {notaSelecionada.entrada_estoque_realizada ? (
              <span className="text-green-600 font-semibold">Entrada realizada no estoque</span>
            ) : (
              <span className="text-orange-600 font-semibold">Entrada ainda nao processada</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {podeAbrirProcessamento && (
              <>
                {notaSelecionada.status === "pendente" && (
                  <button
                    onClick={() => onAbrirConferencia(notaSelecionada.id)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold"
                  >
                    Conferencia
                  </button>
                )}
                <button
                  onClick={() => onAjustarCustos(notaSelecionada.id)}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold"
                >
                  {textoBotaoProcessamento}
                </button>
              </>
            )}
            {notaSelecionada.status === "pendente" && (
              <button
                onClick={() => onAbrirDetalhes(notaSelecionada.id)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
              >
                Vincular Produtos
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
            >
              Voltar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

EntradaXmlVisualizacaoNotaModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  notaSelecionada: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    numero_nota: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    serie: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    data_emissao: PropTypes.string,
    status: PropTypes.string,
    valor_total: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    fornecedor_nome: PropTypes.string,
    fornecedor_cnpj: PropTypes.string,
    chave_acesso: PropTypes.string,
    produtos_vinculados: PropTypes.number,
    produtos_nao_vinculados: PropTypes.number,
    entrada_estoque_realizada: PropTypes.bool,
    itens: PropTypes.arrayOf(PropTypes.object),
  }),
  resumoConferenciaAtual: PropTypes.shape({
    quantidade_total_conferida: PropTypes.number,
    itens_com_divergencia: PropTypes.number,
  }),
  metaConferenciaAtual: PropTypes.shape({
    cls: PropTypes.string,
    label: PropTypes.string,
  }),
  onClose: PropTypes.func.isRequired,
  onAbrirConferencia: PropTypes.func.isRequired,
  onAbrirDetalhes: PropTypes.func.isRequired,
  onAjustarCustos: PropTypes.func.isRequired,
};

EntradaXmlVisualizacaoNotaModal.defaultProps = {
  notaSelecionada: null,
  resumoConferenciaAtual: null,
  metaConferenciaAtual: null,
};

export default EntradaXmlVisualizacaoNotaModal;
