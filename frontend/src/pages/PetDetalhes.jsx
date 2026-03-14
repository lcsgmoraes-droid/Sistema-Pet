import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { vetApi } from './veterinario/vetApi';
import { 
  FiArrowLeft, FiEdit2, FiUser, FiPhone, FiCalendar, FiActivity,
  FiHeart, FiClipboard, FiAlertCircle, FiCheckCircle, FiXCircle
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import { formatarIdadeMeses } from '../helpers/idadeHelper';

const listaClinica = (lista = [], fallback = '') => {
  if (Array.isArray(lista) && lista.length > 0) {
    return lista;
  }
  return (fallback || '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
};

const PetDetalhes = () => {
  const { petId } = useParams();
  const navigate = useNavigate();

  const [pet, setPet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [abaAtiva, setAbaAtiva] = useState('geral');
  const [historicoInternacoes, setHistoricoInternacoes] = useState([]);
  const [loadingInternacoes, setLoadingInternacoes] = useState(false);
  const [historicoVacinas, setHistoricoVacinas] = useState([]);
  const [loadingVacinas, setLoadingVacinas] = useState(false);
  const [historicoConsultas, setHistoricoConsultas] = useState([]);
  const [loadingConsultas, setLoadingConsultas] = useState(false);
  const [filtroVacinas, setFiltroVacinas] = useState('');
  const [filtroConsultas, setFiltroConsultas] = useState('');
  const [limiteVacinas, setLimiteVacinas] = useState(6);
  const [limiteConsultas, setLimiteConsultas] = useState(6);
  const [ultimaVacina, setUltimaVacina] = useState(null);
  const [ultimaAlta, setUltimaAlta] = useState(null);
  const [carteirinha, setCarteirinha] = useState(null);
  const [exames, setExames] = useState([]);
  const [loadingExames, setLoadingExames] = useState(false);
  const [salvandoExame, setSalvandoExame] = useState(false);
  const [novoExame, setNovoExame] = useState({
    nome: '',
    tipo: 'laboratorial',
    data_solicitacao: '',
    laboratorio: '',
    observacoes: '',
    arquivo: null,
  });

  useEffect(() => {
    loadPet();
  }, [petId]);

  useEffect(() => {
    carregarResumoClinico();
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

  const formatarDataHora = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleString('pt-BR');
  };

  const renderListaClinica = (titulo, itens, vazio = 'Nada registrado') => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{titulo}</label>
      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
        {itens.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {itens.map((item) => (
              <span key={`${titulo}_${item}`} className="px-3 py-1 bg-white border border-gray-200 rounded-full text-sm text-gray-800">
                {item}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">{vazio}</p>
        )}
      </div>
    </div>
  );

  const carregarHistoricoInternacoes = async () => {
    try {
      setLoadingInternacoes(true);
      const response = await vetApi.historicoInternacoesPet(petId);
      const lista = Array.isArray(response.data?.historico) ? response.data.historico : [];
      setHistoricoInternacoes(lista);
    } catch {
      setHistoricoInternacoes([]);
    } finally {
      setLoadingInternacoes(false);
    }
  };

  const carregarHistoricoVacinas = async () => {
    try {
      setLoadingVacinas(true);
      const response = await vetApi.listarVacinasPet(petId);
      const lista = Array.isArray(response.data)
        ? response.data
        : (response.data?.items ?? []);

      const ordenadas = [...lista].sort((a, b) => {
        const da = new Date(a.data_aplicacao || 0).getTime();
        const db = new Date(b.data_aplicacao || 0).getTime();
        return db - da;
      });

      setHistoricoVacinas(ordenadas);
    } catch {
      setHistoricoVacinas([]);
    } finally {
      setLoadingVacinas(false);
    }
  };

  const carregarHistoricoConsultas = async () => {
    try {
      setLoadingConsultas(true);
      const response = await vetApi.listarConsultas({
        pet_id: petId,
        limit: 200,
      });

      const lista = Array.isArray(response.data)
        ? response.data
        : (response.data?.items ?? []);

      const ordenadas = [...lista].sort((a, b) => {
        const da = new Date(a.inicio_atendimento || a.created_at || 0).getTime();
        const db = new Date(b.inicio_atendimento || b.created_at || 0).getTime();
        return db - da;
      });

      setHistoricoConsultas(ordenadas);
    } catch {
      setHistoricoConsultas([]);
    } finally {
      setLoadingConsultas(false);
    }
  };

  const carregarExames = async () => {
    try {
      setLoadingExames(true);
      const response = await vetApi.listarExamesPet(petId);
      const lista = Array.isArray(response.data) ? response.data : (response.data?.items ?? []);
      setExames(lista);
    } catch {
      setExames([]);
    } finally {
      setLoadingExames(false);
    }
  };

  const carregarResumoClinico = async () => {
    try {
      const [resCarteirinha, resHistoricoInternacoes] = await Promise.all([
        vetApi.obterCarteirinhaPet(petId).catch(() => ({ data: null })),
        vetApi.historicoInternacoesPet(petId).catch(() => ({ data: { historico: [] } })),
      ]);

      const resumoCarteirinha = resCarteirinha.data || null;
      setCarteirinha(resumoCarteirinha);

      const listaVacinas = Array.isArray(resumoCarteirinha?.status_vacinal?.carteira)
        ? resumoCarteirinha.status_vacinal.carteira
        : [];

      const vacinasOrdenadas = [...listaVacinas].sort((a, b) => {
        const da = new Date(a.data_aplicacao || 0).getTime();
        const db = new Date(b.data_aplicacao || 0).getTime();
        return db - da;
      });
      setUltimaVacina(vacinasOrdenadas[0] ?? null);

      const listaHistorico = Array.isArray(resHistoricoInternacoes.data?.historico)
        ? resHistoricoInternacoes.data.historico
        : [];

      const altas = listaHistorico.filter((item) => item?.data_saida);
      const altasOrdenadas = [...altas].sort((a, b) => {
        const da = new Date(a.data_saida || 0).getTime();
        const db = new Date(b.data_saida || 0).getTime();
        return db - da;
      });
      setUltimaAlta(altasOrdenadas[0] ?? null);
    } catch {
      setCarteirinha(null);
      setUltimaVacina(null);
      setUltimaAlta(null);
    }
  };

  const interpretarExameIA = async (exameId) => {
    try {
      await vetApi.interpretarExameIA(exameId);
      await Promise.all([carregarExames(), carregarResumoClinico()]);
    } catch (err) {
      alert(err.response?.data?.detail || 'Não foi possível interpretar o exame com IA');
    }
  };

  useEffect(() => {
    if (abaAtiva !== 'internacoes') return;
    carregarHistoricoInternacoes();
  }, [abaAtiva, petId]);

  useEffect(() => {
    if (abaAtiva !== 'vacinas') return;
    carregarHistoricoVacinas();
  }, [abaAtiva, petId]);

  useEffect(() => {
    if (abaAtiva !== 'consultas') return;
    carregarHistoricoConsultas();
  }, [abaAtiva, petId]);

  useEffect(() => {
    if (abaAtiva !== 'saude') return;
    carregarExames();
  }, [abaAtiva, petId]);

  useEffect(() => {
    if (abaAtiva !== 'vacinas') return;
    setLimiteVacinas(6);
  }, [abaAtiva, filtroVacinas]);

  useEffect(() => {
    if (abaAtiva !== 'consultas') return;
    setLimiteConsultas(6);
  }, [abaAtiva, filtroConsultas]);

  const vacinasFiltradas = historicoVacinas.filter((vacina) => {
    const termo = filtroVacinas.trim().toLowerCase();
    if (!termo) return true;
    const texto = [
      vacina?.nome_vacina,
      vacina?.fabricante,
      vacina?.lote,
      vacina?.veterinario_responsavel,
      vacina?.veterinario_nome,
    ].filter(Boolean).join(' ').toLowerCase();
    return texto.includes(termo);
  });

  const consultasFiltradas = historicoConsultas.filter((consulta) => {
    const termo = filtroConsultas.trim().toLowerCase();
    if (!termo) return true;
    const texto = [
      consulta?.queixa_principal,
      consulta?.motivo_consulta,
      consulta?.diagnostico,
      consulta?.veterinario_nome,
      consulta?.status,
    ].filter(Boolean).join(' ').toLowerCase();
    return texto.includes(termo);
  });

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

  const salvarNovoExame = async () => {
    if (!novoExame.nome.trim()) return;

    try {
      setSalvandoExame(true);
      const response = await vetApi.criarExame({
        pet_id: Number(petId),
        nome: novoExame.nome,
        tipo: novoExame.tipo,
        data_solicitacao: novoExame.data_solicitacao || undefined,
        laboratorio: novoExame.laboratorio || undefined,
        observacoes: novoExame.observacoes || undefined,
      });

      if (novoExame.arquivo) {
        await vetApi.uploadArquivoExame(response.data.id, novoExame.arquivo);
      }

      setNovoExame({
        nome: '',
        tipo: 'laboratorial',
        data_solicitacao: '',
        laboratorio: '',
        observacoes: '',
        arquivo: null,
      });
      await carregarExames();
    } catch (err) {
      console.error('Erro ao salvar exame:', err);
      alert(err.response?.data?.detail || 'Erro ao salvar exame');
    } finally {
      setSalvandoExame(false);
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
    { id: 'internacoes', label: 'Internações', icon: FiActivity },
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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-blue-200 bg-blue-50 rounded-lg p-4">
                <p className="text-xs font-semibold text-blue-700 mb-1">Última vacina</p>
                {ultimaVacina ? (
                  <>
                    <p className="text-sm font-semibold text-blue-900">{ultimaVacina.nome_vacina || 'Vacina'}</p>
                    <p className="text-xs text-blue-800">Aplicada em: {formatarData(ultimaVacina.data_aplicacao)}</p>
                    <p className="text-xs text-blue-800">Próxima dose: {formatarData(ultimaVacina.proxima_dose || ultimaVacina.data_proxima_dose)}</p>
                  </>
                ) : (
                  <p className="text-sm text-blue-800">Nenhuma vacina registrada.</p>
                )}
              </div>

              <div className="border border-green-200 bg-green-50 rounded-lg p-4">
                <p className="text-xs font-semibold text-green-700 mb-1">Resumo da última alta</p>
                {ultimaAlta ? (
                  <>
                    <p className="text-xs text-green-800">Alta em: {formatarDataHora(ultimaAlta.data_saida)}</p>
                    <p className="text-sm font-semibold text-green-900 mt-1">Motivo: {ultimaAlta.motivo || '-'}</p>
                    <p className="text-xs text-green-800 mt-1">Observação: {ultimaAlta.observacoes_alta || 'Sem observação de alta.'}</p>
                  </>
                ) : (
                  <p className="text-sm text-green-800">Nenhuma alta registrada.</p>
                )}
              </div>
            </div>
            
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

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo sanguíneo</label>
                <p className="text-gray-900">{pet.tipo_sanguineo || '-'}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Pedigree</label>
                <p className="text-gray-900">{pet.pedigree_registro || '-'}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data da castração</label>
                <p className="text-gray-900">{formatarData(pet.castrado_data)}</p>
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

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {renderListaClinica('Alergias', listaClinica(pet.alergias_lista, pet.alergias), 'Nenhuma alergia registrada')}
              {renderListaClinica('Doenças crônicas', listaClinica(pet.condicoes_cronicas_lista, pet.doencas_cronicas), 'Nenhuma doença crônica registrada')}
              {renderListaClinica('Medicamentos contínuos', listaClinica(pet.medicamentos_continuos_lista, pet.medicamentos_continuos), 'Nenhum medicamento contínuo registrado')}
              {renderListaClinica('Restrições alimentares', listaClinica(pet.restricoes_alimentares_lista), 'Nenhuma restrição alimentar registrada')}
            </div>

            {Array.isArray(carteirinha?.alertas) && carteirinha.alertas.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-amber-900 mb-2">Alertas para atendimento e venda</h3>
                <div className="space-y-2">
                  {carteirinha.alertas.slice(0, 6).map((alerta, idx) => (
                    <div key={`alerta_${idx}`} className="text-sm text-amber-900">
                      • {alerta.mensagem}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Histórico Clínico</label>
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <p className="text-gray-900 whitespace-pre-line">
                    {pet.historico_clinico || 'Nenhum histórico clínico registrado'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-[1fr_0.95fr] gap-4">
                <div className="bg-white border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold text-gray-900">Exames recentes</h3>
                    <button
                      type="button"
                      onClick={carregarExames}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      Atualizar
                    </button>
                  </div>

                  {loadingExames ? (
                    <div className="text-sm text-gray-500">Carregando exames...</div>
                  ) : exames.length === 0 ? (
                    <div className="text-sm text-gray-500">Nenhum exame registrado ainda.</div>
                  ) : (
                    <div className="space-y-3">
                      {exames.map((exame) => (
                        <div key={exame.id} className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-medium text-gray-900">{exame.nome}</p>
                              <p className="text-sm text-gray-500">
                                {exame.tipo || 'Exame'} • {formatarData(exame.data_solicitacao)} • {exame.status || '-'}
                              </p>
                            </div>
                            {exame.arquivo_url && (
                              <a
                                href={exame.arquivo_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-sm text-blue-600 hover:text-blue-700"
                              >
                                Abrir arquivo
                              </a>
                            )}
                          </div>
                          {exame.laboratorio && <p className="text-sm text-gray-600 mt-2">Laboratório: {exame.laboratorio}</p>}
                          {exame.interpretacao_ia_resumo && (
                            <div className="mt-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2">
                              <p className="text-xs font-semibold text-cyan-800">Triagem IA</p>
                              <p className="text-sm text-cyan-900">{exame.interpretacao_ia_resumo}</p>
                            </div>
                          )}
                          {exame.observacoes && <p className="text-sm text-gray-600 mt-2">Obs.: {exame.observacoes}</p>}
                          <div className="mt-3 flex flex-wrap gap-3">
                            <button
                              type="button"
                              onClick={() => interpretarExameIA(exame.id)}
                              className="text-sm text-cyan-700 hover:text-cyan-800"
                            >
                              {exame.interpretacao_ia_resumo ? 'Reprocessar triagem IA' : 'Interpretar com IA'}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
                  <h3 className="text-lg font-semibold text-gray-900">Novo exame</h3>
                  <input
                    type="text"
                    value={novoExame.nome}
                    onChange={(e) => setNovoExame((prev) => ({ ...prev, nome: e.target.value }))}
                    placeholder="Nome do exame"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                  <div className="grid grid-cols-2 gap-3">
                    <select
                      value={novoExame.tipo}
                      onChange={(e) => setNovoExame((prev) => ({ ...prev, tipo: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    >
                      <option value="laboratorial">Laboratorial</option>
                      <option value="imagem">Imagem</option>
                      <option value="citologia">Citologia</option>
                      <option value="outro">Outro</option>
                    </select>
                    <input
                      type="date"
                      value={novoExame.data_solicitacao}
                      onChange={(e) => setNovoExame((prev) => ({ ...prev, data_solicitacao: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    />
                  </div>
                  <input
                    type="text"
                    value={novoExame.laboratorio}
                    onChange={(e) => setNovoExame((prev) => ({ ...prev, laboratorio: e.target.value }))}
                    placeholder="Laboratório ou clínica"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                  <textarea
                    value={novoExame.observacoes}
                    onChange={(e) => setNovoExame((prev) => ({ ...prev, observacoes: e.target.value }))}
                    rows="3"
                    placeholder="Observações do pedido ou resultado"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  />
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.webp"
                    onChange={(e) => setNovoExame((prev) => ({ ...prev, arquivo: e.target.files?.[0] || null }))}
                    className="w-full text-sm text-gray-600"
                  />
                  <button
                    type="button"
                    onClick={salvarNovoExame}
                    disabled={salvandoExame || !novoExame.nome.trim()}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg transition-colors font-medium"
                  >
                    {salvandoExame ? 'Salvando exame...' : 'Salvar exame'}
                  </button>
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
              <button
                onClick={() => navigate(`/veterinario/vacinas?pet_id=${pet.id}&acao=novo`)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
              >
                + Registrar Vacina
              </button>
            </div>

            <div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                <div className="rounded-xl border border-gray-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-500">Aplicadas</p>
                  <p className="text-2xl font-bold text-gray-900">{carteirinha?.status_vacinal?.resumo?.total_aplicadas ?? historicoVacinas.length}</p>
                </div>
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <p className="text-xs uppercase tracking-wide text-amber-700">Pendentes</p>
                  <p className="text-2xl font-bold text-amber-900">{carteirinha?.status_vacinal?.resumo?.total_pendentes ?? 0}</p>
                </div>
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
                  <p className="text-xs uppercase tracking-wide text-rose-700">Atrasadas</p>
                  <p className="text-2xl font-bold text-rose-900">{carteirinha?.status_vacinal?.resumo?.total_vencidas ?? 0}</p>
                </div>
              </div>

              {Array.isArray(carteirinha?.status_vacinal?.pendentes) && carteirinha.status_vacinal.pendentes.length > 0 && (
                <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <h3 className="text-sm font-semibold text-amber-900 mb-2">Protocolos pendentes</h3>
                  <div className="flex flex-wrap gap-2">
                    {carteirinha.status_vacinal.pendentes.map((item) => (
                      <span key={`pendente_${item.nome}`} className="px-3 py-1 rounded-full bg-white border border-amber-200 text-sm text-amber-900">
                        {item.nome}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <input
                type="text"
                value={filtroVacinas}
                onChange={(e) => setFiltroVacinas(e.target.value)}
                placeholder="Filtrar por vacina, fabricante, lote ou veterinário..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            {loadingVacinas ? (
              <div className="text-center py-10 text-gray-500">Carregando histórico de vacinas...</div>
            ) : vacinasFiltradas.length === 0 ? (
              <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
                Nenhuma vacina encontrada com esse filtro.
              </div>
            ) : (
              <div className="space-y-3">
                {vacinasFiltradas.slice(0, limiteVacinas).map((vacina) => (
                  <div key={vacina.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <p className="font-semibold text-gray-800">{vacina.nome_vacina || 'Vacina'}</p>
                      <p className="text-xs text-gray-500">{formatarData(vacina.data_aplicacao)}</p>
                    </div>
                    <p className="text-sm text-gray-600">Fabricante: {vacina.fabricante || '-'}</p>
                    <p className="text-sm text-gray-600">Lote: {vacina.lote || '-'}</p>
                    <p className="text-sm text-gray-600">
                      Próxima dose: {formatarData(vacina.proxima_dose || vacina.data_proxima_dose)}
                    </p>
                    <p className="text-sm text-gray-600">
                      Veterinário: {vacina.veterinario_responsavel || vacina.veterinario_nome || '-'}
                    </p>
                    {vacina.observacoes && (
                      <p className="text-sm text-gray-700 mt-1">Obs.: {vacina.observacoes}</p>
                    )}
                  </div>
                ))}

                {vacinasFiltradas.length > limiteVacinas && (
                  <div className="pt-1">
                    <button
                      onClick={() => setLimiteVacinas((prev) => prev + 6)}
                      className="text-sm text-blue-600 hover:text-blue-700 underline"
                    >
                      Ver mais vacinas ({vacinasFiltradas.length - limiteVacinas} restantes)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Aba: Consultas */}
        {abaAtiva === 'consultas' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Histórico de Consultas</h2>
              <button
                onClick={() => navigate(`/veterinario/consultas/nova?pet_id=${pet.id}`)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
              >
                + Nova Consulta
              </button>
            </div>

            <div>
              <input
                type="text"
                value={filtroConsultas}
                onChange={(e) => setFiltroConsultas(e.target.value)}
                placeholder="Filtrar por motivo, diagnóstico, veterinário ou status..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            {loadingConsultas ? (
              <div className="text-center py-10 text-gray-500">Carregando histórico de consultas...</div>
            ) : consultasFiltradas.length === 0 ? (
              <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
                Nenhuma consulta encontrada com esse filtro.
              </div>
            ) : (
              <div className="space-y-3">
                {consultasFiltradas.slice(0, limiteConsultas).map((consulta) => (
                  <div key={consulta.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <p className="font-semibold text-gray-800">
                        {consulta.queixa_principal || consulta.motivo_consulta || 'Consulta veterinária'}
                      </p>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        {consulta.status || 'registrada'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">
                      Data: {formatarDataHora(consulta.inicio_atendimento || consulta.created_at)}
                    </p>
                    <p className="text-sm text-gray-600">
                      Veterinário: {consulta.veterinario_nome || '-'}
                    </p>
                    <p className="text-sm text-gray-700 mt-1">
                      Diagnóstico: {consulta.diagnostico || '-'}
                    </p>
                    <div className="mt-2">
                      <button
                        onClick={() => navigate(`/veterinario/consultas/${consulta.id}`)}
                        className="text-sm text-blue-600 hover:text-blue-700 underline"
                      >
                        Abrir consulta completa
                      </button>
                    </div>
                  </div>
                ))}

                {consultasFiltradas.length > limiteConsultas && (
                  <div className="pt-1">
                    <button
                      onClick={() => setLimiteConsultas((prev) => prev + 6)}
                      className="text-sm text-blue-600 hover:text-blue-700 underline"
                    >
                      Ver mais consultas ({consultasFiltradas.length - limiteConsultas} restantes)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Aba: Serviços */}
        {abaAtiva === 'internacoes' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Histórico de Internações</h2>
              <button
                onClick={() => navigate('/veterinario/internacoes')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
              >
                Abrir módulo de internações
              </button>
            </div>

            {loadingInternacoes ? (
              <div className="text-center py-10 text-gray-500">Carregando histórico...</div>
            ) : historicoInternacoes.length === 0 ? (
              <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg bg-gray-50">
                Nenhuma internação registrada para este pet.
              </div>
            ) : (
              <div className="space-y-4">
                {historicoInternacoes.map((internacao) => (
                  <div key={internacao.internacao_id} className="border border-gray-200 rounded-lg p-4 bg-white">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <p className="font-semibold text-gray-800">
                        Internação #{internacao.internacao_id} {internacao.box ? `• Baia ${internacao.box}` : '• Sem baia'}
                      </p>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${internacao.status === 'alta' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                        {internacao.status}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600">Motivo: {internacao.motivo || '-'}</p>
                    <p className="text-sm text-gray-600">Entrada: {formatarDataHora(internacao.data_entrada)}</p>
                    <p className="text-sm text-gray-600">Alta: {formatarDataHora(internacao.data_saida)}</p>
                    {internacao.observacoes_alta && (
                      <p className="text-sm text-green-700 mt-1">Obs. alta: {internacao.observacoes_alta}</p>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-xs font-semibold text-gray-600 mb-2">Evoluções ({internacao.evolucoes?.length || 0})</p>
                        {(internacao.evolucoes?.length || 0) === 0 ? (
                          <p className="text-xs text-gray-400">Nenhuma evolução.</p>
                        ) : (
                          <div className="space-y-2">
                            {(internacao.evolucoes || []).slice(0, 5).map((ev) => (
                              <div key={ev.id} className="text-xs text-gray-700 border border-gray-200 bg-white rounded p-2">
                                <p className="text-gray-500">{formatarDataHora(ev.data_hora)}</p>
                                <p>Temp: {ev.temperatura || '-'} • FC: {ev.freq_cardiaca || '-'} • FR: {ev.freq_respiratoria || '-'}</p>
                                {ev.observacoes && <p className="text-gray-600">{ev.observacoes}</p>}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-xs font-semibold text-gray-600 mb-2">Procedimentos ({internacao.procedimentos?.length || 0})</p>
                        {(internacao.procedimentos?.length || 0) === 0 ? (
                          <p className="text-xs text-gray-400">Nenhum procedimento.</p>
                        ) : (
                          <div className="space-y-2">
                            {(internacao.procedimentos || []).slice(0, 8).map((proc, idx) => (
                              <div key={`${proc.id || idx}_pet_proc`} className="text-xs text-gray-700 border border-gray-200 bg-white rounded p-2">
                                <div className="flex items-center justify-between gap-2 mb-1">
                                  <p className="font-semibold text-gray-800">{proc.medicamento || 'Procedimento'}</p>
                                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${proc.status === 'agendado' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                                    {proc.status === 'agendado' ? 'Agendado' : 'Concluído'}
                                  </span>
                                </div>
                                <p>Agendado: {formatarDataHora(proc.horario_agendado)}</p>
                                <p>Executado: {formatarDataHora(proc.horario_execucao)}</p>
                                <p>Dose: {proc.dose || '-'} • Via: {proc.via || '-'}</p>
                                <p>Responsável: {proc.executado_por || '-'}</p>
                                {proc.observacao_execucao && <p>Obs: {proc.observacao_execucao}</p>}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
            {Array.isArray(carteirinha?.alertas) && carteirinha.alertas.length > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-900 mb-2">Alertas para banho, tosa e serviços</h3>
                <div className="space-y-2 text-sm text-amber-900">
                  {carteirinha.alertas.slice(0, 5).map((alerta, idx) => (
                    <p key={`servico_alerta_${idx}`}>• {alerta.mensagem}</p>
                  ))}
                </div>
              </div>
            )}
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
