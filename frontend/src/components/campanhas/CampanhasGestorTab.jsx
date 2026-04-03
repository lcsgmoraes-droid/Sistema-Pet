export default function CampanhasGestorTab({
  gestorModo,
  setGestorModo,
  gestorSearch,
  setGestorSearch,
  buscarClientesGestor,
  setGestorSugestoes,
  gestorBuscando,
  gestorSugestoes,
  selecionarClienteGestor,
  gestorCampanhaTipo,
  setGestorCampanhaTipo,
  carregarClientesPorCampanha,
  gestorCampanhaCarregando,
  gestorCampanhaLista,
  abrirClienteNoGestor,
  gestorCarregando,
  gestorCliente,
  gestorSaldo,
  gestorCarimbos,
  gestorSecao,
  setGestorSecao,
  gestorIncluirEstornados,
  setGestorIncluirEstornados,
  gestorCarimboNota,
  setGestorCarimboNota,
  gestorLancandoCarimbo,
  lancarCarimboGestor,
  gestorRemovendo,
  estornarCarimboGestor,
  formatBRL,
  RANK_LABELS,
  gestorCashbackTipo,
  setGestorCashbackTipo,
  gestorCashbackValor,
  setGestorCashbackValor,
  gestorCashbackDesc,
  setGestorCashbackDesc,
  gestorLancandoCashback,
  ajustarCashbackGestor,
  gestorCupons,
  CUPOM_STATUS,
  anularCupomGestor,
  gestorAnulando,
}) {
  return (

        <div className="space-y-4">
          {/* HEADER + TOGGLE DE MODO */}
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <div>
                <h2 className="font-semibold text-gray-800">
                  Ã°Å¸â€ºÂ Ã¯Â¸Â Gestor de BenefÃƒÂ­cios
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {gestorModo === "cliente"
                    ? "Busque um cliente para gerenciar seus benefÃƒÂ­cios."
                    : "Selecione um tipo e veja todos os clientes participantes."}
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => setGestorModo("cliente")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gestorModo === "cliente"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  Ã°Å¸â€Â Por Cliente
                </button>
                <button
                  onClick={() => setGestorModo("campanha")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    gestorModo === "campanha"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  Ã°Å¸ÂÂ·Ã¯Â¸Â Por Campanha
                </button>
              </div>
            </div>

            {/* MODO: POR CLIENTE */}
            {gestorModo === "cliente" && (
              <div className="relative max-w-md">
                <input
                  type="text"
                  value={gestorSearch}
                  onChange={(e) => {
                    setGestorSearch(e.target.value);
                    buscarClientesGestor(e.target.value);
                  }}
                  onKeyDown={(e) =>
                    e.key === "Escape" && setGestorSugestoes([])
                  }
                  placeholder="Nome, CPF ou telefone do cliente..."
                  className="w-full border rounded-lg px-3 py-2.5 text-sm"
                  autoComplete="off"
                />
                {gestorBuscando && (
                  <span className="absolute right-3 top-3 text-xs text-gray-400 animate-pulse">
                    Buscando...
                  </span>
                )}
                {gestorSugestoes.length > 0 && (
                  <div className="absolute z-20 mt-1 w-full bg-white rounded-xl border shadow-xl overflow-hidden max-h-72 overflow-y-auto">
                    {gestorSugestoes.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => selecionarClienteGestor(c)}
                        className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b last:border-b-0"
                      >
                        <p className="text-sm font-medium text-gray-900">
                          {c.nome}
                        </p>
                        <p className="text-xs text-gray-400">
                          {c.cpf ? `CPF: ${c.cpf}` : ""}
                          {c.cpf && c.telefone ? " Ã‚Â· " : ""}
                          {c.telefone || ""}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* MODO: POR CAMPANHA */}
            {gestorModo === "campanha" && (
              <div className="flex gap-3 flex-wrap items-center">
                <select
                  value={gestorCampanhaTipo}
                  onChange={(e) => setGestorCampanhaTipo(e.target.value)}
                  className="border rounded-lg px-3 py-2 text-sm min-w-[200px]"
                >
                  <option value="carimbos">Ã°Å¸ÂÂ·Ã¯Â¸Â CartÃƒÂ£o Fidelidade</option>
                  <option value="cashback">Ã°Å¸â€™Â° Cashback (saldo positivo)</option>
                  <option value="cupons">Ã°Å¸Å½Å¸Ã¯Â¸Â Cupons Ativos</option>
                  <option value="ranking">Ã°Å¸Ââ€  Ranking (mÃƒÂªs atual)</option>
                </select>
                <button
                  onClick={() =>
                    carregarClientesPorCampanha(gestorCampanhaTipo)
                  }
                  disabled={gestorCampanhaCarregando}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {gestorCampanhaCarregando
                    ? "Carregando..."
                    : "Buscar Clientes"}
                </button>
              </div>
            )}
          </div>

          {/* LISTA DE CLIENTES POR CAMPANHA */}
          {gestorModo === "campanha" && gestorCampanhaCarregando && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando clientes...</p>
            </div>
          )}
          {gestorModo === "campanha" &&
            gestorCampanhaLista !== null &&
            !gestorCampanhaCarregando && (
              <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-6 py-3 bg-gray-50 border-b flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700">
                    {gestorCampanhaLista.length === 0
                      ? "Nenhum cliente encontrado"
                      : `${gestorCampanhaLista.length} cliente(s) encontrado(s)`}
                  </p>
                  <p className="text-xs text-gray-400">
                    Clique em Ã¢â‚¬Å“Ver detalhesÃ¢â‚¬Â para gerenciar
                  </p>
                </div>
                {gestorCampanhaLista.length === 0 ? (
                  <div className="p-10 text-center text-gray-400 text-sm">
                    Nenhum cliente ativo neste tipo de campanha.
                  </div>
                ) : (
                  <div className="divide-y max-h-[600px] overflow-y-auto">
                    {gestorCampanhaLista.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-center gap-4 px-6 py-3 hover:bg-gray-50 transition-colors"
                      >
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-sm shrink-0">
                          {c.nome?.[0]?.toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {c.nome}
                          </p>
                          <p className="text-xs text-gray-400">
                            {c.cpf ? `CPF: ${c.cpf}` : ""}
                            {c.cpf && c.telefone ? " Ã‚Â· " : ""}
                            {c.telefone || ""}
                          </p>
                        </div>
                        <span className="px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full font-medium shrink-0">
                          {c.detalhe}
                        </span>
                        <button
                          onClick={() => abrirClienteNoGestor(c)}
                          className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 font-medium shrink-0"
                        >
                          Ver detalhes Ã¢â€ â€™
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

          {/* LOADING E DETALHES DO CLIENTE (modo Por Cliente) */}
          {gestorModo === "cliente" && gestorCarregando && (
            <div className="text-center py-12 text-gray-400">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-sm">Carregando dados do cliente...</p>
            </div>
          )}

          {gestorModo === "cliente" &&
            gestorCliente &&
            gestorSaldo &&
            !gestorCarregando && (
              <>
                {/* CARD DO CLIENTE */}
                <div className="bg-white rounded-xl border shadow-sm p-4 flex items-center gap-4">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold text-lg shrink-0">
                    {gestorCliente.nome?.[0]?.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 truncate">
                      {gestorCliente.nome}
                    </p>
                    <p className="text-xs text-gray-400">
                      ID #{gestorCliente.id} Ã‚Â·{" "}
                      {gestorCliente.telefone ||
                        gestorCliente.celular ||
                        "Sem telefone"}
                    </p>
                  </div>
                  {(() => {
                    const r =
                      RANK_LABELS[gestorSaldo.rank_level] || RANK_LABELS.bronze;
                    return (
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium shrink-0 ${r.color}`}
                      >
                        {r.emoji} {r.label}
                      </span>
                    );
                  })()}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Carimbos Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(
                        gestorSecao === "carimbos" ? null : "carimbos",
                      )
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸ÂÂ·Ã¯Â¸Â</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">
                          CartÃƒÂ£o Fidelidade
                        </p>
                        <p className="text-xs text-gray-500">
                          {gestorSaldo.total_carimbos} carimbo(s) ativo(s)
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "carimbos" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "carimbos" && (
                    <div className="border-t p-6 space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <p className="text-sm font-medium text-green-800 mb-3">
                          Ã¢Å¾â€¢ LanÃƒÂ§ar Carimbo Manual
                        </p>
                        <div className="flex gap-3 flex-wrap items-end">
                          <div className="flex-1 min-w-[200px]">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              ObservaÃƒÂ§ÃƒÂ£o (opcional)
                            </label>
                            <input
                              type="text"
                              value={gestorCarimboNota}
                              onChange={(e) =>
                                setGestorCarimboNota(e.target.value)
                              }
                              placeholder="Ex: ConversÃƒÂ£o de cartÃƒÂ£o fÃƒÂ­sico"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                          <button
                            onClick={lancarCarimboGestor}
                            disabled={gestorLancandoCarimbo}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                          >
                            {gestorLancandoCarimbo
                              ? "LanÃƒÂ§ando..."
                              : "Ã¢Å“â€¦ LanÃƒÂ§ar Carimbo"}
                          </button>
                        </div>
                      </div>
                      {gestorCarimbos && gestorCarimbos.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50">
                              <tr>
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
                                  AÃƒÂ§ÃƒÂ£o
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y">
                              {gestorCarimbos
                                .filter(
                                  (s) =>
                                    !s.voided_at || gestorIncluirEstornados,
                                )
                                .map((s) => (
                                  <tr
                                    key={s.id}
                                    className={
                                      s.voided_at
                                        ? "bg-red-50 opacity-60"
                                        : "hover:bg-gray-50"
                                    }
                                  >
                                    <td className="px-4 py-2 text-gray-500 font-mono text-xs">
                                      {s.id}
                                    </td>
                                    <td className="px-4 py-2 text-gray-700 text-xs whitespace-nowrap">
                                      {new Date(s.created_at).toLocaleString(
                                        "pt-BR",
                                      )}
                                    </td>
                                    <td className="px-4 py-2">
                                      {s.is_manual ? (
                                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                                          Manual
                                        </span>
                                      ) : (
                                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                                          AutomÃƒÂ¡tico
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-gray-500 text-xs max-w-[180px] truncate">
                                      {s.notes || "Ã¢â‚¬â€"}
                                    </td>
                                    <td className="px-4 py-2 text-center">
                                      {s.voided_at ? (
                                        <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                                          Estornado
                                        </span>
                                      ) : (
                                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                                          Ativo
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 text-center">
                                      {!s.voided_at && (
                                        <button
                                          onClick={() =>
                                            estornarCarimboGestor(s.id)
                                          }
                                          disabled={gestorRemovendo === s.id}
                                          className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                                        >
                                          {gestorRemovendo === s.id
                                            ? "..."
                                            : "Ã¢ÂÅ’ Remover"}
                                        </button>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
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
                          onChange={(e) =>
                            setGestorIncluirEstornados(e.target.checked)
                          }
                          className="rounded"
                        />
                        Mostrar estornados
                      </label>
                    </div>
                  )}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Cashback Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(
                        gestorSecao === "cashback" ? null : "cashback",
                      )
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸â€™Â°</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cashback</p>
                        <p className="text-xs text-gray-500">
                          Saldo: R$ {formatBRL(gestorSaldo.saldo_cashback)}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cashback" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "cashback" && (
                    <div className="border-t p-6 space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                        <p className="text-xs text-gray-500 mb-1">
                          Saldo atual
                        </p>
                        <p className="text-3xl font-bold text-green-700">
                          R$ {formatBRL(gestorSaldo.saldo_cashback)}
                        </p>
                      </div>
                      <div
                        className={`border rounded-lg p-4 space-y-3 ${gestorCashbackTipo === "debito" ? "bg-red-50 border-red-200" : "bg-blue-50 border-blue-200"}`}
                      >
                        <p className="text-sm font-medium text-gray-700">
                          Ã¢Å“ÂÃ¯Â¸Â Ajuste Manual
                        </p>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Tipo
                            </label>
                            <select
                              value={gestorCashbackTipo}
                              onChange={(e) =>
                                setGestorCashbackTipo(e.target.value)
                              }
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            >
                              <option value="credito">
                                Ã¢Å¾â€¢ CrÃƒÂ©dito (adicionar)
                              </option>
                              <option value="debito">
                                Ã¢Å¾â€“ DÃƒÂ©bito (remover)
                              </option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Valor (R$)
                            </label>
                            <input
                              type="number"
                              min="0.01"
                              step="0.01"
                              value={gestorCashbackValor}
                              onChange={(e) =>
                                setGestorCashbackValor(e.target.value)
                              }
                              placeholder="0,00"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                          <div className="col-span-2">
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              Motivo (opcional)
                            </label>
                            <input
                              type="text"
                              value={gestorCashbackDesc}
                              onChange={(e) =>
                                setGestorCashbackDesc(e.target.value)
                              }
                              placeholder="Ex: CorreÃƒÂ§ÃƒÂ£o de campanha"
                              className="w-full border rounded-lg px-3 py-2 text-sm"
                            />
                          </div>
                        </div>
                        <button
                          onClick={ajustarCashbackGestor}
                          disabled={
                            gestorLancandoCashback || !gestorCashbackValor
                          }
                          className={`w-full py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 ${gestorCashbackTipo === "debito" ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"}`}
                        >
                          {gestorLancandoCashback
                            ? "Salvando..."
                            : gestorCashbackTipo === "debito"
                              ? "Ã¢Å¾â€“ Confirmar DÃƒÂ©bito"
                              : "Ã¢Å¾â€¢ Confirmar CrÃƒÂ©dito"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Cupons Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(gestorSecao === "cupons" ? null : "cupons")
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸Å½Å¸Ã¯Â¸Â</span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Cupons</p>
                        <p className="text-xs text-gray-500">
                          {gestorCupons?.filter((c) => c.status === "active")
                            .length || 0}{" "}
                          ativo(s) Ã‚Â· {gestorCupons?.length || 0} no total
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "cupons" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "cupons" && (
                    <div className="border-t">
                      {gestorCupons && gestorCupons.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                                  CÃƒÂ³digo
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                                  Desconto
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-600">
                                  Validade
                                </th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">
                                  Status
                                </th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-gray-600">
                                  AÃƒÂ§ÃƒÂ£o
                                </th>
                              </tr>
                            </thead>
                            <tbody className="divide-y">
                              {gestorCupons.map((c) => (
                                <tr
                                  key={c.id}
                                  className={
                                    c.status !== "active"
                                      ? "bg-gray-50 opacity-70"
                                      : "hover:bg-gray-50"
                                  }
                                >
                                  <td className="px-4 py-3 font-mono text-xs font-bold text-gray-800">
                                    {c.code}
                                  </td>
                                  <td className="px-4 py-3 text-xs text-gray-700">
                                    {c.coupon_type === "gift"
                                      ? "Ã°Å¸Å½Â Brinde"
                                      : c.coupon_type === "percent"
                                        ? `${c.discount_percent}%`
                                        : `R$ ${formatBRL(c.discount_value)}`}
                                  </td>
                                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                                    {c.valid_until
                                      ? new Date(
                                          c.valid_until,
                                        ).toLocaleDateString("pt-BR")
                                      : "Indeterminado"}
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span
                                      className={`px-2 py-0.5 text-xs rounded-full ${CUPOM_STATUS[c.status]?.color || "bg-gray-100 text-gray-600"}`}
                                    >
                                      {CUPOM_STATUS[c.status]?.label ||
                                        c.status}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    {c.status === "active" && (
                                      <button
                                        onClick={() =>
                                          anularCupomGestor(c.code)
                                        }
                                        disabled={gestorAnulando === c.code}
                                        className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 disabled:opacity-50"
                                      >
                                        {gestorAnulando === c.code
                                          ? "..."
                                          : "Ã°Å¸Å¡Â« Anular"}
                                      </button>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-8 text-center text-gray-400 text-sm">
                          Nenhum cupom encontrado.
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Ã¢â€â‚¬Ã¢â€â‚¬ SeÃƒÂ§ÃƒÂ£o: Ranking Ã¢â€â‚¬Ã¢â€â‚¬ */}
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <button
                    onClick={() =>
                      setGestorSecao(
                        gestorSecao === "ranking" ? null : "ranking",
                      )
                    }
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">Ã°Å¸Ââ€ </span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-800">Ranking</p>
                        <p className="text-xs text-gray-500">
                          {(() => {
                            const r =
                              RANK_LABELS[gestorSaldo.rank_level] ||
                              RANK_LABELS.bronze;
                            return `${r.emoji} ${r.label}`;
                          })()}
                          {gestorSaldo.rank_period
                            ? ` Ã‚Â· ${gestorSaldo.rank_period}`
                            : ""}
                        </p>
                      </div>
                    </div>
                    <span className="text-gray-400 text-sm">
                      {gestorSecao === "ranking" ? "Ã¢â€“Â²" : "Ã¢â€“Â¼"}
                    </span>
                  </button>
                  {gestorSecao === "ranking" && (
                    <div className="border-t p-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          {
                            label: "NÃƒÂ­vel",
                            value: (() => {
                              const r =
                                RANK_LABELS[gestorSaldo.rank_level] ||
                                RANK_LABELS.bronze;
                              return `${r.emoji} ${r.label}`;
                            })(),
                          },
                          {
                            label: "PerÃƒÂ­odo",
                            value: gestorSaldo.rank_period || "Ã¢â‚¬â€",
                          },
                          {
                            label: "Total Gasto (12m)",
                            value: `R$ ${formatBRL(gestorSaldo.rank_total_spent || 0)}`,
                          },
                          {
                            label: "Compras (12m)",
                            value: String(
                              gestorSaldo.rank_total_purchases || 0,
                            ),
                          },
                        ].map((item) => (
                          <div
                            key={item.label}
                            className="bg-gray-50 rounded-lg p-3 text-center"
                          >
                            <p className="text-xs text-gray-500 mb-1">
                              {item.label}
                            </p>
                            <p className="font-semibold text-gray-800 text-sm">
                              {item.value}
                            </p>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-400 mt-4 text-center">
                        O nÃƒÂ­vel de ranking ÃƒÂ© recalculado automaticamente no dia
                        1 de cada mÃƒÂªs.
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}
        </div>
  );
}
