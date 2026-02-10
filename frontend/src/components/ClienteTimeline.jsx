import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import { 
  FiShoppingCart, FiDollarSign, FiCalendar, FiAlertCircle,
  FiCheck, FiClock, FiX, FiPackage, FiTruck, FiMessageCircle
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';

// Mapeamento de ícones por tipo de evento
const ICONES_EVENTO = {
  venda: FiShoppingCart,
  conta_receber: FiDollarSign,
  pet_cadastro: PawPrint,
  pet_atualizacao: PawPrint,
  pedido_compra: FiPackage,
  conta_pagar: FiDollarSign,
  recebimento: FiTruck,
  vacina: FiCalendar,
  consulta: FiCalendar,
  whatsapp: FiMessageCircle
};

// Mapeamento de cores por badge
const CORES_BADGE = {
  green: 'bg-green-100 text-green-700 border-green-300',
  yellow: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  red: 'bg-red-100 text-red-700 border-red-300',
  blue: 'bg-blue-100 text-blue-700 border-blue-300',
  purple: 'bg-purple-100 text-purple-700 border-purple-300',
  gray: 'bg-gray-100 text-gray-700 border-gray-300'
};

const ClienteTimeline = ({ 
  clienteId, 
  fornecedorId,
  tipo = 'cliente', // 'cliente' ou 'fornecedor'
  limit = 5, 
  showHeader = true, 
  onVerMais 
}) => {
  const [eventos, setEventos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const entityId = tipo === 'fornecedor' ? fornecedorId : clienteId;
  const endpoint = tipo === 'fornecedor' 
    ? `/clientes/fornecedor/${entityId}/timeline`
    : `/clientes/${entityId}/timeline`;

  useEffect(() => {
    if (entityId) {
      loadTimeline();
    }
  }, [entityId, limit, tipo]);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await api.get(`${endpoint}?limit=${limit}`);
      setEventos(response.data);
    } catch (err) {
      // Silenciar erros 500 (VIEW ainda não criada) e 404 (endpoint não existe)
      if (err.response?.status === 500 || err.response?.status === 404) {
        console.warn('Timeline não disponível:', err.response?.status);
        setEventos([]);
        setError(''); // Não mostrar erro ao usuário
      } else {
        console.error('Erro ao carregar timeline:', err);
        setError('Erro ao carregar timeline');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatarData = (data) => {
    const date = new Date(data);
    const hoje = new Date();
    const ontem = new Date(hoje);
    ontem.setDate(ontem.getDate() - 1);

    // Se for hoje
    if (date.toDateString() === hoje.toDateString()) {
      return `Hoje às ${date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
    }

    // Se foi ontem
    if (date.toDateString() === ontem.toDateString()) {
      return `Ontem às ${date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
    }

    // Senão, data completa
    return date.toLocaleDateString('pt-BR', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleEventoClick = (evento) => {
    // Navegação futura para telas específicas
    console.log('Evento clicado:', evento);
    // TODO: Implementar navegação baseada no tipo
    // if (evento.tipo_evento === 'venda') navigate(`/vendas/${evento.evento_id}`)
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-3"></div>
          <p className="text-gray-600 text-sm">Carregando timeline...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
        <FiAlertCircle />
        {error}
      </div>
    );
  }

  if (eventos.length === 0) {
    return (
      <div className="text-center py-12">
        <FiCalendar className="mx-auto text-gray-300 mb-4" size={48} />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Nenhum evento registrado
        </h3>
        <p className="text-gray-600 text-sm">
          Eventos do cliente aparecerão aqui conforme forem acontecendo
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showHeader && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FiCalendar className="text-blue-600" />
            Linha do Tempo
          </h3>
          {onVerMais && (
            <button
              onClick={onVerMais}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Ver completa →
            </button>
          )}
        </div>
      )}

      {/* Timeline vertical */}
      <div className="relative">
        {/* Linha vertical */}
        <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gray-200"></div>

        {/* Eventos */}
        <div className="space-y-6">
          {eventos.map((evento, index) => {
            const IconeEvento = ICONES_EVENTO[evento.tipo_evento] || FiCalendar;
            const corBadge = CORES_BADGE[evento.cor_badge] || CORES_BADGE.gray;

            return (
              <div 
                key={`${evento.tipo_evento}-${evento.evento_id}-${index}`}
                className="relative pl-12 group"
              >
                {/* Ícone */}
                <div className="absolute left-0 top-0 w-10 h-10 rounded-full bg-white border-2 border-gray-200 flex items-center justify-center group-hover:border-blue-400 transition-colors">
                  <IconeEvento className="text-gray-600 group-hover:text-blue-600 transition-colors" size={18} />
                </div>

                {/* Card do evento */}
                <div 
                  onClick={() => handleEventoClick(evento)}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md hover:border-gray-300 transition-all cursor-pointer"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900 mb-1">
                        {evento.titulo}
                      </h4>
                      <p className="text-sm text-gray-600">
                        {evento.descricao}
                      </p>
                    </div>
                    {/* Badge de status */}
                    <span className={`ml-3 px-2 py-1 text-xs font-medium rounded border ${corBadge} whitespace-nowrap`}>
                      {evento.status}
                    </span>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between text-xs text-gray-500 mt-3 pt-3 border-t border-gray-100">
                    <span className="flex items-center gap-1">
                      <FiClock size={12} />
                      {formatarData(evento.data_evento)}
                    </span>
                    {evento.pet_id && (
                      <span className="flex items-center gap-1 text-blue-600">
                        <PawPrint size={12} />
                        Pet relacionado
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Botão "Ver mais" se estiver limitado */}
      {eventos.length >= limit && onVerMais && (
        <div className="text-center pt-4">
          <button
            onClick={onVerMais}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium underline"
          >
            Ver todos os eventos →
          </button>
        </div>
      )}
    </div>
  );
};

ClienteTimeline.propTypes = {
  clienteId: PropTypes.number,
  fornecedorId: PropTypes.number,
  tipo: PropTypes.oneOf(['cliente', 'fornecedor']),
  limit: PropTypes.number,
  showHeader: PropTypes.bool,
  onVerMais: PropTypes.func
};

export default ClienteTimeline;
