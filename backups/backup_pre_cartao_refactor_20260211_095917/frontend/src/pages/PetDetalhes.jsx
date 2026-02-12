import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { 
  FiArrowLeft, FiEdit2, FiUser, FiPhone, FiCalendar, FiActivity,
  FiHeart, FiClipboard, FiAlertCircle, FiCheckCircle, FiXCircle
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import { formatarIdadeMeses } from '../helpers/idadeHelper';

const PetDetalhes = () => {
  const { petId } = useParams();
  const navigate = useNavigate();

  const [pet, setPet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [abaAtiva, setAbaAtiva] = useState('geral');

  useEffect(() => {
    loadPet();
  }, [petId]);

  const loadPet = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/pets/${petId}`);
      setPet(response.data);
      setError('');
    } catch (err) {
      console.error('Erro ao carregar pet:', err);
      setError('Erro ao carregar informações do pet');
    } finally {
      setLoading(false);
    }
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
    if (meses < 0) {
      return `${anos - 1} anos e ${12 + meses} meses`;
    }
    if (meses === 0) {
      return `${anos} ${anos === 1 ? 'ano' : 'anos'}`;
    }
    return `${anos} anos e ${meses} ${meses === 1 ? 'mês' : 'meses'}`;
  };

  const formatarData = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
  };

  const toggleAtivacao = async () => {
    try {
      if (pet.ativo) {
        await api.delete(`/pets/${pet.id}?soft_delete=true`);
      } else {
        await api.post(`/pets/${pet.id}/ativar`);
      }
      loadPet();
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
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  if (error || !pet) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <FiAlertCircle />
          {error || 'Pet não encontrado'}
        </div>
        <button
          onClick={() => navigate('/pets')}
          className="mt-4 flex items-center gap-2 text-blue-600 hover:text-blue-700"
        >
          <FiArrowLeft />
          Voltar para lista de pets
        </button>
      </div>
    );
  }

  const abas = [
    { id: 'geral', label: 'Dados Gerais', icon: FiClipboard },
    { id: 'saude', label: 'Saúde', icon: FiHeart },
    { id: 'vacinas', label: 'Vacinas', icon: FiActivity },
    { id: 'consultas', label: 'Consultas', icon: FiCalendar },
    { id: 'servicos', label: 'Serviços', icon: PawPrint },
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/pets')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <FiArrowLeft />
          Voltar para Gerenciamento de Pets
        </button>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-6">
              {pet.foto_url ? (
                <img
                  src={pet.foto_url}
                  alt={pet.nome}
                  className="w-24 h-24 rounded-full object-cover border-4 border-gray-200"
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center border-4 border-gray-200">
                  <PawPrint className="text-blue-600" size={48} />
                </div>
              )}
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-3xl font-bold text-gray-900">{pet.nome}</h1>
                  {pet.ativo ? (
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium flex items-center gap-1">
                      <FiCheckCircle size={14} />
                      Ativo
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium flex items-center gap-1">
                      <FiXCircle size={14} />
                      Inativo
                    </span>
                  )}
                </div>
                <p className="text-gray-500 mb-1">
                  {pet.especie} {pet.raca && `• ${pet.raca}`} {pet.sexo && `• ${pet.sexo}`}
                </p>
                <p className="text-sm text-gray-400">{pet.codigo}</p>
                
                {/* Info do tutor */}
                <div className="mt-3 flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2 text-gray-700">
                    <FiUser size={16} />
                    <span className="font-medium">Tutor:</span>
                    <span className="text-blue-600">{pet.cliente_nome}</span>
                  </div>
                  {pet.cliente_celular && (
                    <div className="flex items-center gap-2 text-gray-700">
                      <FiPhone size={16} />
                      <span>{pet.cliente_celular}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Ações */}
            <div className="flex gap-2">
              <button
                onClick={() => navigate(`/pets/${pet.id}/editar`)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
              >
                <FiEdit2 />
                Editar
              </button>
              <button
                onClick={toggleAtivacao}
                className={`px-4 py-2 border-2 rounded-lg transition-colors font-medium ${
                  pet.ativo
                    ? 'border-red-300 text-red-600 hover:bg-red-50'
                    : 'border-green-300 text-green-600 hover:bg-green-50'
                }`}
              >
                {pet.ativo ? 'Desativar' : 'Reativar'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Abas */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex gap-4">
          {abas.map(aba => {
            const Icon = aba.icon;
            return (
              <button
                key={aba.id}
                onClick={() => setAbaAtiva(aba.id)}
                className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors ${
                  abaAtiva === aba.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <Icon size={18} />
                {aba.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Conteúdo das abas */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {/* Aba: Dados Gerais */}
        {abaAtiva === 'geral' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Informações Gerais</h2>
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <p className="text-gray-900 font-medium">{pet.nome}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Código</label>
                <p className="text-gray-900 font-mono text-sm">{pet.codigo}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Espécie</label>
                <p className="text-gray-900">{pet.especie}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Raça</label>
                <p className="text-gray-900">{pet.raca || '-'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sexo</label>
                <p className="text-gray-900">{pet.sexo || '-'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Castrado</label>
                <p className="text-gray-900">{pet.castrado ? 'Sim' : 'Não'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Nascimento</label>
                <p className="text-gray-900">{formatarData(pet.data_nascimento)}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Idade</label>
                <p className="text-gray-900">
                  {pet.idade_meses ? formatarIdadeMeses(pet.idade_meses) :
                   pet.idade_aproximada ? formatarIdadeMeses(pet.idade_aproximada) :
                   pet.data_nascimento ? calcularIdade(pet.data_nascimento) : '-'}
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Peso</label>
                <p className="text-gray-900">{pet.peso ? `${pet.peso} kg` : '-'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Porte</label>
                <p className="text-gray-900">{pet.porte || '-'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cor/Pelagem</label>
                <p className="text-gray-900">{pet.cor || '-'}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Microchip</label>
                <p className="text-gray-900 font-mono text-sm">{pet.microchip || '-'}</p>
              </div>
            </div>

            {pet.observacoes && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">{pet.observacoes}</p>
              </div>
            )}

            <div className="pt-4 border-t border-gray-200 text-sm text-gray-500">
              <p>Cadastrado em: {formatarData(pet.created_at)}</p>
              <p>Última atualização: {formatarData(pet.updated_at)}</p>
            </div>
          </div>
        )}

        {/* Aba: Saúde */}
        {abaAtiva === 'saude' && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Informações de Saúde</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Alergias</label>
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <p className="text-gray-900">{pet.alergias || 'Nenhuma alergia registrada'}</p>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Doenças Crônicas</label>
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <p className="text-gray-900">{pet.doencas_cronicas || 'Nenhuma doença crônica registrada'}</p>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Medicamentos Contínuos</label>
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <p className="text-gray-900">{pet.medicamentos_continuos || 'Nenhum medicamento contínuo registrado'}</p>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Histórico Clínico</label>
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <p className="text-gray-900 whitespace-pre-line">
                    {pet.historico_clinico || 'Nenhum histórico clínico registrado'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Aba: Vacinas */}
        {abaAtiva === 'vacinas' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Carteira de Vacinação</h2>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
                + Registrar Vacina
              </button>
            </div>
            <div className="text-center py-12 text-gray-500">
              <FiActivity size={48} className="mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium mb-2">Módulo em desenvolvimento</p>
              <p className="text-sm">Em breve você poderá gerenciar o histórico de vacinas do pet</p>
            </div>
          </div>
        )}

        {/* Aba: Consultas */}
        {abaAtiva === 'consultas' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Histórico de Consultas</h2>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
                + Nova Consulta
              </button>
            </div>
            <div className="text-center py-12 text-gray-500">
              <FiCalendar size={48} className="mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium mb-2">Módulo em desenvolvimento</p>
              <p className="text-sm">Em breve você poderá gerenciar consultas veterinárias</p>
            </div>
          </div>
        )}

        {/* Aba: Serviços */}
        {abaAtiva === 'servicos' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Histórico de Serviços</h2>
              <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
                + Registrar Serviço
              </button>
            </div>
            <div className="text-center py-12 text-gray-500">
              <PawPrint size={48} className="mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium mb-2">Módulo em desenvolvimento</p>
              <p className="text-sm">Em breve você poderá gerenciar banho, tosa e outros serviços</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PetDetalhes;
