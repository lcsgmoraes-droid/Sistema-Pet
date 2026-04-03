export default function CampanhasModalsLayer(props) {
  const {
    modalEnvioInativos,
    setModalEnvioInativos,
    resultadoEnvioInativos,
    setResultadoEnvioInativos,
    envioInativosForm,
    setEnvioInativosForm,
    enviandoInativos,
    enviarParaInativos,
    modalSorteio,
    setModalSorteio,
    novoSorteio,
    setNovoSorteio,
    erroCriarSorteio,
    criarSorteio,
    criandoSorteio,
    modalCodigosOffline,
    setModalCodigosOffline,
    loadingCodigosOffline,
    codigosOffline,
    RANK_LABELS,
    fidModalManual,
    setFidModalManual,
    fidClienteId,
    fidManualNota,
    setFidManualNota,
    lancarCarimboManual,
    fidLancandoManual,
    modalLote,
    setModalLote,
    loteForm,
    setLoteForm,
    resultadoLote,
    enviarLote,
    enviandoLote,
    modalCriarCampanha,
    setModalCriarCampanha,
    novaCampanha,
    setNovaCampanha,
    erroCriarCampanha,
    criarCampanha,
    criandoCampanha,
    modalCupomAberto,
    setModalCupomAberto,
    setErroCupom,
    novoCupom,
    setNovoCupom,
    erroCupom,
    criarCupomManual,
    criandoCupom,
  } = props;

  return (
    <>
      {modalEnvioInativos && (
              <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        Ã¢Å“â€°Ã¯Â¸Â Enviar e-mail de reativaÃƒÂ§ÃƒÂ£o
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Clientes sem compra hÃƒÂ¡ mais de {modalEnvioInativos} dias Ã‚Â· Os
                        e-mails sÃƒÂ£o enfileirados e enviados em lotes
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setModalEnvioInativos(null);
                        setResultadoEnvioInativos(null);
                      }}
                      className="text-gray-400 hover:text-gray-600 text-xl font-bold"
                    >
                      Ãƒâ€”
                    </button>
                  </div>
                  <div className="p-6 space-y-4">
                    {resultadoEnvioInativos ? (
                      <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-1">
                        <p className="font-semibold text-green-800">
                          Ã¢Å“â€¦ E-mails enfileirados com sucesso!
                        </p>
                        <p className="text-sm text-green-700">
                          {resultadoEnvioInativos.enfileirados} e-mail(s)
                          adicionado(s) ÃƒÂ  fila.
                        </p>
                        {resultadoEnvioInativos.sem_email > 0 && (
                          <p className="text-xs text-gray-500">
                            {resultadoEnvioInativos.sem_email} cliente(s) nÃƒÂ£o tÃƒÂªm
                            e-mail cadastrado e foram ignorados.
                          </p>
                        )}
                        <button
                          onClick={() => {
                            setModalEnvioInativos(null);
                            setResultadoEnvioInativos(null);
                          }}
                          className="mt-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                        >
                          Fechar
                        </button>
                      </div>
                    ) : (
                      <>
                        <div>
                          <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                            Assunto do e-mail
                          </label>
                          <input
                            type="text"
                            value={envioInativosForm.assunto}
                            onChange={(e) =>
                              setEnvioInativosForm((f) => ({
                                ...f,
                                assunto: e.target.value,
                              }))
                            }
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
                            placeholder="Ex: Sentimos sua falta! Ã°Å¸ÂÂ¾"
                          />
                        </div>
                        <div>
                          <label className="text-xs font-semibold text-gray-500 uppercase block mb-1">
                            Mensagem
                          </label>
                          <textarea
                            rows={5}
                            value={envioInativosForm.mensagem}
                            onChange={(e) =>
                              setEnvioInativosForm((f) => ({
                                ...f,
                                mensagem: e.target.value,
                              }))
                            }
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300 resize-none"
                            placeholder="Escreva a mensagem para os clientes inativos..."
                          />
                        </div>
                        <div className="flex gap-2 pt-1">
                          <button
                            onClick={() => setModalEnvioInativos(null)}
                            className="flex-1 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50"
                          >
                            Cancelar
                          </button>
                          <button
                            onClick={enviarParaInativos}
                            disabled={
                              enviandoInativos ||
                              !envioInativosForm.assunto.trim() ||
                              !envioInativosForm.mensagem.trim()
                            }
                            className="flex-1 py-2.5 bg-orange-500 text-white rounded-lg text-sm font-semibold hover:bg-orange-600 disabled:opacity-50 transition-colors"
                          >
                            {enviandoInativos
                              ? "Enfileirando..."
                              : "Ã¢Å“â€°Ã¯Â¸Â Enfileirar e-mails"}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Ã¢â€â‚¬Ã¢â€â‚¬ ABA: CAMPANHAS Ã¢â€â‚¬Ã¢â€â‚¬ */}

      {modalSorteio && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">Ã°Å¸Å½Â² Novo Sorteio</h3>
                    <button
                      onClick={() => setModalSorteio(false)}
                      className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                      Ãƒâ€”
                    </button>
                  </div>
                  <div className="px-6 py-4 space-y-3">
                    <div>
                      <label
                        htmlFor="s-nome"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Nome do sorteio
                      </label>
                      <input
                        id="s-nome"
                        type="text"
                        placeholder="Ex: Sorteio de MarÃƒÂ§o"
                        value={novoSorteio.name}
                        onChange={(e) =>
                          setNovoSorteio((p) => ({ ...p, name: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="s-premio"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        PrÃƒÂªmio
                      </label>
                      <input
                        id="s-premio"
                        type="text"
                        placeholder="Ex: Kit banho + tosa grÃƒÂ¡tis"
                        value={novoSorteio.prize_description}
                        onChange={(e) =>
                          setNovoSorteio((p) => ({
                            ...p,
                            prize_description: e.target.value,
                          }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="s-nivel"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        NÃƒÂ­vel mÃƒÂ­nimo elegantÃƒÂ­vel (opcional)
                      </label>
                      <select
                        id="s-nivel"
                        value={novoSorteio.rank_filter}
                        onChange={(e) =>
                          setNovoSorteio((p) => ({
                            ...p,
                            rank_filter: e.target.value,
                          }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="">Todos os clientes</option>
                        <option value="bronze">Ã°Å¸Â¥â€° Bronze+</option>
                        <option value="silver">Ã°Å¸Â¥Ë† Prata+</option>
                        <option value="gold">Ã°Å¸Â¥â€¡ Ouro+</option>
                        <option value="platinum">Ã°Å¸â€™Å½ Diamante+</option>
                        <option value="diamond">Ã°Å¸â€˜â€˜ Platina</option>
                      </select>
                    </div>
                    <div>
                      <label
                        htmlFor="s-data"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Data do sorteio (opcional)
                      </label>
                      <input
                        id="s-data"
                        type="date"
                        value={novoSorteio.draw_date}
                        onChange={(e) =>
                          setNovoSorteio((p) => ({ ...p, draw_date: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="s-desc"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        DescriÃƒÂ§ÃƒÂ£o (opcional)
                      </label>
                      <textarea
                        id="s-desc"
                        rows={2}
                        value={novoSorteio.description}
                        onChange={(e) =>
                          setNovoSorteio((p) => ({
                            ...p,
                            description: e.target.value,
                          }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={novoSorteio.auto_execute}
                        onChange={(e) =>
                          setNovoSorteio((p) => ({
                            ...p,
                            auto_execute: e.target.checked,
                          }))
                        }
                        className="w-4 h-4 rounded"
                      />
                      <span className="text-sm text-gray-700">
                        Ã°Å¸Â¤â€“ Executar automaticamente na data do sorteio
                      </span>
                    </label>
                    {erroCriarSorteio && (
                      <p className="text-sm text-red-600">{erroCriarSorteio}</p>
                    )}
                  </div>
                  <div className="px-6 py-4 border-t flex gap-3 justify-end">
                    <button
                      onClick={() => setModalSorteio(false)}
                      className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={criarSorteio}
                      disabled={criandoSorteio}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
                    >
                      {criandoSorteio ? "Criando..." : "Criar Sorteio"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: CÃƒâ€œDIGOS OFFLINE (SORTEIO) Ã¢â€â‚¬Ã¢â€â‚¬ */}

      {modalCodigosOffline && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        Ã°Å¸â€œâ€¹ CÃƒÂ³digos Offline Ã¢â‚¬â€ {modalCodigosOffline.name}
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Lista de participantes para sorteio fÃƒÂ­sico
                      </p>
                    </div>
                    <div className="flex gap-2 items-center">
                      <button
                        onClick={() => window.print()}
                        className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200"
                      >
                        Ã°Å¸â€“Â¨Ã¯Â¸Â Imprimir
                      </button>
                      <button
                        onClick={() => setModalCodigosOffline(null)}
                        className="text-gray-400 hover:text-gray-600 text-xl ml-2"
                      >
                        Ãƒâ€”
                      </button>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto px-6 py-4">
                    {loadingCodigosOffline ? (
                      <div className="text-center text-gray-400 py-8">
                        Carregando...
                      </div>
                    ) : codigosOffline.length === 0 ? (
                      <div className="text-center text-gray-400 py-8">
                        Nenhum participante encontrado.
                      </div>
                    ) : (
                      <table className="w-full text-sm border-collapse">
                        <thead>
                          <tr className="bg-gray-50 text-gray-600 text-xs uppercase">
                            <th className="text-center p-2 border-b w-16">NÃ‚Âº</th>
                            <th className="text-left p-2 border-b">Cliente</th>
                            <th className="text-center p-2 border-b">NÃƒÂ­vel</th>
                          </tr>
                        </thead>
                        <tbody>
                          {codigosOffline.map((c) => (
                            <tr
                              key={c.numero}
                              className="border-b last:border-0 hover:bg-gray-50"
                            >
                              <td className="p-2 text-center font-mono font-semibold text-gray-700">
                                {c.numero}
                              </td>
                              <td className="p-2 text-gray-700">
                                {c.nome || `Cliente #${c.customer_id}`}
                              </td>
                              <td className="p-2 text-center text-xs text-gray-500">
                                {c.rank_level
                                  ? `${RANK_LABELS[c.rank_level]?.emoji || ""} ${RANK_LABELS[c.rank_level]?.label || c.rank_level}`
                                  : "Ã¢â‚¬â€"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                  <div className="px-6 py-3 border-t text-xs text-gray-400">
                    {codigosOffline.length} participante(s) Ã‚Â· Sorteio:{" "}
                    {modalCodigosOffline.name}
                  </div>
                </div>
              </div>
            )}

            {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: LANÃƒâ€¡AR CARIMBO MANUAL Ã¢â€â‚¬Ã¢â€â‚¬ */}

      {fidModalManual && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">
                      Ã°Å¸ÂÂ·Ã¯Â¸Â LanÃƒÂ§ar Carimbo Manual
                    </h3>
                    <button
                      onClick={() => setFidModalManual(false)}
                      className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                      Ãƒâ€”
                    </button>
                  </div>
                  <div className="px-6 py-4 space-y-3">
                    <p className="text-sm text-gray-500">
                      Cliente <strong>#{fidClienteId}</strong> Ã¢â‚¬â€ Esse carimbo serÃƒÂ¡
                      registrado como manual (sem vÃƒÂ­nculo com uma venda).
                    </p>
                    <div>
                      <label
                        htmlFor="fid-nota"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        ObservaÃƒÂ§ÃƒÂ£o (opcional)
                      </label>
                      <input
                        id="fid-nota"
                        type="text"
                        value={fidManualNota}
                        onChange={(e) => setFidManualNota(e.target.value)}
                        placeholder="Ex: ConversÃƒÂ£o de cartÃƒÂ£o fÃƒÂ­sico"
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                  <div className="px-6 py-4 border-t flex gap-3 justify-end">
                    <button
                      onClick={() => setFidModalManual(false)}
                      className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={lancarCarimboManual}
                      disabled={fidLancandoManual}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                    >
                      {fidLancandoManual ? "LanÃƒÂ§ando..." : "Confirmar Carimbo"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: ENVIO EM LOTE Ã¢â€â‚¬Ã¢â€â‚¬ */}

      {modalLote && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">Ã°Å¸â€œÂ§ Envio em Lote</h3>
                    <button
                      onClick={() => setModalLote(false)}
                      className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                      Ãƒâ€”
                    </button>
                  </div>
                  <div className="px-6 py-4 space-y-3">
                    <div>
                      <label
                        htmlFor="lote-nivel"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        NÃƒÂ­vel de ranking
                      </label>
                      <select
                        id="lote-nivel"
                        value={loteForm.nivel}
                        onChange={(e) =>
                          setLoteForm((p) => ({ ...p, nivel: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="todos">Todos os nÃƒÂ­veis</option>
                        <option value="platinum">Ã°Å¸â€™Å½ Diamante</option>
                        <option value="diamond">Ã°Å¸â€˜â€˜ Platina</option>
                        <option value="gold">Ã°Å¸Â¥â€¡ Ouro</option>
                        <option value="silver">Ã°Å¸Â¥Ë† Prata</option>
                        <option value="bronze">Ã°Å¸Â¥â€° Bronze</option>
                      </select>
                    </div>
                    <div>
                      <label
                        htmlFor="lote-assunto"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Assunto do e-mail
                      </label>
                      <input
                        id="lote-assunto"
                        type="text"
                        placeholder="Ex: PromoÃƒÂ§ÃƒÂ£o exclusiva para clientes Ouro!"
                        value={loteForm.assunto}
                        onChange={(e) =>
                          setLoteForm((p) => ({ ...p, assunto: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="lote-msg"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Mensagem
                      </label>
                      <textarea
                        id="lote-msg"
                        rows={4}
                        placeholder="Escreva a mensagem que serÃƒÂ¡ enviada para os clientes..."
                        value={loteForm.mensagem}
                        onChange={(e) =>
                          setLoteForm((p) => ({ ...p, mensagem: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    {resultadoLote && (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
                        <p className="font-semibold text-green-800">
                          Ã¢Å“â€¦ {resultadoLote.enfileirados} e-mail(s) enfileirado(s)!
                        </p>
                        {resultadoLote.sem_email > 0 && (
                          <p className="text-green-600">
                            {resultadoLote.sem_email} cliente(s) sem e-mail cadastrado
                            foram ignorados.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="px-6 py-4 border-t flex gap-3 justify-end">
                    <button
                      onClick={() => setModalLote(false)}
                      className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
                    >
                      Fechar
                    </button>
                    <button
                      onClick={enviarLote}
                      disabled={enviandoLote}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {enviandoLote ? "Enviando..." : "Enfileirar Envio"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: NOVA CAMPANHA Ã¢â€â‚¬Ã¢â€â‚¬ */}

      {modalCriarCampanha && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">Ã¢Å¾â€¢ Nova Campanha</h3>
                    <button
                      onClick={() => setModalCriarCampanha(false)}
                      className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                      Ãƒâ€”
                    </button>
                  </div>
                  <div className="px-6 py-4 space-y-4">
                    <div>
                      <label
                        htmlFor="nc-nome"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Nome da campanha
                      </label>
                      <input
                        id="nc-nome"
                        type="text"
                        placeholder="Ex: Recompra RÃƒÂ¡pida VerÃƒÂ£o"
                        value={novaCampanha.name}
                        onChange={(e) =>
                          setNovaCampanha((p) => ({ ...p, name: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="nc-tipo"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Tipo
                      </label>
                      <select
                        id="nc-tipo"
                        value={novaCampanha.campaign_type}
                        onChange={(e) =>
                          setNovaCampanha((p) => ({
                            ...p,
                            campaign_type: e.target.value,
                          }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="inactivity">Ã°Å¸ËœÂ´ Clientes Inativos</option>
                        <option value="quick_repurchase">Ã°Å¸â€Â Recompra RÃƒÂ¡pida</option>
                      </select>
                    </div>
                    <p className="text-xs text-gray-500">
                      Os parÃƒÂ¢metros poderÃƒÂ£o ser configurados depois de criar a
                      campanha.
                    </p>
                    {erroCriarCampanha && (
                      <p className="text-sm text-red-600">{erroCriarCampanha}</p>
                    )}
                  </div>
                  <div className="px-6 py-4 border-t flex gap-3 justify-end">
                    <button
                      onClick={() => setModalCriarCampanha(false)}
                      className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={criarCampanha}
                      disabled={criandoCampanha}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {criandoCampanha ? "Criando..." : "Criar Campanha"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Ã¢â€â‚¬Ã¢â€â‚¬ MODAL: CRIAR CUPOM MANUAL Ã¢â€â‚¬Ã¢â€â‚¬ */}

      {modalCupomAberto && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
                  <div className="px-6 py-4 border-b flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">
                      Ã°Å¸Å½Å¸Ã¯Â¸Â Criar Cupom Manual
                    </h3>
                    <button
                      onClick={() => {
                        setModalCupomAberto(false);
                        setErroCupom("");
                      }}
                      className="text-gray-400 hover:text-gray-600 text-xl"
                    >
                      Ãƒâ€”
                    </button>
                  </div>
                  <div className="px-6 py-4 space-y-3">
                    <div>
                      <label
                        htmlFor="cupom-tipo"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Tipo de desconto
                      </label>
                      <select
                        id="cupom-tipo"
                        value={novoCupom.coupon_type}
                        onChange={(e) =>
                          setNovoCupom((p) => ({ ...p, coupon_type: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="fixed">Valor fixo (R$)</option>
                        <option value="percent">Percentual (%)</option>
                        <option value="gift">Brinde (sem valor)</option>
                      </select>
                    </div>
                    {novoCupom.coupon_type === "fixed" && (
                      <div>
                        <label
                          htmlFor="cupom-valor"
                          className="block text-xs font-medium text-gray-600 mb-1"
                        >
                          Valor do desconto (R$)
                        </label>
                        <input
                          id="cupom-valor"
                          type="text"
                          placeholder="Ex: 20,00"
                          value={novoCupom.discount_value}
                          onChange={(e) =>
                            setNovoCupom((p) => ({
                              ...p,
                              discount_value: e.target.value,
                            }))
                          }
                          className="w-full border rounded-lg px-3 py-2 text-sm"
                        />
                      </div>
                    )}
                    {novoCupom.coupon_type === "percent" && (
                      <div>
                        <label
                          htmlFor="cupom-pct"
                          className="block text-xs font-medium text-gray-600 mb-1"
                        >
                          Percentual (%)
                        </label>
                        <input
                          id="cupom-pct"
                          type="number"
                          min="1"
                          max="100"
                          placeholder="Ex: 10"
                          value={novoCupom.discount_percent}
                          onChange={(e) =>
                            setNovoCupom((p) => ({
                              ...p,
                              discount_percent: e.target.value,
                            }))
                          }
                          className="w-full border rounded-lg px-3 py-2 text-sm"
                        />
                      </div>
                    )}
                    <div>
                      <label
                        htmlFor="cupom-canal"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Canal
                      </label>
                      <select
                        id="cupom-canal"
                        value={novoCupom.channel}
                        onChange={(e) =>
                          setNovoCupom((p) => ({ ...p, channel: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      >
                        <option value="pdv">PDV (caixa)</option>
                        <option value="ecommerce">E-commerce</option>
                        <option value="app">App</option>
                      </select>
                    </div>
                    <div>
                      <label
                        htmlFor="cupom-validade"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        VÃƒÂ¡lido atÃƒÂ© (opcional)
                      </label>
                      <input
                        id="cupom-validade"
                        type="date"
                        value={novoCupom.valid_until}
                        onChange={(e) =>
                          setNovoCupom((p) => ({ ...p, valid_until: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="cupom-mincompra"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        Compra mÃƒÂ­nima (R$, opcional)
                      </label>
                      <input
                        id="cupom-mincompra"
                        type="text"
                        placeholder="Ex: 50,00"
                        value={novoCupom.min_purchase_value}
                        onChange={(e) =>
                          setNovoCupom((p) => ({
                            ...p,
                            min_purchase_value: e.target.value,
                          }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="cupom-cliente"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        ID do cliente (opcional)
                      </label>
                      <input
                        id="cupom-cliente"
                        type="number"
                        placeholder="Deixe vazio para cupom genÃƒÂ©rico"
                        value={novoCupom.customer_id}
                        onChange={(e) =>
                          setNovoCupom((p) => ({ ...p, customer_id: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="cupom-descricao"
                        className="block text-xs font-medium text-gray-600 mb-1"
                      >
                        DescriÃƒÂ§ÃƒÂ£o (opcional)
                      </label>
                      <input
                        id="cupom-descricao"
                        type="text"
                        placeholder="Ex: Cupom de cortesia"
                        value={novoCupom.descricao}
                        onChange={(e) =>
                          setNovoCupom((p) => ({ ...p, descricao: e.target.value }))
                        }
                        className="w-full border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    {erroCupom && <p className="text-red-600 text-sm">{erroCupom}</p>}
                  </div>
                  <div className="px-6 py-4 border-t flex gap-3 justify-end">
                    <button
                      onClick={() => {
                        setModalCupomAberto(false);
                        setErroCupom("");
                      }}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200"
                    >
                      Cancelar
                    </button>
                    <button
                      onClick={criarCupomManual}
                      disabled={criandoCupom}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {criandoCupom ? "Criando..." : "Criar Cupom"}
                    </button>
                  </div>
                </div>
              </div>
            )}

    </>
  );
}
