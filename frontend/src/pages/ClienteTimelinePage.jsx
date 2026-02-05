import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { FiArrowLeft, FiFilter, FiX, FiCalendar } from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import ClienteTimeline from '../components/ClienteTimeline';

const ClienteTimelinePage = () => {
  const { clienteId } = useParams();
  const navigate = useNavigate();
  const [cliente, setCliente] = useState(null);
  const [pets, setPets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    tipo_evento: '',
    pet_id: ''
  });
  const [mostrarFiltros, setMostrarFiltros] = useState(false);

  useEffect(() => {
    loadCliente();
    loadPets();
  }, [clienteId]);

  const loadCliente = async () => {
    try {
      const response = await api.get(`/clientes/${clienteId}`);
      setCliente(response.data);
    } catch (err) {
      console.error('Erro ao carregar cliente:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPets = async () => {
    try {
      const response = await api.get(`/pets/cliente/${clienteId}`);
      setPets(response.data);
    } catch (err) {
      console.error('Erro ao carregar pets:', err);
    }
  };

  const limparFiltros = () => {
    setFiltros({
      tipo_evento: '',
      pet_id: ''
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  if (!cliente) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          Cliente não encontrado
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/clientes')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <FiArrowLeft />
          Voltar para clientes
        </button>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Timeline de {cliente.nome}
              </h1>
              <p className="text-gray-600">
                Histórico completo de eventos e interações
              </p>
            </div>
            <button
              onClick={() => setMostrarFiltros(!mostrarFiltros)}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <FiFilter />
              Filtros
            </button>
          </div>

          {/* Painel de filtros */}
          {mostrarFiltros && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Evento
                  </label>
                  <select
                    value={filtros.tipo_evento}
                    onChange={(e) => setFiltros({ ...filtros, tipo_evento: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  >
                    <option value="">Todos os tipos</option>
                    <option value="venda">🛒 Vendas</option>
                    <option value="conta_receber">💰 Contas a Receber</option>
                    <option value="pet_cadastro">🐾 Cadastro de Pet</option>
                    <option value="pet_atualizacao">✏️ Atualização de Pet</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Pet
                  </label>
                  <select
                    value={filtros.pet_id}
                    onChange={(e) => setFiltros({ ...filtros, pet_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    disabled={pets.length === 0}
                  >
                    <option value="">Todos os pets</option>
                    {pets.map(pet => (
                      <option key={pet.id} value={pet.id}>
                        {pet.nome} - {pet.especie}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-span-2 flex justify-end gap-2">
                  <button
                    onClick={limparFiltros}
                    className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-2"
                  >
                    <FiX />
                    Limpar filtros
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <ClienteTimeline 
          clienteId={parseInt(clienteId)} 
          limit={100}
          showHeader={false}
        />
      </div>
    </div>
  );
};

export default ClienteTimelinePage;
