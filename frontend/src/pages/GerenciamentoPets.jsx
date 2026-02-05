import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import { 
  FiPlus, FiSearch, FiFilter, FiX, FiEdit2, FiEye, FiAlertCircle,
  FiCheckCircle, FiXCircle
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';

const GerenciamentoPets = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const clienteIdParam = searchParams.get('cliente_id');

  const [pets, setPets] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filtros
  const [busca, setBusca] = useState('');
  const [clienteFiltro, setClienteFiltro] = useState(clienteIdParam || '');
  const [especieFiltro, setEspecieFiltro] = useState('');
  const [statusFiltro, setStatusFiltro] = useState(''); // '', 'ativo', 'inativo'
  const [mostrarFiltros, setMostrarFiltros] = useState(false);

  // Carregar dados
  useEffect(() => {
    loadPets();
    loadClientes();
  }, [clienteFiltro, especieFiltro, statusFiltro]);

  const loadPets = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (busca) params.append('busca', busca);
      if (clienteFiltro) params.append('cliente_id', clienteFiltro);
      if (especieFiltro) params.append('especie', especieFiltro);
      if (statusFiltro) params.append('ativo', statusFiltro === 'ativo' ? 'true' : 'false');
      
      const response = await api.get(`/pets?${params.toString()}`);
      setPets(response.data);
      setError('');
    } catch (err) {
      console.error('Erro ao carregar pets:', err);
      setError('Erro ao carregar pets');
    } finally {
      setLoading(false);
    }
  };

  const loadClientes = async () => {
    try {
      const response = await api.get('/clientes');
      setClientes(response.data);
    } catch (err) {
      console.error('Erro ao carregar clientes:', err);
    }
  };

  const handleBusca = (e) => {
    e.preventDefault();
    loadPets();
  };

  const limparFiltros = () => {
    setBusca('');
    setClienteFiltro('');
    setEspecieFiltro('');
    setStatusFiltro('');
  };

  const calcularIdade = (dataNascimento) => {
    if (!dataNascimento) return null;
    const hoje = new Date();
    const nascimento = new Date(dataNascimento);
    const anos = hoje.getFullYear() - nascimento.getFullYear();
    const meses = hoje.getMonth() - nascimento.getMonth();
    
    if (anos === 0) {
      return `${meses} ${meses === 1 ? 'mês' : 'meses'}`;
    }
    return `${anos} ${anos === 1 ? 'ano' : 'anos'}`;
  };

  const toggleAtivacao = async (pet) => {
    try {
      if (pet.ativo) {
        // Desativar (soft delete)
        await api.delete(`/pets/${pet.id}?soft_delete=true`);
      } else {
        // Reativar
        await api.post(`/pets/${pet.id}/ativar`);
      }
      loadPets();
    } catch (err) {
      console.error('Erro ao alterar status do pet:', err);
      alert('Erro ao alterar status do pet');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando pets...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <PawPrint className="text-blue-600" size={36} />
            Gerenciamento de Pets
          </h1>
          <p className="text-gray-600 mt-1">
            {clienteFiltro 
              ? `Pets do cliente: ${clientes.find(c => c.id === parseInt(clienteFiltro))?.nome || ''}`
              : 'Gestão completa dos animais de estimação'}
          </p>
        </div>
        <button
          onClick={() => navigate('/pets/novo')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
        >
          <FiPlus size={20} />
          Adicionar Pet
        </button>
      </div>

      {/* Barra de busca e filtros */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <form onSubmit={handleBusca} className="space-y-4">
          {/* Busca principal */}
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por nome, raça, microchip ou código..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              Buscar
            </button>
            <button
              type="button"
              onClick={() => setMostrarFiltros(!mostrarFiltros)}
              className="px-4 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors flex items-center gap-2"
            >
              <FiFilter />
              Filtros
            </button>
          </div>

          {/* Filtros avançados */}
          {mostrarFiltros && (
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cliente (Tutor)
                </label>
                <select
                  value={clienteFiltro}
                  onChange={(e) => setClienteFiltro(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                >
                  <option value="">Todos os clientes</option>
                  {clientes.map(cliente => (
                    <option key={cliente.id} value={cliente.id}>
                      {cliente.nome}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Espécie
                </label>
                <select
                  value={especieFiltro}
                  onChange={(e) => setEspecieFiltro(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                >
                  <option value="">Todas as espécies</option>
                  <option value="Cão">Cão</option>
                  <option value="Gato">Gato</option>
                  <option value="Ave">Ave</option>
                  <option value="Roedor">Roedor</option>
                  <option value="Réptil">Réptil</option>
                  <option value="Outro">Outro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={statusFiltro}
                  onChange={(e) => setStatusFiltro(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                >
                  <option value="">Todos</option>
                  <option value="ativo">Ativos</option>
                  <option value="inativo">Inativos</option>
                </select>
              </div>

              <div className="col-span-3 flex justify-end">
                <button
                  type="button"
                  onClick={limparFiltros}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-2"
                >
                  <FiX />
                  Limpar filtros
                </button>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Erro */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <FiAlertCircle />
          {error}
        </div>
      )}

      {/* Lista de pets */}
      {pets.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <PawPrint className="mx-auto text-gray-300 mb-4" size={64} />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Nenhum pet encontrado
          </h3>
          <p className="text-gray-600 mb-6">
            {busca || clienteFiltro || especieFiltro || statusFiltro
              ? 'Tente ajustar os filtros ou fazer uma nova busca'
              : 'Comece adicionando o primeiro pet'}
          </p>
          <button
            onClick={() => navigate('/pets/novo')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          >
            <FiPlus />
            Adicionar Primeiro Pet
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pets.map(pet => (
            <div
              key={pet.id}
              className={`bg-white rounded-lg shadow-sm border-2 transition-all hover:shadow-md ${
                pet.ativo ? 'border-gray-200' : 'border-red-200 bg-gray-50'
              }`}
            >
              <div className="p-5">
                {/* Header do card */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold text-gray-900">
                        {pet.nome}
                      </h3>
                      {pet.ativo ? (
                        <FiCheckCircle className="text-green-500" size={16} />
                      ) : (
                        <FiXCircle className="text-red-500" size={16} />
                      )}
                    </div>
                    <p className="text-sm text-gray-500">{pet.codigo}</p>
                  </div>
                  {pet.foto_url && (
                    <img
                      src={pet.foto_url}
                      alt={pet.nome}
                      className="w-16 h-16 rounded-full object-cover border-2 border-gray-200"
                    />
                  )}
                </div>

                {/* Informações principais */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-gray-700">Espécie:</span>
                    <span className="text-gray-900">{pet.especie}</span>
                  </div>
                  {pet.raca && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium text-gray-700">Raça:</span>
                      <span className="text-gray-900">{pet.raca}</span>
                    </div>
                  )}
                  {pet.sexo && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium text-gray-700">Sexo:</span>
                      <span className="text-gray-900">{pet.sexo}</span>
                    </div>
                  )}
                  {pet.data_nascimento && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium text-gray-700">Idade:</span>
                      <span className="text-gray-900">{calcularIdade(pet.data_nascimento)}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-sm pt-2 border-t border-gray-100">
                    <span className="font-medium text-gray-700">Tutor:</span>
                    <span className="text-blue-600">{pet.cliente_nome}</span>
                  </div>
                </div>

                {/* Ações */}
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/pets/${pet.id}`)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
                  >
                    <FiEye size={16} />
                    Ver Detalhes
                  </button>
                  <button
                    onClick={() => navigate(`/pets/${pet.id}/editar`)}
                    className="px-3 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors"
                    title="Editar"
                  >
                    <FiEdit2 size={16} className="text-gray-600" />
                  </button>
                  <button
                    onClick={() => toggleAtivacao(pet)}
                    className={`px-3 py-2 border rounded-lg transition-colors ${
                      pet.ativo
                        ? 'border-red-300 hover:bg-red-50 text-red-600'
                        : 'border-green-300 hover:bg-green-50 text-green-600'
                    }`}
                    title={pet.ativo ? 'Desativar' : 'Reativar'}
                  >
                    {pet.ativo ? <FiXCircle size={16} /> : <FiCheckCircle size={16} />}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Resumo */}
      {pets.length > 0 && (
        <div className="mt-6 text-center text-sm text-gray-600">
          Total: <strong>{pets.length}</strong> pet(s) encontrado(s)
          {statusFiltro === '' && (
            <>
              {' • '}
              <strong className="text-green-600">
                {pets.filter(p => p.ativo).length}
              </strong> ativo(s)
              {' • '}
              <strong className="text-red-600">
                {pets.filter(p => !p.ativo).length}
              </strong> inativo(s)
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default GerenciamentoPets;
