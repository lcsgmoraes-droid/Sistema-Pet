/**
 * ExtratoCredito
 *
 * Exibe o histórico de movimentações de crédito de um cliente.
 * Mostra tipo, valor, saldo, motivo, data e quem realizou a operação.
 */

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, ShoppingCart, RefreshCw, Coins } from 'lucide-react';
import api from '../api';

const TIPO_CONFIG = {
  adicao_manual:  { label: 'Inserção manual',   icon: TrendingUp,   cor: 'text-green-600',  bg: 'bg-green-50',  borda: 'border-green-200', sinal: '+' },
  remocao_manual: { label: 'Remoção manual',    icon: TrendingDown, cor: 'text-red-600',    bg: 'bg-red-50',    borda: 'border-red-200',   sinal: '−' },
  uso_venda:      { label: 'Usado em venda',    icon: ShoppingCart, cor: 'text-blue-600',   bg: 'bg-blue-50',   borda: 'border-blue-200',  sinal: '−' },
  troco:          { label: 'Troco em crédito',  icon: Coins,        cor: 'text-purple-600', bg: 'bg-purple-50', borda: 'border-purple-200',sinal: '+' },
  devolucao:      { label: 'Devolução',         icon: RefreshCw,    cor: 'text-orange-600', bg: 'bg-orange-50', borda: 'border-orange-200',sinal: '+' },
};

function formatarData(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatarReais(valor) {
  return parseFloat(valor || 0).toFixed(2).replace('.', ',');
}

export default function ExtratoCredito({ clienteId, refreshKey = 0 }) {
  const [extrato, setExtrato] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [expandido, setExpandido] = useState(false);

  useEffect(() => {
    if (!clienteId) return;
    setLoading(true);
    setErro('');
    api.get(`/clientes/${clienteId}/credito/extrato?limit=50`)
      .then(r => setExtrato(r.data))
      .catch(() => setErro('Não foi possível carregar o extrato.'))
      .finally(() => setLoading(false));
  }, [clienteId, refreshKey]);

  const visivel = expandido ? extrato : extrato.slice(0, 5);

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          <Coins className="w-5 h-5 text-amber-500" />
          <span className="text-sm font-semibold text-gray-800">Extrato de Crédito</span>
          {extrato.length > 0 && (
            <span className="text-xs bg-gray-200 text-gray-600 rounded-full px-2 py-0.5">
              {extrato.length} movimentação{extrato.length !== 1 ? 'ões' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Conteúdo */}
      <div className="px-5 py-4">
        {loading && (
          <div className="flex items-center justify-center py-8 gap-2 text-gray-400 text-sm">
            <span className="w-4 h-4 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
            Carregando extrato...
          </div>
        )}

        {!loading && erro && (
          <p className="text-center text-red-500 text-sm py-4">{erro}</p>
        )}

        {!loading && !erro && extrato.length === 0 && (
          <div className="text-center py-8">
            <Coins className="w-10 h-10 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-400 text-sm">Nenhuma movimentação de crédito registrada.</p>
          </div>
        )}

        {!loading && !erro && extrato.length > 0 && (
          <div className="space-y-2">
            {visivel.map((mov) => {
              const cfg = TIPO_CONFIG[mov.tipo] || TIPO_CONFIG.adicao_manual;
              const Icon = cfg.icon;
              const isPositivo = cfg.sinal === '+';

              return (
                <div
                  key={mov.id}
                  className={`flex items-start gap-3 p-3 rounded-xl border ${cfg.bg} ${cfg.borda}`}
                >
                  {/* Ícone */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-white border ${cfg.borda}`}>
                    <Icon className={`w-4 h-4 ${cfg.cor}`} />
                  </div>

                  {/* Dados */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className={`text-xs font-semibold ${cfg.cor}`}>{cfg.label}</span>
                        {mov.motivo && (
                          <p className="text-xs text-gray-600 mt-0.5 truncate max-w-[220px]" title={mov.motivo}>
                            {mov.motivo}
                          </p>
                        )}
                        {mov.usuario_nome && (
                          <p className="text-xs text-gray-400 mt-0.5">por {mov.usuario_nome}</p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className={`text-sm font-bold ${isPositivo ? 'text-green-600' : 'text-red-600'}`}>
                          {cfg.sinal} R$ {formatarReais(mov.valor)}
                        </p>
                        <p className="text-xs text-gray-500">
                          saldo: R$ {formatarReais(mov.saldo_atual)}
                        </p>
                      </div>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">{formatarData(mov.created_at)}</p>
                  </div>
                </div>
              );
            })}

            {extrato.length > 5 && (
              <button
                onClick={() => setExpandido(!expandido)}
                className="w-full flex items-center justify-center gap-1 py-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
              >
                {expandido ? (
                  <><ChevronUp className="w-3 h-3" /> Mostrar menos</>
                ) : (
                  <><ChevronDown className="w-3 h-3" /> Ver mais {extrato.length - 5} movimentações</>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
