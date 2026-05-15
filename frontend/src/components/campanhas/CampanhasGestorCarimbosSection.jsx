import { useEffect, useMemo, useState } from "react";

import CampanhasGestorSection from "./CampanhasGestorSection";

export default function CampanhasGestorCarimbosSection({
  gestorSaldo,
  gestorSecao,
  setGestorSecao,
  gestorCarimboNota,
  setGestorCarimboNota,
  gestorCarimboQuantidade,
  setGestorCarimboQuantidade,
  gestorLancandoCarimbo,
  lancarCarimboGestor,
  gestorCarimbos,
  gestorIncluirEstornados,
  setGestorIncluirEstornados,
  gestorRemovendo,
  estornarCarimboGestor,
  estornarCarimbosSelecionadosGestor,
}) {
  const isOpen = gestorSecao === "carimbos";
  const saldoAtual = Number(gestorSaldo?.total_carimbos || 0);
  const carimbosAtivos = Number(gestorSaldo?.total_carimbos_brutos || 0);
  const carimbosComprometidos = Number(
    gestorSaldo?.carimbos_comprometidos_total ||
      gestorSaldo?.carimbos_convertidos ||
      0,
  );
  const carimbosEmDebito = Number(gestorSaldo?.carimbos_em_debito || 0);
  const [carimbosSelecionados, setCarimbosSelecionados] = useState([]);
  const removendoLote = gestorRemovendo === "lote";
  const carimbosVisiveis = useMemo(
    () =>
      (gestorCarimbos || []).filter(
        (stamp) => !stamp.voided_at || gestorIncluirEstornados,
      ),
    [gestorCarimbos, gestorIncluirEstornados],
  );
  const carimbosSelecionaveis = useMemo(
    () => carimbosVisiveis.filter((stamp) => !stamp.voided_at),
    [carimbosVisiveis],
  );
  const idsSelecionaveis = useMemo(
    () => carimbosSelecionaveis.map((stamp) => stamp.id),
    [carimbosSelecionaveis],
  );
  const selecionadosVisiveis = carimbosSelecionados.filter((id) =>
    idsSelecionaveis.includes(id),
  );
  const todosVisiveisSelecionados =
    idsSelecionaveis.length > 0 &&
    idsSelecionaveis.every((id) => carimbosSelecionados.includes(id));

  useEffect(() => {
    setCarimbosSelecionados((atuais) =>
      atuais.filter((id) => idsSelecionaveis.includes(id)),
    );
  }, [idsSelecionaveis]);

  const alternarTodosVisiveis = () => {
    setCarimbosSelecionados(todosVisiveisSelecionados ? [] : idsSelecionaveis);
  };

  const alternarCarimbo = (stampId) => {
    setCarimbosSelecionados((atuais) =>
      atuais.includes(stampId)
        ? atuais.filter((id) => id !== stampId)
        : [...atuais, stampId],
    );
  };

  const removerSelecionados = async () => {
    const ok = await estornarCarimbosSelecionadosGestor(selecionadosVisiveis);
    if (ok) {
      setCarimbosSelecionados([]);
    }
  };

  return (
    <CampanhasGestorSection
      icon={"\uD83C\uDFF7\uFE0F"}
      title="Cartao Fidelidade"
      subtitle={`${saldoAtual} carimbo(s) no saldo atual`}
      isOpen={isOpen}
      onToggle={() => setGestorSecao(isOpen ? null : "carimbos")}
    >
      <div className="p-6 space-y-4">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900 space-y-1">
          <p className="font-medium">
            Saldo atual de carimbos: {saldoAtual}
          </p>
          <p className="text-amber-800">
            Carimbos ativos no historico: {carimbosAtivos}
          </p>
          <p className="text-amber-800">
            Carimbos comprometidos por recompensa: {carimbosComprometidos}
          </p>
          {carimbosEmDebito > 0 && (
            <p className="text-red-700 font-medium">
              Debito fidelidade: {carimbosEmDebito} carimbo(s)
            </p>
          )}
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm font-medium text-green-800 mb-3">
            Lancar carimbo manual
          </p>
          <div className="flex gap-3 flex-wrap items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Observacao (opcional)
              </label>
              <input
                type="text"
                value={gestorCarimboNota}
                onChange={(e) => setGestorCarimboNota(e.target.value)}
                placeholder="Ex: Conversao de cartao fisico"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="flex flex-col">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Quantidade
              </label>
              <div className="flex items-center gap-2 border rounded-lg bg-white">
                <button
                  onClick={() => setGestorCarimboQuantidade(Math.max(1, gestorCarimboQuantidade - 1))}
                  disabled={gestorLancandoCarimbo || gestorCarimboQuantidade <= 1}
                  className="px-3 py-2 text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  −
                </button>
                <span className="px-3 py-2 font-semibold text-gray-900 min-w-[3rem] text-center">
                  {gestorCarimboQuantidade}
                </span>
                <button
                  onClick={() => setGestorCarimboQuantidade(gestorCarimboQuantidade + 1)}
                  disabled={gestorLancandoCarimbo || gestorCarimboQuantidade >= 100}
                  className="px-3 py-2 text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  +
                </button>
              </div>
            </div>
            <button
              onClick={lancarCarimboGestor}
              disabled={gestorLancandoCarimbo}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {gestorLancandoCarimbo ? `Lancando (${gestorCarimboQuantidade})...` : `Lancar ${gestorCarimboQuantidade > 1 ? gestorCarimboQuantidade + " Carimbos" : "Carimbo"}`}
            </button>
          </div>
        </div>

        {gestorCarimbos && gestorCarimbos.length > 0 ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2">
              <label className="flex items-center gap-2 text-xs font-medium text-gray-600 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={todosVisiveisSelecionados}
                  onChange={alternarTodosVisiveis}
                  disabled={idsSelecionaveis.length === 0 || removendoLote}
                  className="rounded"
                />
                Selecionar visiveis
              </label>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">
                  {selecionadosVisiveis.length} selecionado(s)
                </span>
                <button
                  type="button"
                  onClick={removerSelecionados}
                  disabled={
                    selecionadosVisiveis.length === 0 ||
                    removendoLote ||
                    !estornarCarimbosSelecionadosGestor
                  }
                  className="px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {removendoLote ? "Removendo..." : "Remover selecionados"}
                </button>
              </div>
            </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 w-10">
                    <input
                      type="checkbox"
                      checked={todosVisiveisSelecionados}
                      onChange={alternarTodosVisiveis}
                      disabled={idsSelecionaveis.length === 0 || removendoLote}
                      className="rounded"
                      aria-label="Selecionar carimbos visiveis"
                    />
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    #ID
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    Data
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    Origem
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-600">
                    Obs
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-600">
                    Acao
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {carimbosVisiveis.map((stamp) => (
                    <tr
                      key={stamp.id}
                      className={
                        stamp.voided_at
                          ? "bg-red-50 opacity-60"
                          : "hover:bg-gray-50"
                      }
                    >
                      <td className="px-4 py-2">
                        <input
                          type="checkbox"
                          checked={carimbosSelecionados.includes(stamp.id)}
                          onChange={() => alternarCarimbo(stamp.id)}
                          disabled={Boolean(stamp.voided_at) || removendoLote}
                          className="rounded"
                          aria-label={`Selecionar carimbo ${stamp.id}`}
                        />
                      </td>
                      <td className="px-4 py-2 text-gray-500 font-mono text-xs">
                        {stamp.id}
                      </td>
                      <td className="px-4 py-2 text-gray-700 text-xs whitespace-nowrap">
                        {new Date(stamp.created_at).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-4 py-2">
                        {stamp.is_manual ? (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                            Manual
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            Automatico
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-gray-500 text-xs max-w-[180px] truncate">
                        {stamp.notes || "-"}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {stamp.voided_at ? (
                          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                            Estornado
                          </span>
                        ) : stamp.is_converted ? (
                          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">
                            Comprometido em recompensa
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            Disponivel
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {!stamp.voided_at && (
                          <button
                            onClick={() => estornarCarimboGestor(stamp.id)}
                            disabled={gestorRemovendo === stamp.id || removendoLote}
                            className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                          >
                            {gestorRemovendo === stamp.id ? "..." : "Remover"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          </div>
        ) : (
          <p className="text-center text-gray-400 py-4 text-sm">
            Nenhum carimbo encontrado.
          </p>
        )}

        <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={gestorIncluirEstornados}
            onChange={(e) => setGestorIncluirEstornados(e.target.checked)}
            className="rounded"
          />
          Mostrar estornados
        </label>
      </div>
    </CampanhasGestorSection>
  );
}
