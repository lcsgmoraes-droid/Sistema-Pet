import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { Save, Search } from 'lucide-react';
import ActionButton from '../ui/ActionButton';
import Panel from '../ui/Panel';

function formatarChaveAcesso(valor) {
  return String(valor).replaceAll(/\D/g, '').slice(0, 44);
}

export default function EntradaXmlSefazPanels({
  avisoConectorSefaz,
  chaveSefaz,
  cfgSefaz,
  configSefazLoading,
  consultaExpandidaId,
  consultasSefaz,
  consultarSefaz,
  erroSefaz,
  formatMoneyBRL,
  importandoConsultaId,
  loadingSefaz,
  mensagemRotina,
  mostrarConfigSefaz,
  mostrarPainelSefaz,
  salvarRotinaSefaz,
  salvandoRotina,
  setCfgSefaz,
  setChaveSefaz,
  setConsultaExpandidaId,
  usarNaEntrada,
}) {
  return (
    <>
      {mostrarPainelSefaz && (
        <Panel
          className="mb-6 border-l-4 border-l-emerald-500"
          padding="lg"
          title="Buscar NF-e pela SEFAZ"
        >
          <form onSubmit={consultarSefaz} className="mb-2 flex gap-3">
            <input
              type="text"
              value={chaveSefaz}
              onChange={(event) => setChaveSefaz(formatarChaveAcesso(event.target.value))}
              onPaste={(event) => {
                event.preventDefault();
                setChaveSefaz(formatarChaveAcesso(event.clipboardData?.getData('text') || ''));
              }}
              placeholder="Chave de acesso (44 digitos)"
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-mono text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500"
              maxLength={80}
            />
            <ActionButton
              type="submit"
              icon={Search}
              intent="create"
              size="md"
              loading={loadingSefaz}
              disabled={loadingSefaz || chaveSefaz.length !== 44}
            >
              {loadingSefaz ? 'Consultando...' : 'Consultar'}
            </ActionButton>
          </form>

          <p className="mb-3 text-xs text-gray-400">{chaveSefaz.length}/44 digitos</p>

          {erroSefaz && (
            <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {erroSefaz}
            </div>
          )}

          {avisoConectorSefaz && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <strong>Integracao validada, etapa final pendente:</strong> {avisoConectorSefaz}
            </div>
          )}

          {consultasSefaz.length > 0 && (
            <div className="mt-4 space-y-3">
              <p className="text-sm font-semibold text-gray-700">
                Consultas desta sessao ({consultasSefaz.length}):
              </p>
              {consultasSefaz.map((consulta) => {
                const expandida = consultaExpandidaId === consulta.id;
                const dados = consulta.dados;

                return (
                  <div key={consulta.id} className="overflow-hidden rounded-lg border border-gray-200">
                    <button
                      type="button"
                      onClick={() => setConsultaExpandidaId(expandida ? null : consulta.id)}
                      className="w-full px-4 py-3 text-left transition-colors hover:bg-gray-50"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-gray-800">
                          NF {dados.numero_nf}/{dados.serie} - {dados.emitente_nome}
                        </span>
                        <span className="text-xs text-gray-500">
                          {dados.itens?.length || 0} itens | {formatMoneyBRL(dados.valor_total_nf)}
                        </span>
                      </div>
                    </button>

                    <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 bg-gray-50 px-4 pb-3 pt-2">
                      <ActionButton
                        type="button"
                        intent="create"
                        tone="soft"
                        size="sm"
                        loading={importandoConsultaId === consulta.id}
                        disabled={importandoConsultaId === consulta.id}
                        onClick={() => usarNaEntrada(consulta)}
                      >
                        {importandoConsultaId === consulta.id ? 'Importando...' : 'Usar esta NF na Entrada'}
                      </ActionButton>
                    </div>

                    {expandida && dados.itens?.length > 0 && (
                      <div className="overflow-x-auto border-t border-gray-100 p-4">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-50 text-gray-600 uppercase">
                              <th className="px-2 py-1 text-left">Cod.</th>
                              <th className="px-2 py-1 text-left">Descricao</th>
                              <th className="px-2 py-1 text-right">Qtd</th>
                              <th className="px-2 py-1 text-right">Unit.</th>
                              <th className="px-2 py-1 text-right">Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {dados.itens.map((item) => (
                              <tr key={item.numero_item} className="hover:bg-gray-50">
                                <td className="px-2 py-1 font-mono">{item.codigo_produto}</td>
                                <td className="px-2 py-1">{item.descricao}</td>
                                <td className="px-2 py-1 text-right">{item.quantidade}</td>
                                <td className="px-2 py-1 text-right">{formatMoneyBRL(item.valor_unitario)}</td>
                                <td className="px-2 py-1 text-right font-semibold">
                                  {formatMoneyBRL(item.valor_total)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Panel>
      )}

      {mostrarConfigSefaz && (
        <Panel
          className="mb-6 border-l-4 border-l-slate-500"
          padding="lg"
          title="Configurar SEFAZ"
          subtitle={(
            <>
              Certificado digital e parametros ficam em{' '}
              <Link to="/configuracoes/integracoes" className="font-semibold text-indigo-600">
                Configuracoes &gt; Integracoes
              </Link>
              . Aqui configure apenas a rotina automatica.
            </>
          )}
        >
          {configSefazLoading ? (
            <p className="text-sm text-gray-500">Carregando configuracao...</p>
          ) : (
            <>
              {(!cfgSefaz.enabled || !cfgSefaz.cert_ok) && (
                <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  Integracao ainda nao esta pronta para rotina automatica. Finalize em Configuracoes &gt; Integracoes.
                </div>
              )}

              <div className="mb-4">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={cfgSefaz.importacao_automatica}
                    onChange={(event) => setCfgSefaz((prev) => ({
                      ...prev,
                      importacao_automatica: event.target.checked,
                    }))}
                  />
                  <span>Ativar importacao automatica</span>
                </label>
              </div>

              <div className="mb-4 grid grid-cols-1 gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600 sm:grid-cols-2">
                <div>
                  Ultima sincronizacao:{' '}
                  <strong>
                    {cfgSefaz.ultimo_sync_at
                      ? new Date(cfgSefaz.ultimo_sync_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })
                      : '-'}
                  </strong>
                </div>
                <div>Status: <strong>{cfgSefaz.ultimo_sync_status}</strong></div>
                <div>Documentos trazidos: <strong>{cfgSefaz.ultimo_sync_documentos}</strong></div>
                <div>Modo atual: <strong>{cfgSefaz.modo}</strong></div>
                <div className="sm:col-span-2">Mensagem: <strong>{cfgSefaz.ultimo_sync_mensagem}</strong></div>
              </div>

              {mensagemRotina && (
                <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
                  {mensagemRotina}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <ActionButton
                  type="button"
                  icon={Save}
                  intent="edit"
                  size="md"
                  loading={salvandoRotina}
                  disabled={salvandoRotina}
                  onClick={salvarRotinaSefaz}
                >
                  {salvandoRotina ? 'Salvando...' : 'Salvar configuracao'}
                </ActionButton>
              </div>
            </>
          )}
        </Panel>
      )}
    </>
  );
}

EntradaXmlSefazPanels.propTypes = {
  avisoConectorSefaz: PropTypes.string,
  chaveSefaz: PropTypes.string.isRequired,
  cfgSefaz: PropTypes.shape({
    cert_ok: PropTypes.bool,
    enabled: PropTypes.bool,
    importacao_automatica: PropTypes.bool,
    modo: PropTypes.string,
    ultimo_sync_at: PropTypes.string,
    ultimo_sync_documentos: PropTypes.number,
    ultimo_sync_mensagem: PropTypes.string,
    ultimo_sync_status: PropTypes.string,
  }).isRequired,
  configSefazLoading: PropTypes.bool.isRequired,
  consultaExpandidaId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  consultasSefaz: PropTypes.arrayOf(PropTypes.shape({
    dados: PropTypes.shape({
      emitente_nome: PropTypes.string,
      itens: PropTypes.arrayOf(PropTypes.shape({
        codigo_produto: PropTypes.string,
        descricao: PropTypes.string,
        numero_item: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
        quantidade: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
        valor_total: PropTypes.number,
        valor_unitario: PropTypes.number,
      })),
      numero_nf: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
      serie: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
      valor_total_nf: PropTypes.number,
    }).isRequired,
    id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  })).isRequired,
  consultarSefaz: PropTypes.func.isRequired,
  erroSefaz: PropTypes.string,
  formatMoneyBRL: PropTypes.func.isRequired,
  importandoConsultaId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  loadingSefaz: PropTypes.bool.isRequired,
  mensagemRotina: PropTypes.string,
  mostrarConfigSefaz: PropTypes.bool.isRequired,
  mostrarPainelSefaz: PropTypes.bool.isRequired,
  salvarRotinaSefaz: PropTypes.func.isRequired,
  salvandoRotina: PropTypes.bool.isRequired,
  setCfgSefaz: PropTypes.func.isRequired,
  setChaveSefaz: PropTypes.func.isRequired,
  setConsultaExpandidaId: PropTypes.func.isRequired,
  usarNaEntrada: PropTypes.func.isRequired,
};

EntradaXmlSefazPanels.defaultProps = {
  avisoConectorSefaz: '',
  consultaExpandidaId: null,
  erroSefaz: '',
  importandoConsultaId: null,
  mensagemRotina: '',
};
