import { ChevronDown, ChevronUp, Zap } from "lucide-react";
import { Link } from "react-router-dom";

import { formatarChave, formatarDataHora, tratarColagemChave } from "./centralNFSaidaUtils";

export default function SefazToolsPanel({
  painelSefazAberto,
  setPainelSefazAberto,
  consultarChave,
  chave,
  setChave,
  consultando,
  erroConsulta,
  cfgLoading,
  cfg,
  setCfg,
  msgRotina,
  salvarRotina,
  salvandoRotina,
  sincronizarAgora,
  sincronizando,
}) {
  return (
    <div className="bg-white rounded-xl border border-purple-200 mb-6 overflow-hidden">
      <button
        type="button"
        onClick={() => setPainelSefazAberto((aberto) => !aberto)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-purple-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-600" />
          <span className="font-semibold text-gray-800">Ferramentas SEFAZ</span>
          <span className="text-xs text-gray-500 ml-1">
            (consulta por chave · rotina automática)
          </span>
        </div>
        {painelSefazAberto ? (
          <ChevronUp className="w-5 h-5 text-gray-500" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" />
        )}
      </button>

      {painelSefazAberto && (
        <div className="border-t border-purple-100 p-5 space-y-5">
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">
              Consultar NF-e por chave de acesso
            </p>
            <p className="text-xs text-gray-500 mb-3">
              A configuração do certificado e ambiente fica em{" "}
              <Link to="/configuracoes/integracoes" className="text-indigo-600 font-semibold">
                Configurações → Integrações
              </Link>
              .
            </p>
            <form onSubmit={consultarChave} className="flex gap-3">
              <input
                type="text"
                value={chave}
                onChange={(event) => setChave(formatarChave(event.target.value))}
                onPaste={(event) => tratarColagemChave(event, setChave)}
                placeholder="44 dígitos — Ex: 35250112345678000195550010000001231234567890"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                maxLength={80}
              />
              <button
                type="submit"
                disabled={consultando || chave.length !== 44}
                className="px-5 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {consultando ? "Consultando..." : "Consultar"}
              </button>
            </form>
            <p className="text-xs text-gray-400 mt-1">{chave.length}/44 dígitos</p>
            {erroConsulta && (
              <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {erroConsulta}
              </div>
            )}
          </div>

          <div className="border-t border-gray-100 pt-4">
            <p className="text-sm font-semibold text-gray-700 mb-3">
              Rotina automática de sincronização
            </p>
            {cfgLoading ? (
              <p className="text-sm text-gray-500">Carregando...</p>
            ) : (
              <div className="space-y-3">
                {(!cfg.enabled || !cfg.cert_ok) && (
                  <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm">
                    Integração ainda não está pronta para rotina automática. Finalize em
                    Configurações &gt; Integrações.
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input
                      type="checkbox"
                      checked={cfg.importacao_automatica}
                      onChange={(event) =>
                        setCfg((atual) => ({
                          ...atual,
                          importacao_automatica: event.target.checked,
                        }))
                      }
                    />
                    <span>Ativar sincronização automática</span>
                  </label>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Intervalo (minutos)
                    </label>
                    <input
                      type="number"
                      min={5}
                      value={cfg.importacao_intervalo_min}
                      onChange={(event) =>
                        setCfg((atual) => ({
                          ...atual,
                          importacao_intervalo_min: Number(event.target.value || 15),
                        }))
                      }
                      className="w-full border rounded-lg px-3 py-1.5 text-sm"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3">
                  <div>
                    Última sync: <strong>{formatarDataHora(cfg.ultimo_sync_at)}</strong>
                  </div>
                  <div>
                    Status: <strong>{cfg.ultimo_sync_status}</strong>
                  </div>
                  <div>
                    Documentos: <strong>{cfg.ultimo_sync_documentos}</strong>
                  </div>
                  <div>
                    Modo: <strong>{cfg.modo}</strong>
                  </div>
                  <div className="col-span-2">
                    Mensagem: <strong>{cfg.ultimo_sync_mensagem}</strong>
                  </div>
                </div>
                {msgRotina && (
                  <div className="text-sm bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-700">
                    {msgRotina}
                  </div>
                )}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={salvarRotina}
                    disabled={salvandoRotina}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60"
                  >
                    {salvandoRotina ? "Salvando..." : "Salvar rotina"}
                  </button>
                  <button
                    type="button"
                    onClick={sincronizarAgora}
                    disabled={sincronizando}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-60"
                  >
                    {sincronizando ? "Sincronizando..." : "Sincronizar agora"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
