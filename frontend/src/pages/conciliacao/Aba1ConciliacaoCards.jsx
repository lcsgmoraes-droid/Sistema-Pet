import { useState } from "react";
import api from "../../api";
import SaleReference from "../../components/ui/SaleReference";

export function VendaPDVItem({
  expandido,
  onAtualizarOperadora,
  onRecarregarVendas,
  operadoraSelecionada,
  operadoras,
  venda,
}) {
  const [expanded, setExpanded] = useState(expandido);
  const [editandoNSU, setEditandoNSU] = useState(false);
  const [novoNSU, setNovoNSU] = useState("");
  const [editandoOperadora, setEditandoOperadora] = useState(false);
  const [novaOperadora, setNovaOperadora] = useState("");

  const handleSalvarNSU = async () => {
    if (!novoNSU || novoNSU.trim() === "") {
      alert("Digite um NSU válido");
      return;
    }

    try {
      const response = await api.patch(`/vendas/${venda.id}/pagamento/${venda.pagamento.id}/nsu`, {
        nsu_cartao: novoNSU.trim(),
      });

      if (response.data) {
        setEditandoNSU(false);
        setNovoNSU("");
        await onRecarregarVendas();
        alert("NSU atualizado com sucesso!");
      }
    } catch (error) {
      console.error("Erro ao salvar NSU:", error);
      alert(error.response?.data?.detail || "Erro ao salvar NSU");
    }
  };

  const handleSalvarOperadora = async () => {
    if (!novaOperadora || novaOperadora === "") {
      alert("Selecione uma operadora");
      return;
    }

    const sucesso = await onAtualizarOperadora(venda.pagamento.id, parseInt(novaOperadora));
    if (sucesso) {
      setEditandoOperadora(false);
      setNovaOperadora("");
    }
  };

  return (
    <div
      className="border border-gray-200 rounded-lg p-3 mb-2 hover:bg-gray-50 cursor-pointer"
      onClick={(e) => {
        if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON") return;
        if (!expandido) setExpanded(!expanded);
      }}
    >
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-gray-900">
            <SaleReference sale={venda} showPrefix={false} />
          </span>

          {venda.pagamento.operadora_id && !editandoOperadora ? (
            <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
              {operadoras.find((op) => op.id === venda.pagamento.operadora_id)?.nome || "N/A"}
            </span>
          ) : editandoOperadora ? (
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <select
                value={novaOperadora}
                onChange={(e) => setNovaOperadora(e.target.value)}
                className="border border-purple-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
                autoFocus
              >
                <option value="">Selecione...</option>
                {operadoras.map((op) => (
                  <option key={op.id} value={op.id}>
                    {op.nome}
                  </option>
                ))}
              </select>
              <button
                onClick={handleSalvarOperadora}
                className="bg-green-500 text-white px-2 py-1 rounded text-xs hover:bg-green-600"
              >
                ✓
              </button>
              <button
                onClick={() => {
                  setEditandoOperadora(false);
                  setNovaOperadora("");
                }}
                className="bg-gray-400 text-white px-2 py-1 rounded text-xs hover:bg-gray-500"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setEditandoOperadora(true);
              }}
              className="text-xs text-purple-600 hover:text-purple-700 underline font-medium px-2 py-1 bg-purple-50 rounded"
            >
              🏢 Sem Operadora - Clique aqui
            </button>
          )}

          {venda.pagamento.nsu ? (
            <span className="text-sm text-green-600">NSU: {venda.pagamento.nsu}</span>
          ) : editandoNSU ? (
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={novoNSU}
                onChange={(e) => setNovoNSU(e.target.value)}
                placeholder="Digite o NSU"
                className="border border-orange-300 rounded px-2 py-1 text-xs w-32 focus:outline-none focus:ring-1 focus:ring-orange-500"
                autoFocus
              />
              <button
                onClick={handleSalvarNSU}
                className="bg-green-500 text-white px-2 py-1 rounded text-xs hover:bg-green-600"
              >
                ✓
              </button>
              <button
                onClick={() => {
                  setEditandoNSU(false);
                  setNovoNSU("");
                }}
                className="bg-gray-400 text-white px-2 py-1 rounded text-xs hover:bg-gray-500"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setEditandoNSU(true);
              }}
              className="text-sm text-orange-600 hover:text-orange-700 underline font-medium"
            >
              SEM NSU - Clique para preencher
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">R$ {venda.total.toFixed(2)}</span>
          {!expandido && (
            <svg
              className={`h-4 w-4 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          )}
        </div>
      </div>

      {(expanded || expandido) && (
        <div className="mt-3 pt-3 border-t border-gray-200 text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-600">Data:</span>
            <span>{new Date(venda.data_venda).toLocaleDateString("pt-BR")}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Tipo:</span>
            <span className="capitalize">{venda.pagamento.forma}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Operadora:</span>
            <span className="font-medium text-blue-600">{operadoraSelecionada?.nome || "N/A"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Bandeira:</span>
            <span>{venda.pagamento.bandeira || "N/A"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Parcelas:</span>
            <span>{venda.pagamento.parcelas}x</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Valor:</span>
            <span className="font-medium">R$ {venda.pagamento.valor.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function NSUStoneItem({ expandido, nsu }) {
  const [expanded, setExpanded] = useState(expandido);

  return (
    <div
      className="border border-blue-200 rounded-lg p-3 mb-2 hover:bg-blue-50 cursor-pointer"
      onClick={() => !expandido && setExpanded(!expanded)}
    >
      <div className="flex justify-between items-center">
        <div>
          <span className="font-medium text-blue-900">NSU: {nsu.nsu}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">R$ {nsu.valor_liquido?.toFixed(2)}</span>
          {!expandido && (
            <svg
              className={`h-4 w-4 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          )}
        </div>
      </div>

      {(expanded || expandido) && nsu.data_venda && (
        <div className="mt-3 pt-3 border-t border-blue-200 text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-600">Data:</span>
            <span>{new Date(nsu.data_venda).toLocaleDateString("pt-BR")}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Bandeira:</span>
            <span>{nsu.bandeira}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Parcelas:</span>
            <span>{nsu.parcelas}x</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Valor Bruto:</span>
            <span>R$ {nsu.valor_bruto?.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Valor Líquido:</span>
            <span className="font-medium text-green-600">R$ {nsu.valor_liquido?.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function MatchPair({ match, isConciliado = false }) {
  const statusCor = {
    ok: "bg-green-50 border-green-300",
    divergencia: "bg-yellow-50 border-yellow-300",
    orfao: "bg-red-50 border-red-300",
    sem_nsu: "bg-orange-50 border-orange-300",
  };

  return (
    <div className={`border-2 rounded-lg p-4 mb-3 ${statusCor[match.status]} relative`}>
      {isConciliado && (
        <div className="absolute top-2 right-2 px-3 py-1 bg-green-600 text-white text-xs font-bold rounded-full">
          ✅ CONCILIADO
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 items-center">
        <div className="bg-white p-3 rounded border">
          {match.venda_pdv ? (
            <>
              <div className="text-sm font-semibold text-gray-800">
                <SaleReference value={match.venda_pdv.numero} />
              </div>
              <div className="text-xs text-gray-600 mt-1">
                NSU: {match.venda_pdv.nsu || <span className="text-orange-600">SEM NSU</span>}
              </div>
              <div className="text-xs text-gray-600">
                {match.venda_pdv.bandeira} - {match.venda_pdv.parcelas}x
              </div>
              <div className="text-xs font-semibold text-gray-800 mt-1">
                R$ {match.venda_pdv.valor?.toFixed(2)}
              </div>
            </>
          ) : (
            <div className="text-sm text-gray-400 italic">Sem venda no PDV</div>
          )}
        </div>

        <div className="flex items-center justify-center">
          {match.status === "ok" && <div className="text-green-600 text-2xl">✅</div>}
          {match.status === "divergencia" && (
            <div className="flex flex-col items-center">
              <div className="text-yellow-600 text-xl">⚠️</div>
              <div className="text-xs text-yellow-700 font-semibold mt-1">
                {match.divergencia?.tipo}
              </div>
            </div>
          )}
          {match.status === "orfao" && <div className="text-red-600 text-2xl">❌</div>}
          {match.status === "sem_nsu" && <div className="text-orange-600 text-2xl">➡️</div>}
        </div>

        <div className="bg-blue-50 p-3 rounded border border-blue-200">
          {match.venda_stone ? (
            <>
              <div className="text-sm font-semibold text-blue-800">Planilha Operadora</div>
              <div className="text-xs text-blue-700 mt-1">NSU: {match.venda_stone.nsu}</div>
              <div className="text-xs text-blue-600">
                {match.venda_stone.bandeira} - {match.venda_stone.parcelas}x
              </div>
              <div className="text-xs font-semibold text-blue-800 mt-1">
                R$ {match.venda_stone.valor_bruto?.toFixed(2)}
              </div>
            </>
          ) : (
            <div className="text-sm text-blue-300 italic">Sem NSU na planilha</div>
          )}
        </div>
      </div>

      {match.divergencia && (
        <div className="mt-3 pt-3 border-t border-yellow-300">
          <div className="text-xs text-yellow-800">
            <span className="font-semibold">PDV:</span> {match.divergencia.pdv} →{" "}
            <span className="font-semibold">Stone:</span> {match.divergencia.stone}
          </div>
        </div>
      )}
    </div>
  );
}
