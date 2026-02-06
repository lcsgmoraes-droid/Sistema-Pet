import { useState, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { 
  FiPlus, FiEdit2, FiTrash2, FiSearch, FiX, FiPhone, FiMail,
  FiMapPin, FiUser, FiSave, FiAlertCircle, FiCheck, FiArrowLeft, FiArrowRight,
  FiDollarSign, FiTrendingUp, FiTrendingDown, FiCreditCard, FiUploadCloud, FiCalendar, FiMessageCircle
} from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import ModalImportacaoPessoas from '../components/ModalImportacaoPessoas';
import ClienteTimeline from '../components/ClienteTimeline';
import { ClienteSegmentos, SegmentoBadge } from '../components/ClienteSegmentos';
import ClienteInsights from '../components/ClienteInsights';

const Pessoas = () => {
  const navigate = useNavigate();
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showModalImportacao, setShowModalImportacao] = useState(false);
  const [editingCliente, setEditingCliente] = useState(null);
  const [error, setError] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState('todos'); // Filtro por tipo: todos, cliente, fornecedor, veterinario, funcionario
  const [loadingCep, setLoadingCep] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [pets, setPets] = useState([]);
  const [editingPetIndex, setEditingPetIndex] = useState(null);
  const [cepError, setCepError] = useState('');
  const [clienteDuplicado, setClienteDuplicado] = useState(null);
  const [showDuplicadoWarning, setShowDuplicadoWarning] = useState(false);
  const [showConfirmacaoRemocao, setShowConfirmacaoRemocao] = useState(false);
  const [racas, setRacas] = useState([]);
  const [expandedPets, setExpandedPets] = useState({});
  const [highlightedPetId, setHighlightedPetId] = useState(null);
  const [petIdToEdit, setPetIdToEdit] = useState(null);
  const [resumoFinanceiro, setResumoFinanceiro] = useState(null);
  const [loadingResumo, setLoadingResumo] = useState(false);
  
  // Form states
  const [formData, setFormData] = useState({
    tipo_cadastro: 'cliente', // cliente, fornecedor, veterinario
    tipo_pessoa: 'PF', // PF ou PJ
    nome: '',
    cpf: '',
    email: '',
    telefone: '',
    celular: '',
    celular_whatsapp: true,
    // Campos PJ
    cnpj: '',
    inscricao_estadual: '',
    razao_social: '',
    nome_fantasia: '',
    responsavel: '',
    // Campo veterinário
    crmv: '',
    // Sistema de parceiros (comissões)
    parceiro_ativo: false,
    parceiro_desde: '',
    parceiro_observacoes: '',
    // Endereço
    cep: '',
    endereco: '',
    numero: '',
    complemento: '',
    bairro: '',
    cidade: '',
    estado: '',
    // Endereços de entrega
    endereco_entrega: '',
    endereco_entrega_2: '',
    // Campos de entrega (Sprint 1 - Bloco 4)
    is_entregador: false,
    entregador_ativo: true,
    entregador_padrao: false,
    tipo_vinculo_entrega: '',
    // Funcionário com controla RH
    controla_rh: false,
    gera_conta_pagar_custo_entrega: false,
    media_entregas_configurada: '',
    custo_rh_ajustado: '',
    // Terceirizado/Eventual
    modelo_custo_entrega: '',
    taxa_fixa_entrega: '',
    valor_por_km_entrega: '',
    // Moto
    moto_propria: true,
    // 📆 Acerto financeiro (ETAPA 4)
    tipo_acerto_entrega: '',
    dia_semana_acerto: '',
    dia_mes_acerto: '',
    // Legado (manter compatibilidade)
    is_terceirizado: false,
    recebe_repasse: false,
    gera_conta_pagar: false,
    observacoes: '',
    tags: ''
  });

  // Estado para endereços adicionais
  const [enderecosAdicionais, setEnderecosAdicionais] = useState([]);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [mostrarFormEndereco, setMostrarFormEndereco] = useState(false);

  const [currentPet, setCurrentPet] = useState({
    nome: '',
    especie: '',
    raca: '',
    sexo: '',
    data_nascimento: '',
    cor: '',
    peso: '',
    observacoes: '',
    castrado: false,
    porte: '',
    microchip: '',
    alergias: '',
    doencas_cronicas: '',
    medicamentos_continuos: '',
    historico_clinico: '',
    foto_url: '',
    idade_aproximada: ''
  });

  const steps = [
    { number: 1, title: 'Informações do cliente' },
    { number: 2, title: 'Contatos' },
    { number: 3, title: 'Endereço' },
    { number: 4, title: 'Informações complementares' },
    { number: 5, title: 'Animais' },
    { number: 6, title: 'Financeiro' }
  ];

  useEffect(() => {
    loadClientes();
  }, [tipoFiltro]);

  // Carregar raças quando espécie mudar
  useEffect(() => {
    if (currentPet && currentPet.especie) {
      loadRacas(currentPet.especie);
    } else {
      setRacas([]);
    }
  }, [currentPet?.especie]);

  // Editar pet automaticamente quando pets são carregados
  useEffect(() => {
    if (petIdToEdit && pets.length > 0) {
      const petIndex = pets.findIndex(p => p.id === petIdToEdit);
      if (petIndex !== -1) {
        editPet(petIndex);
        setPetIdToEdit(null); // Limpar após editar
      }
    }
  }, [pets, petIdToEdit]);

  const loadRacas = async (especie) => {
    try {
      const response = await api.get(`/clientes/racas?especie=${especie}`);
      setRacas(response.data);
    } catch (err) {
      console.error('Erro ao carregar raças:', err);
      setRacas([]);
    }
  };

  const loadClientes = async () => {
    try {
      setLoading(true);
      const url = tipoFiltro === 'todos' ? '/clientes/' : `/clientes/?tipo_cadastro=${tipoFiltro}`;
      const response = await api.get(url);
      setClientes(response.data);
    } catch (err) {
      setError('Erro ao carregar pessoas');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const buscarCep = async (cep) => {
    const cepLimpo = cep.replace(/\D/g, '');
    
    if (cepLimpo.length !== 8) return;
    
    setLoadingCep(true);
    setCepError('');
    setError('');
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
      const data = await response.json();
      
      if (data.erro) {
        setCepError('CEP não encontrado');
        return;
      }
      
      setFormData(prev => ({
        ...prev,
        endereco: data.logradouro || '',
        bairro: data.bairro || '',
        cidade: data.localidade || '',
        estado: data.uf || '',
        cep: cep
      }));
    } catch (err) {
      console.error('Erro ao buscar CEP:', err);
    } finally {
      setLoadingCep(false);
    }
  };

  // Funções de gerenciamento de endereços adicionais
  const abrirModalEndereco = (index = null) => {
    if (index !== null) {
      // Editando endereço existente
      setEnderecoAtual({ ...enderecosAdicionais[index], index });
    } else {
      // Novo endereço
      setEnderecoAtual({
        tipo: 'entrega',
        apelido: '',
        cep: '',
        endereco: '',
        numero: '',
        complemento: '',
        bairro: '',
        cidade: '',
        estado: ''
      });
    }
    setMostrarFormEndereco(true);
  };

  const fecharModalEndereco = () => {
    setMostrarFormEndereco(false);
    setEnderecoAtual(null);
  };

  const buscarCepModal = async (cep) => {
    if (!cep || cep.length !== 9) return;

    setLoadingCep(true);
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep.replace('-', '')}/json/`);
      const data = await response.json();

      if (data.erro) {
        alert('CEP não encontrado');
        return;
      }

      setEnderecoAtual(prev => ({
        ...prev,
        endereco: data.logradouro || '',
        bairro: data.bairro || '',
        cidade: data.localidade || '',
        estado: data.uf || ''
      }));
    } catch (error) {
      console.error('Erro ao buscar CEP:', error);
      alert('Erro ao buscar CEP');
    } finally {
      setLoadingCep(false);
    }
  };

  const salvarEndereco = () => {
    if (!enderecoAtual.cep || !enderecoAtual.endereco || !enderecoAtual.cidade) {
      alert('Preencha pelo menos CEP, Endereço e Cidade');
      return;
    }

    const novosEnderecos = [...enderecosAdicionais];
    
    if (enderecoAtual.index !== undefined) {
      // Editando endereço existente
      novosEnderecos[enderecoAtual.index] = { ...enderecoAtual };
      delete novosEnderecos[enderecoAtual.index].index;
    } else {
      // Novo endereço
      novosEnderecos.push({ ...enderecoAtual });
    }

    setEnderecosAdicionais(novosEnderecos);
    fecharModalEndereco();
  };

  const removerEndereco = (index) => {
    if (confirm('Deseja realmente remover este endereço?')) {
      const novosEnderecos = enderecosAdicionais.filter((_, i) => i !== index);
      setEnderecosAdicionais(novosEnderecos);
    }
  };

  const handleSubmitFinal = async () => {
    setError('');

    try {
      // ✅ VALIDAÇÕES DE ENTREGADOR (ETAPA 4)
      if (formData.is_entregador) {
        // Validar tipo de acerto
        if (!formData.tipo_acerto_entrega) {
          alert("Informe o tipo de acerto do entregador (semanal, quinzenal ou mensal)");
          return;
        }

        // Validar dia da semana para acerto semanal
        if (formData.tipo_acerto_entrega === 'semanal' && !formData.dia_semana_acerto) {
          alert("Informe o dia da semana para o acerto semanal");
          return;
        }

        // Validar dia do mês para acerto mensal
        if (formData.tipo_acerto_entrega === 'mensal' && !formData.dia_mes_acerto) {
          alert("Informe o dia do mês para o acerto mensal");
          return;
        }

        // Validar range do dia do mês (1-28)
        if (formData.tipo_acerto_entrega === 'mensal') {
          const dia = parseInt(formData.dia_mes_acerto);
          if (dia < 1 || dia > 28) {
            alert("O dia do mês deve estar entre 1 e 28");
            return;
          }
        }
      }

      // Remover campos que não existem no backend
      const { celular_whatsapp, tags, ...clienteData } = formData;
      
      // 🚚 LÓGICA AUTOMÁTICA DE ENTREGA baseada em tipo_cadastro
      if (clienteData.is_entregador) {
        // Se é funcionário → tipo_vinculo = "funcionario" automaticamente
        if (clienteData.tipo_cadastro === 'funcionario') {
          clienteData.tipo_vinculo_entrega = 'funcionario';
          clienteData.is_terceirizado = false;
        }
        // Se é fornecedor → is_terceirizado = true e tipo_vinculo = "terceirizado" automaticamente
        else if (clienteData.tipo_cadastro === 'fornecedor') {
          clienteData.is_terceirizado = true;
          clienteData.tipo_vinculo_entrega = 'terceirizado';
        }
      }
      
      // Adicionar endereços adicionais aos dados do cliente
      clienteData.enderecos_adicionais = enderecosAdicionais.length > 0 ? enderecosAdicionais : null;
      
      // Remover campos vazios (transformar "" em null)
      Object.keys(clienteData).forEach(key => {
        if (clienteData[key] === '') {
          clienteData[key] = null;
        }
      });
      
      // Garantir que tipo_cadastro nunca seja 'todos'
      if (clienteData.tipo_cadastro === 'todos') {
        clienteData.tipo_cadastro = 'cliente';
      }
      
      // 🐛 DEBUG: Verificar entregador_padrao
      console.log('🐛 entregador_padrao antes do envio:', clienteData.entregador_padrao);
      console.log('🐛 is_entregador:', clienteData.is_entregador);
      
      console.log('Dados enviados:', clienteData);
      
      let clienteId;
      
      if (editingCliente) {
        // Atualizar cliente existente
        await api.put(`/clientes/${editingCliente.id}`, clienteData);
        clienteId = editingCliente.id;
      } else {
        // Criar novo cliente
        const clienteResponse = await api.post('/clientes/', clienteData);
        clienteId = clienteResponse.data.id;
      }
      
      // Criar/atualizar pets vinculados
      for (const pet of pets) {
        // Guardar o ID antes de limpar
        const petId = pet.id;
        
        // Limpar e converter dados do pet
        const petData = { ...pet };
        
        // Remover campos de controle interno
        delete petData.id;
        delete petData.created_at;
        delete petData.updated_at;
        delete petData.cliente_id;
        delete petData.user_id;
        delete petData.ativo;
        delete petData.codigo;
        
        // Converter strings vazias em null
        Object.keys(petData).forEach(key => {
          if (petData[key] === '') {
            petData[key] = null;
          }
        });
        
        // Converter peso para float se houver valor
        if (petData.peso !== null && petData.peso !== undefined) {
          petData.peso = parseFloat(petData.peso) || null;
        }
        
        if (petId) {
          // Atualizar pet existente
          console.log(`Atualizando pet ${petId}:`, petData);
          await api.put(`/clientes/pets/${petId}`, petData);
        } else {
          // Criar novo pet
          console.log('Criando novo pet:', petData);
          await api.post(`/clientes/${clienteId}/pets`, petData);
        }
      }
      
      loadClientes();
      closeModal();
    } catch (err) {
      const errorDetails = err.response?.data?.details;
      setError(err.response?.data?.message || 'Erro ao salvar cliente');
      console.error('Erro completo:', err.response?.data);
      console.error('Detalhes de validação:', errorDetails);
      
      // Mostrar cada erro de campo
      if (errorDetails && Array.isArray(errorDetails)) {
        errorDetails.forEach((detail, index) => {
          console.error(`Erro ${index + 1}:`, {
            campo: detail.loc,
            tipo: detail.type,
            mensagem: detail.msg
          });
        });
      }
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Tem certeza que deseja excluir este cliente?')) return;

    try {
      console.log('Excluindo cliente ID:', id);
      const response = await api.delete(`/clientes/${id}`);
      console.log('Cliente excluído com sucesso:', response);
      await loadClientes();
    } catch (err) {
      console.error('Erro ao excluir cliente:', err);
      console.error('Resposta do erro:', err.response);
      setError(err.response?.data?.detail || 'Erro ao excluir cliente');
    }
  };

  const handleDeletePet = async (petId) => {
    if (!confirm('Tem certeza que deseja excluir este pet?')) return;

    try {
      console.log('Excluindo pet ID:', petId);
      await api.delete(`/clientes/pets/${petId}`);
      console.log('Pet excluído com sucesso');
      
      // Limpar estado de expansão para forçar re-render
      setExpandedPets({});
      
      // Atualizar lista de clientes
      await loadClientes();
      console.log('Lista de clientes atualizada');
    } catch (err) {
      console.error('Erro ao excluir pet:', err);
      alert(err.response?.data?.detail || 'Erro ao excluir pet');
    }
  };

  // Carregar apenas resumo financeiro leve (não o histórico completo)
  const loadResumoFinanceiro = async (clienteId) => {
    if (!clienteId) return;
    
    try {
      setLoadingResumo(true);
      // Nova rota otimizada - apenas agregações
      const response = await api.get(`/financeiro/cliente/${clienteId}/resumo`);
      setResumoFinanceiro(response.data.resumo);
    } catch (err) {
      // Silencioso se 404 (cliente sem histórico financeiro ainda)
      if (err.response?.status !== 404) {
        console.error('Erro ao carregar resumo financeiro:', err);
      }
      setResumoFinanceiro(null);
    } finally {
      setLoadingResumo(false);
    }
  };

  const openModal = (cliente = null, tipo = null, petIdToEdit = null) => {
    if (cliente) {
      setEditingCliente(cliente);
      
      // 🐛 DEBUG: Verificar o que vem do backend
      console.log('🐛 Cliente carregado do backend:', {
        id: cliente.id,
        nome: cliente.nome,
        is_entregador: cliente.is_entregador,
        entregador_padrao: cliente.entregador_padrao,
        entregador_padrao_tipo: typeof cliente.entregador_padrao
      });
      
      setFormData({
        tipo_cadastro: cliente.tipo_cadastro || 'cliente',
        tipo_pessoa: cliente.tipo_pessoa || 'PF',
        nome: cliente.nome,
        cpf: cliente.cpf || '',
        email: cliente.email || '',
        telefone: cliente.telefone || '',
        celular: cliente.celular || '',
        celular_whatsapp: true,
        cnpj: cliente.cnpj || '',
        inscricao_estadual: cliente.inscricao_estadual || '',
        razao_social: cliente.razao_social || '',
        nome_fantasia: cliente.nome_fantasia || '',
        responsavel: cliente.responsavel || '',
        crmv: cliente.crmv || '',
        // Sistema de parceiros
        parceiro_ativo: cliente.parceiro_ativo || false,
        parceiro_desde: cliente.parceiro_desde || '',
        parceiro_observacoes: cliente.parceiro_observacoes || '',
        cep: cliente.cep || '',
        endereco: cliente.endereco || '',
        numero: cliente.numero || '',
        complemento: cliente.complemento || '',
        bairro: cliente.bairro || '',
        cidade: cliente.cidade || '',
        estado: cliente.estado || '',
        endereco_entrega: cliente.endereco_entrega || '',
        endereco_entrega_2: cliente.endereco_entrega_2 || '',
        // Campos de entrega
        is_entregador: cliente.is_entregador || false,
        entregador_ativo: cliente.entregador_ativo !== undefined ? cliente.entregador_ativo : true,
        entregador_padrao: cliente.entregador_padrao || false,
        tipo_vinculo_entrega: cliente.tipo_vinculo_entrega || '',
        // Funcionário com controla RH
        controla_rh: cliente.controla_rh || false,
        gera_conta_pagar_custo_entrega: cliente.gera_conta_pagar_custo_entrega || false,
        media_entregas_configurada: cliente.media_entregas_configurada || '',
        custo_rh_ajustado: cliente.custo_rh_ajustado || '',
        // Terceirizado/Eventual
        modelo_custo_entrega: cliente.modelo_custo_entrega || '',
        taxa_fixa_entrega: cliente.taxa_fixa_entrega || '',
        valor_por_km_entrega: cliente.valor_por_km_entrega || '',
        // Moto
        moto_propria: cliente.moto_propria !== undefined ? cliente.moto_propria : true,
        // 📆 Acerto financeiro (ETAPA 4)
        tipo_acerto_entrega: cliente.tipo_acerto_entrega || '',
        dia_semana_acerto: cliente.dia_semana_acerto || '',
        dia_mes_acerto: cliente.dia_mes_acerto || '',
        // Legado (manter compatibilidade)
        is_terceirizado: cliente.is_terceirizado || false,
        recebe_repasse: cliente.recebe_repasse || false,
        gera_conta_pagar: cliente.gera_conta_pagar || false,
        observacoes: cliente.observacoes || '',
        tags: ''
      });
      setPets(cliente.pets || []);
      
      // Carregar endereços adicionais
      setEnderecosAdicionais(cliente.enderecos_adicionais || []);
      
      // Carregar apenas resumo financeiro leve (não histórico completo)
      loadResumoFinanceiro(cliente.id);
      
      // Se um pet específico deve ser editado, marcar para edição
      if (petIdToEdit) {
        setPetIdToEdit(petIdToEdit);
        setCurrentStep(5);
      } else {
        setCurrentStep(1);
        setPetIdToEdit(null);
      }
    } else {
      setEditingCliente(null);
      // Se tipoFiltro for 'todos', usar 'cliente' como padrão
      const tipoCadastro = tipo || (tipoFiltro === 'todos' ? 'cliente' : tipoFiltro);
      // Fornecedor deve ser PJ por padrão
      const tipoPessoa = tipoCadastro === 'fornecedor' ? 'PJ' : 'PF';
      
      setFormData({
        tipo_cadastro: tipoCadastro,
        tipo_pessoa: tipoPessoa,
        nome: '',
        cpf: '',
        email: '',
        telefone: '',
        celular: '',
        celular_whatsapp: true,
        cnpj: '',
        inscricao_estadual: '',
        razao_social: '',
        nome_fantasia: '',
        responsavel: '',
        crmv: '',
        // Sistema de parceiros
        parceiro_ativo: false,
        parceiro_desde: '',
        parceiro_observacoes: '',
        cep: '',
        endereco: '',
        numero: '',
        complemento: '',
        bairro: '',
        cidade: '',
        estado: '',
        // Campos de entrega
        is_entregador: false,
        entregador_ativo: true,
        tipo_vinculo_entrega: '',
        // Funcionário com controla RH
        controla_rh: false,
        media_entregas_configurada: '',
        custo_rh_ajustado: '',
        // Terceirizado/Eventual
        modelo_custo_entrega: '',
        taxa_fixa_entrega: '',
        valor_por_km_entrega: '',
        // Moto
        moto_propria: true,
        // Legado (manter compatibilidade)
        is_terceirizado: false,
        recebe_repasse: false,
        gera_conta_pagar: false,
        observacoes: '',
        tags: ''
      });
      setPets([]);
      setEnderecosAdicionais([]); // Limpar endereços adicionais
      setCurrentStep(1);
    }
    setShowModal(true);
    setError('');
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingCliente(null);
    setCurrentStep(1);
    setPets([]);
    setClienteDuplicado(null);
    setShowDuplicadoWarning(false);
    setShowConfirmacaoRemocao(false);
    setHighlightedPetId(null);
    setPetIdToEdit(null);
    setResumoFinanceiro(null);
  };

  const verificarDuplicata = async () => {
    try {
      const params = new URLSearchParams();
      
      if (formData.cpf) params.append('cpf', formData.cpf);
      if (formData.cnpj) params.append('cnpj', formData.cnpj);
      if (formData.telefone) params.append('telefone', formData.telefone);
      if (formData.celular) params.append('celular', formData.celular);
      if (formData.crmv) params.append('crmv', formData.crmv);
      if (editingCliente) params.append('cliente_id', editingCliente.id);
      
      if (params.toString()) {
        const response = await api.get(`/clientes/verificar-duplicata/campo?${params.toString()}`);
        
        if (response.data.duplicado) {
          setClienteDuplicado(response.data);
          setShowDuplicadoWarning(true);
          return true;
        }
      }
      return false;
    } catch (err) {
      console.error('Erro ao verificar duplicata:', err);
      return false;
    }
  };

  const nextStep = async () => {
    if (currentStep < 6) {
      setError('');
      setCepError('');
      
      // Verificar duplicatas na aba 1 (documentos: CPF/CNPJ/CRMV)
      if (currentStep === 1) {
        const temDuplicata = await verificarDuplicata();
        if (temDuplicata) {
          return; // Não avança se houver duplicata
        }
      }
      
      // Verificar duplicatas na aba 2 (contatos: telefone/celular)
      if (currentStep === 2) {
        const temDuplicata = await verificarDuplicata();
        if (temDuplicata) {
          return; // Não avança se houver duplicata
        }
      }
      
      setCurrentStep(currentStep + 1);
    }
  };

  const continuarMesmoDuplicado = () => {
    // Mostrar confirmação de remoção
    setShowConfirmacaoRemocao(true);
  };

  const confirmarRemocaoEContinuar = async () => {
    try {
      setLoading(true);
      
      // Calcular próximo código disponível
      const proximoCodigo = editingCliente?.codigo || 
        (clientes.length > 0 ? Math.max(...clientes.map(c => c.codigo)) + 1 : 1);
      
      // Remover campo duplicado do cadastro antigo
      await api.put(
        `/clientes/${clienteDuplicado.cliente.id}/remover-campo`,
        null,
        {
          params: {
            campo: clienteDuplicado.campo,
            novo_cliente_codigo: proximoCodigo
          }
        }
      );
      
      // Fechar avisos e continuar
      setShowConfirmacaoRemocao(false);
      setShowDuplicadoWarning(false);
      setClienteDuplicado(null);
      setCurrentStep(currentStep + 1);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao remover campo duplicado');
    } finally {
      setLoading(false);
    }
  };

  const cancelarRemocao = () => {
    setShowConfirmacaoRemocao(false);
  };

  const irParaClienteExistente = () => {
    closeModal();
    // Scroll até o cliente existente
    const elemento = document.getElementById(`cliente-${clienteDuplicado.cliente.id}`);
    if (elemento) {
      elemento.scrollIntoView({ behavior: 'smooth', block: 'center' });
      elemento.classList.add('ring-4', 'ring-yellow-400');
      setTimeout(() => {
        elemento.classList.remove('ring-4', 'ring-yellow-400');
      }, 3000);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setError('');
      setCepError('');
      setCurrentStep(currentStep - 1);
    }
  };

  const addPet = () => {
    if (!currentPet.nome || !currentPet.especie) {
      setError('Nome e espécie são obrigatórios');
      return;
    }

    if (editingPetIndex !== null) {
      // Atualizar pet existente - preservar ID e campos originais
      const updatedPets = [...pets];
      const originalPet = pets[editingPetIndex];
      updatedPets[editingPetIndex] = { 
        ...currentPet,
        id: originalPet.id, // Preservar ID original
        created_at: originalPet.created_at,
        updated_at: originalPet.updated_at,
        cliente_id: originalPet.cliente_id,
        codigo: originalPet.codigo
      };
      setPets(updatedPets);
      setEditingPetIndex(null);
    } else {
      // Adicionar novo pet
      setPets([...pets, { ...currentPet }]);
    }
    
    setCurrentPet({
      nome: '',
      especie: '',
      raca: '',
      sexo: '',
      data_nascimento: '',
      cor: '',
      peso: '',
      observacoes: '',
      castrado: false,
      porte: '',
      microchip: '',
      alergias: '',
      doencas_cronicas: '',
      medicamentos_continuos: '',
      historico_clinico: '',
      foto_url: '',
      idade_aproximada: ''
    });
    setError('');
    setHighlightedPetId(null); // Limpar destaque
  };

  const editPet = (index) => {
    const pet = pets[index];
    setCurrentPet({
      nome: pet.nome || '',
      especie: pet.especie || '',
      raca: pet.raca || '',
      sexo: pet.sexo || '',
      data_nascimento: pet.data_nascimento || '',
      cor: pet.cor || '',
      peso: pet.peso || '',
      observacoes: pet.observacoes || '',
      castrado: pet.castrado || false,
      porte: pet.porte || '',
      microchip: pet.microchip || '',
      alergias: pet.alergias || '',
      doencas_cronicas: pet.doencas_cronicas || '',
      medicamentos_continuos: pet.medicamentos_continuos || '',
      historico_clinico: pet.historico_clinico || '',
      foto_url: pet.foto_url || '',
      idade_aproximada: pet.idade_aproximada || ''
    });
    setEditingPetIndex(index);
    // Destacar o pet sendo editado
    if (pet?.id) {
      setHighlightedPetId(pet.id);
    }
  };

  const cancelEditPet = () => {
    setCurrentPet({
      nome: '',
      especie: '',
      raca: '',
      sexo: '',
      data_nascimento: '',
      cor: '',
      peso: '',
      observacoes: '',
      castrado: false,
      porte: '',
      microchip: '',
      alergias: '',
      doencas_cronicas: '',
      medicamentos_continuos: '',
      historico_clinico: '',
      foto_url: '',
      idade_aproximada: ''
    });
    setEditingPetIndex(null);
  };

  const removePet = (index) => {
    setPets(pets.filter((_, i) => i !== index));
  };

  const filteredClientes = clientes.filter(cliente =>
    cliente.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cliente.cpf?.includes(searchTerm) ||
    cliente.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cliente.celular?.includes(searchTerm)
  );

  // ============================================================================
  // COMPONENTE: ClienteSegmentoBadgeWrapper (lazy load badge na lista)
  // ============================================================================
  function ClienteSegmentoBadgeWrapper({ clienteId }) {
    const [segmento, setSegmento] = useState(null);
    const [loading, setLoading] = useState(false);
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
      if (clienteId && !loaded) {
        loadSegmento();
      }
    }, [clienteId]);

    const loadSegmento = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/segmentacao/clientes/${clienteId}`);
        setSegmento(response.data.segmento);
      } catch (err) {
        // Cliente sem segmento (404) - silencioso
        if (err.response?.status !== 404) {
          console.error('Erro ao carregar segmento:', err);
        }
      } finally {
        setLoading(false);
        setLoaded(true);
      }
    };

    if (loading) {
      return <span className="text-xs text-gray-400">...</span>;
    }

    if (!segmento) {
      return <span className="text-xs text-gray-400">-</span>;
    }

    return <SegmentoBadge segmento={segmento} size="sm" />;
  }

  // ============================================================================
  // COMPONENTE: WhatsAppHistorico
  // ============================================================================
  function WhatsAppHistorico({ clienteId }) {
    const [mensagens, setMensagens] = useState([]);
    const [loadingMensagens, setLoadingMensagens] = useState(true);

    useEffect(() => {
      if (clienteId) {
        loadMensagens();
      }
    }, [clienteId]);

    const loadMensagens = async () => {
      try {
        setLoadingMensagens(true);
        const response = await api.get(`/api/whatsapp/clientes/${clienteId}/whatsapp/ultimas?limit=5`);
        setMensagens(response.data);
      } catch (err) {
        console.error('Erro ao carregar mensagens:', err);
        setMensagens([]);
      } finally {
        setLoadingMensagens(false);
      }
    };

    if (loadingMensagens) {
      return (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
          <p className="text-sm text-gray-600 mt-2">Carregando mensagens...</p>
        </div>
      );
    }

    if (mensagens.length === 0) {
      return (
        <div className="text-center py-6 text-gray-500">
          <FiMessageCircle size={32} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm">Nenhuma mensagem registrada ainda</p>
          <p className="text-xs mt-1">As mensagens enviadas e recebidas aparecerão aqui</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <p className="text-sm font-medium text-gray-700 mb-3">Últimas 5 mensagens:</p>
        {mensagens.map((msg) => (
          <div
            key={msg.id}
            className={`p-3 rounded-lg border ${
              msg.direcao === 'enviada'
                ? 'bg-green-50 border-green-200 ml-6'
                : 'bg-blue-50 border-blue-200 mr-6'
            }`}
          >
            <div className="flex items-start justify-between gap-2 mb-1">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold ${
                  msg.direcao === 'enviada' ? 'text-green-700' : 'text-blue-700'
                }`}>
                  {msg.direcao === 'enviada' ? '→ Enviada' : '← Recebida'}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  msg.status === 'lido' ? 'bg-green-200 text-green-800' :
                  msg.status === 'enviado' ? 'bg-yellow-200 text-yellow-800' :
                  msg.status === 'recebido' ? 'bg-blue-200 text-blue-800' :
                  'bg-red-200 text-red-800'
                }`}>
                  {msg.status}
                </span>
              </div>
              <span className="text-xs text-gray-500">
                {new Date(msg.created_at).toLocaleString('pt-BR')}
              </span>
            </div>
            <p className="text-sm text-gray-700">{msg.preview || msg.conteudo}</p>
          </div>
        ))}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Cadastros</h1>
        <p className="text-gray-600 mt-1">Gerenciamento de clientes, fornecedores, veterinários, funcionários e pets</p>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex gap-2">
          <button
            onClick={() => setTipoFiltro('todos')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === 'todos'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setTipoFiltro('cliente')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === 'cliente'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Clientes
          </button>
          <button
            onClick={() => setTipoFiltro('fornecedor')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === 'fornecedor'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Fornecedores
          </button>
          <button
            onClick={() => setTipoFiltro('veterinario')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === 'veterinario'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Veterinários
          </button>
          <button
            onClick={() => setTipoFiltro('funcionario')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === 'funcionario'
                ? 'border-purple-600 text-purple-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            Funcionários
          </button>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6 flex flex-col sm:flex-row gap-4 justify-between">
        <div className="relative flex-1 max-w-md">
          <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por nome, CPF/CNPJ, email ou telefone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
          />
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowModalImportacao(true)}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <FiUploadCloud /> Importar Excel
          </button>
          <button
            onClick={() => openModal(null, tipoFiltro)}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <FiPlus /> Novo {tipoFiltro === 'cliente' ? 'Cliente' : tipoFiltro === 'fornecedor' ? 'Fornecedor' : tipoFiltro === 'veterinario' ? 'Veterinário' : tipoFiltro === 'funcionario' ? 'Funcionário' : 'Cadastro'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && !showModal && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <FiAlertCircle />
          <span>{error}</span>
        </div>
      )}

      {/* Clientes Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {filteredClientes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nome
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    CPF/CNPJ
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Celular
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pets
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Segmento
                  </th>
                  <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredClientes.map((cliente) => (
                  <Fragment key={cliente.id}>
                    <tr 
                      id={`cliente-${cliente.id}`} 
                      onClick={() => openModal(cliente)}
                      className="hover:bg-gray-50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                        {cliente.codigo}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex flex-col gap-1">
                          <span className="text-sm font-medium text-gray-900">{cliente.nome}</span>
                          {cliente.tipo_pessoa === 'PJ' && cliente.razao_social && (
                            <span className="text-xs text-gray-500">{cliente.razao_social}</span>
                          )}
                          {cliente.parceiro_ativo && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full w-fit">
                              <FiDollarSign size={12} />
                              Parceiro
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {cliente.tipo_pessoa === 'PF' ? cliente.cpf || '-' : cliente.cnpj || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {cliente.celular || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => setExpandedPets({...expandedPets, [cliente.id]: !expandedPets[cliente.id]})}
                          className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors"
                        >
                          <PawPrint size={16} className="text-gray-400" />
                          <span>{cliente.pets?.length || 0}</span>
                          {cliente.pets && cliente.pets.length > 0 && (
                            <FiArrowRight 
                              size={14} 
                              className={`transform transition-transform ${expandedPets[cliente.id] ? 'rotate-90' : ''}`}
                            />
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {/* Desabilitado: causa muitas requisições 404 na listagem */}
                        {/* <ClienteSegmentoBadgeWrapper clienteId={cliente.id} /> */}
                        <span className="text-xs text-gray-400">-</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-2">
                          {cliente.celular && (
                            <button
                              onClick={() => {
                                const celular = cliente.celular.replace(/\D/g, '');
                                window.open(`https://wa.me/55${celular}`, '_blank');
                              }}
                              className="text-green-600 hover:text-green-900 transition-colors"
                              title="Abrir WhatsApp"
                            >
                              <FiMessageCircle size={16} />
                            </button>
                          )}
                          <button
                            onClick={() => openModal(cliente)}
                            className="text-blue-600 hover:text-blue-900 transition-colors"
                            title="Editar"
                          >
                            <FiEdit2 size={16} />
                          </button>
                          <button
                            onClick={() => handleDelete(cliente.id)}
                            className="text-red-600 hover:text-red-900 transition-colors"
                            title="Excluir"
                          >
                            <FiTrash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Pets Row */}
                    {expandedPets[cliente.id] && cliente.pets && cliente.pets.length > 0 && (
                      <tr>
                        <td colSpan="7" className="px-4 py-3 bg-gray-50">
                          <div className="space-y-2">
                            <p className="text-xs font-semibold text-gray-700 mb-2">Pets de {cliente.nome}:</p>
                            {cliente.pets.map((pet) => (
                              <div 
                                key={pet.id} 
                                className={`bg-white rounded-lg p-3 flex justify-between items-start border border-gray-200 ${
                                  highlightedPetId === pet.id 
                                    ? 'ring-2 ring-blue-400 shadow-lg bg-blue-50' 
                                    : ''
                                }`}
                              >
                                <div className="flex-1 grid grid-cols-4 gap-4">
                                  <div>
                                    <p className="text-xs text-gray-500">Nome</p>
                                    <p className="text-sm font-medium text-gray-900">{pet.nome}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-gray-500">Espécie/Raça</p>
                                    <p className="text-sm text-gray-700">{pet.especie} {pet.raca && `- ${pet.raca}`}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-gray-500">Sexo</p>
                                    <p className="text-sm text-gray-700">{pet.sexo || '-'}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-gray-500">Nascimento</p>
                                    <p className="text-sm text-gray-700">
                                      {pet.data_nascimento ? new Date(pet.data_nascimento).toLocaleDateString('pt-BR') : '-'}
                                    </p>
                                  </div>
                                </div>
                                <div className="flex gap-2 ml-4">
                                  <button
                                    onClick={() => {
                                      setHighlightedPetId(pet.id);
                                      openModal(cliente, null, pet.id);
                                    }}
                                    className="text-blue-600 hover:text-blue-900 p-1 transition-colors"
                                    title="Editar pet"
                                  >
                                    <FiEdit2 size={14} />
                                  </button>
                                  <button
                                    onClick={() => handleDeletePet(pet.id)}
                                    className="text-red-600 hover:text-red-900 p-1 transition-colors"
                                    title="Excluir pet"
                                  >
                                    <FiTrash2 size={14} />
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <FiUser className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-gray-600">Nenhum cliente encontrado</p>
          </div>
        )}
      </div>

      {/* Modal Wizard */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  {editingCliente 
                    ? `Editar ${editingCliente.tipo_cadastro === 'cliente' ? 'Cliente' : editingCliente.tipo_cadastro === 'fornecedor' ? 'Fornecedor' : 'Veterinário'}`
                    : `Adicionar ${formData.tipo_cadastro === 'cliente' ? 'Cliente' : formData.tipo_cadastro === 'fornecedor' ? 'Fornecedor' : 'Veterinário'}`
                  }
                </h2>
                <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
                  <FiX size={24} />
                </button>
              </div>

              {/* Progress Steps */}
              <div className="flex items-center justify-between mb-2">
                {steps.map((step, index) => (
                  <div key={step.number} className="flex items-center flex-1">
                    <div className="flex flex-col items-center flex-1">
                      <button
                        onClick={() => setCurrentStep(step.number)}
                        className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm transition-all hover:scale-110 cursor-pointer ${
                          currentStep > step.number ? 'bg-green-500 text-white hover:bg-green-600' :
                          currentStep === step.number ? 'bg-blue-500 text-white hover:bg-blue-600' :
                          'bg-gray-300 text-gray-600 hover:bg-gray-400'
                        }`}
                        type="button"
                        title={`Ir para: ${step.title}`}
                      >
                        {currentStep > step.number ? <FiCheck /> : step.number}
                      </button>
                      <span className="text-xs mt-1 text-center hidden md:block">{step.title}</span>
                    </div>
                    {index < steps.length - 1 && (
                      <div className={`h-0.5 flex-1 ${currentStep > step.number ? 'bg-green-500' : 'bg-gray-300'}`} />
                    )}
                  </div>
                ))}
              </div>
              <div className="text-center text-sm text-gray-600">{currentStep}/6</div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                  <FiAlertCircle />
                  <span>{error}</span>
                </div>
              )}

              {/* Aviso de Duplicata */}
              {showDuplicadoWarning && clienteDuplicado && (
                <div className="mb-4 p-4 bg-yellow-50 border-2 border-yellow-400 rounded-lg">
                  <div className="flex items-start gap-3">
                    <FiAlertCircle className="text-yellow-600 mt-1" size={24} />
                    <div className="flex-1">
                      <h4 className="font-semibold text-yellow-900 mb-2">
                        ⚠️ Cliente já cadastrado!
                      </h4>
                      <p className="text-sm text-yellow-800 mb-3">
                        Já existe um cliente com o mesmo <strong>{clienteDuplicado.campo}</strong> cadastrado:
                      </p>
                      
                      {/* Card do cliente existente */}
                      <div className="bg-white rounded-lg p-3 border border-yellow-300 mb-3">
                        <p className="font-semibold text-gray-900">{clienteDuplicado.cliente.nome}</p>
                        <p className="text-sm text-gray-600">Código: {clienteDuplicado.cliente.codigo}</p>
                        {clienteDuplicado.cliente.cpf && (
                          <p className="text-sm text-gray-600">CPF: {clienteDuplicado.cliente.cpf}</p>
                        )}
                        {clienteDuplicado.cliente.celular && (
                          <p className="text-sm text-gray-600">Celular: {clienteDuplicado.cliente.celular}</p>
                        )}
                        {clienteDuplicado.cliente.telefone && (
                          <p className="text-sm text-gray-600">Telefone: {clienteDuplicado.cliente.telefone}</p>
                        )}
                      </div>

                      {/* Confirmação de remoção */}
                      {showConfirmacaoRemocao ? (
                        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 mb-3">
                          <p className="text-sm font-semibold text-red-900 mb-2">
                            ⚠️ Atenção!
                          </p>
                          <p className="text-sm text-red-800 mb-3">
                            O <strong>{clienteDuplicado.campo}</strong> será removido do cadastro do cliente <strong>{clienteDuplicado.cliente.nome}</strong> (Código {clienteDuplicado.cliente.codigo}) 
                            e uma observação será adicionada informando a transferência.
                          </p>
                          <p className="text-xs text-red-700 mb-3">
                            No cadastro antigo ficará registrado: "Sem número por cadastro novo do cliente código {editingCliente?.codigo || (clientes.length > 0 ? Math.max(...clientes.map(c => c.codigo)) + 1 : 1)}"
                          </p>
                          <div className="flex gap-2">
                            <button
                              onClick={confirmarRemocaoEContinuar}
                              disabled={loading}
                              className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                            >
                              {loading ? 'Processando...' : 'Confirmar e continuar'}
                            </button>
                            <button
                              onClick={cancelarRemocao}
                              disabled={loading}
                              className="flex-1 px-3 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <button
                            onClick={irParaClienteExistente}
                            className="flex-1 px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm font-medium transition-colors"
                          >
                            Ver cadastro existente
                          </button>
                          <button
                            onClick={continuarMesmoDuplicado}
                            className="flex-1 px-3 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium transition-colors"
                          >
                            Continuar mesmo assim
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Step 1: Informações do Cliente */}
              {currentStep === 1 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Informações do cadastro</h3>
                  
                  {/* Tipo de Cadastro */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tipo de cadastro *
                    </label>
                    <div className="flex gap-4">
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="cliente"
                          checked={formData.tipo_cadastro === 'cliente'}
                          onChange={(e) => {
                            // Ao selecionar cliente, volta para PF
                            setFormData({...formData, tipo_cadastro: e.target.value, tipo_pessoa: 'PF'});
                          }}
                          className="mr-2"
                        />
                        <span className="text-sm">Cliente</span>
                      </label>
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="fornecedor"
                          checked={formData.tipo_cadastro === 'fornecedor'}
                          onChange={(e) => {
                            // Ao selecionar fornecedor, muda automaticamente para PJ
                            setFormData({...formData, tipo_cadastro: e.target.value, tipo_pessoa: 'PJ'});
                          }}
                          className="mr-2"
                        />
                        <span className="text-sm">Fornecedor</span>
                      </label>
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="veterinario"
                          checked={formData.tipo_cadastro === 'veterinario'}
                          onChange={(e) => setFormData({...formData, tipo_cadastro: e.target.value})}
                          className="mr-2"
                        />
                        <span className="text-sm">Veterinário</span>
                      </label>
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="funcionario"
                          checked={formData.tipo_cadastro === 'funcionario'}
                          onChange={(e) => setFormData({...formData, tipo_cadastro: e.target.value, tipo_pessoa: 'PF'})}
                          className="mr-2"
                        />
                        <span className="text-sm">Funcionário</span>
                      </label>
                    </div>
                  </div>

                  {/* 🚚 Seção de Entrega */}
                  {(formData.tipo_cadastro === 'funcionario' || formData.tipo_cadastro === 'fornecedor') && (
                    <div className="bg-blue-50 p-3 rounded border border-blue-200">
                      <div className="flex items-center gap-2 mb-1">
                        <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
                        </svg>
                        <label className="text-xs font-medium text-gray-700">É entregador</label>
                        <label className="relative inline-flex items-center cursor-pointer ml-auto">
                          <input
                            type="checkbox"
                            checked={formData.is_entregador || false}
                            onChange={(e) => setFormData({...formData, is_entregador: e.target.checked})}
                            className="sr-only peer"
                          />
                          <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                      </div>

                      {formData.is_entregador && (
                        <div className="ml-5 mt-2 space-y-2 border-l-2 border-blue-300 pl-3">
                          
                          {/* Entregador Padrão */}
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.entregador_padrao || false}
                              onChange={(e) => setFormData({...formData, entregador_padrao: e.target.checked})}
                              className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <span className="text-xs text-gray-700 font-medium">Entregador padrão</span>
                            <span className="text-[10px] text-gray-500">(pré-selecionado nas rotas)</span>
                          </label>

                          {/* CONTROLA RH - Só para funcionário */}
                          {formData.tipo_cadastro === 'funcionario' && (
                            <div className="space-y-2">
                              <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formData.controla_rh || false}
                                  onChange={(e) => {
                                    const controlaRH = e.target.checked;
                                    setFormData({
                                      ...formData, 
                                      controla_rh: controlaRH,
                                      // Se controla RH, limpa modelo de custo E força gera_conta_pagar = false
                                      modelo_custo_entrega: controlaRH ? '' : formData.modelo_custo_entrega,
                                      taxa_fixa_entrega: controlaRH ? '' : formData.taxa_fixa_entrega,
                                      valor_por_km_entrega: controlaRH ? '' : formData.valor_por_km_entrega,
                                      gera_conta_pagar_custo_entrega: false, // SEMPRE false se controla RH
                                    });
                                  }}
                                  className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                                />
                                <div>
                                  <span className="text-xs text-gray-700 font-medium">Controla RH</span>
                                  <p className="text-[10px] text-gray-500 mt-0.5">Custo rateado na folha (não gera contas a pagar)</p>
                                </div>
                              </label>

                              {/* MÉDIA DE ENTREGAS POR MÊS - Só aparece se controla RH */}
                              {formData.controla_rh && (
                                <div className="ml-5 pl-3 border-l-2 border-blue-300">
                                  <label className="block">
                                    <span className="text-xs text-gray-700 font-medium">Média de entregas por mês</span>
                                    <p className="text-[10px] text-gray-500 mt-0.5 mb-1">
                                      Define o rateio inicial do custo do funcionário por entrega. Será ajustado automaticamente no final do mês.
                                    </p>
                                    <input
                                      type="number"
                                      min="1"
                                      step="1"
                                      value={formData.media_entregas_configurada || ''}
                                      onChange={(e) => setFormData({...formData, media_entregas_configurada: e.target.value})}
                                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                      placeholder="Ex: 100 entregas/mês"
                                    />
                                    <p className="text-[10px] text-blue-600 mt-1">
                                      💡 Exemplo: Se o custo mensal é R$ 3.000 e média é 100 entregas, cada entrega custará R$ 30,00 inicialmente
                                    </p>
                                  </label>
                                </div>
                              )}

                              {/* GERAR CONTAS A PAGAR - Só aparece se NÃO controla RH */}
                              {!formData.controla_rh && (
                                <label className="flex items-start gap-2 cursor-pointer ml-5 pl-2 border-l border-gray-300">
                                  <input
                                    type="checkbox"
                                    checked={formData.gera_conta_pagar_custo_entrega || false}
                                    onChange={(e) => setFormData({...formData, gera_conta_pagar_custo_entrega: e.target.checked})}
                                    className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                                  />
                                  <div>
                                    <span className="text-xs text-gray-700 font-medium">Gerar contas a pagar por entrega</span>
                                    <p className="text-[10px] text-gray-500 mt-0.5">Marque se este funcionário recebe por KM ou taxa fixa a cada entrega</p>
                                  </div>
                                </label>
                              )}
                            </div>
                          )}

                          {/* MODELO DE CUSTO */}
                          {(formData.tipo_cadastro === 'fornecedor' || (formData.tipo_cadastro === 'funcionario' && !formData.controla_rh)) && (
                            <div className="space-y-2">
                              {/* Avisos condicionais */}
                              {formData.tipo_cadastro === 'fornecedor' && (
                                <div className="bg-yellow-50 border border-yellow-200 rounded p-1.5 text-[10px] text-yellow-800">
                                  ⚠️ <strong>Terceirizado</strong> - Sempre gera contas a pagar
                                </div>
                              )}
                              {formData.tipo_cadastro === 'funcionario' && !formData.controla_rh && (
                                <div className="bg-blue-50 border border-blue-200 rounded p-1.5 text-[10px] text-blue-800">
                                  ℹ️ <strong>Funcionário sem RH</strong> - {formData.gera_conta_pagar_custo_entrega ? 'Gera CP por entrega' : 'Não gera CP'}
                                </div>
                              )}

                              {/* Taxa Fixa */}
                              <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formData.modelo_custo_entrega === 'taxa_fixa'}
                                  onChange={(e) => setFormData({
                                    ...formData, 
                                    modelo_custo_entrega: e.target.checked ? 'taxa_fixa' : '',
                                    valor_por_km_entrega: '',
                                  })}
                                  className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                                />
                                <div className="flex-1">
                                  <span className="text-xs text-gray-700 font-medium">Taxa Fixa</span>
                                  {formData.modelo_custo_entrega === 'taxa_fixa' && (
                                    <input
                                      type="number"
                                      step="0.01"
                                      min="0"
                                      value={formData.taxa_fixa_entrega || ''}
                                      onChange={(e) => setFormData({...formData, taxa_fixa_entrega: e.target.value})}
                                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded mt-1 focus:ring-1 focus:ring-blue-500"
                                      placeholder="Ex: 15.00"
                                    />
                                  )}
                                </div>
                              </label>

                              {/* Valor por KM */}
                              <label className="flex items-start gap-2 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formData.modelo_custo_entrega === 'por_km'}
                                  onChange={(e) => setFormData({
                                    ...formData, 
                                    modelo_custo_entrega: e.target.checked ? 'por_km' : '',
                                    taxa_fixa_entrega: '',
                                  })}
                                  className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                                />
                                <div className="flex-1">
                                  <span className="text-xs text-gray-700 font-medium">Valor por KM</span>
                                  {formData.modelo_custo_entrega === 'por_km' && (
                                    <input
                                      type="number"
                                      step="0.01"
                                      min="0"
                                      value={formData.valor_por_km_entrega || ''}
                                      onChange={(e) => setFormData({...formData, valor_por_km_entrega: e.target.value})}
                                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded mt-1 focus:ring-1 focus:ring-blue-500"
                                      placeholder="Ex: 2.50"
                                    />
                                  )}
                                </div>
                              </label>
                            </div>
                          )}

                          {/* MOTO PRÓPRIA */}
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.moto_propria || false}
                              onChange={(e) => setFormData({...formData, moto_propria: e.target.checked})}
                              className="w-3.5 h-3.5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <span className="text-xs text-gray-700">{formData.moto_propria ? '✅ Moto própria' : '🏢 Moto da loja'}</span>
                          </label>

                          {/* 📆 Acerto Financeiro */}
                          <div className="mt-2 pt-2 border-t border-blue-200">
                            <h4 className="text-xs font-semibold text-gray-700 mb-2">📆 Acerto Financeiro</h4>
                            <div className="space-y-2">
                              <div>
                                <label className="block text-[10px] font-medium text-gray-600 mb-0.5">Periodicidade</label>
                                <select
                                  value={formData.tipo_acerto_entrega || ''}
                                  onChange={(e) => setFormData({
                                    ...formData,
                                    tipo_acerto_entrega: e.target.value,
                                    dia_semana_acerto: '',
                                    dia_mes_acerto: '',
                                  })}
                                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                >
                                  <option value="">Selecione</option>
                                  <option value="semanal">Semanal</option>
                                  <option value="quinzenal">Quinzenal (dias 1 e 15)</option>
                                  <option value="mensal">Mensal</option>
                                </select>
                              </div>

                              {formData.tipo_acerto_entrega === 'semanal' && (
                                <div>
                                  <label className="block text-[10px] font-medium text-gray-600 mb-0.5">Dia da semana</label>
                                  <select
                                    value={formData.dia_semana_acerto || ''}
                                    onChange={(e) => setFormData({...formData, dia_semana_acerto: e.target.value})}
                                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                  >
                                    <option value="">Selecione</option>
                                    <option value="1">Segunda</option>
                                    <option value="2">Terça</option>
                                    <option value="3">Quarta</option>
                                    <option value="4">Quinta</option>
                                    <option value="5">Sexta</option>
                                    <option value="6">Sábado</option>
                                    <option value="7">Domingo</option>
                                  </select>
                                </div>
                              )}

                              {formData.tipo_acerto_entrega === 'mensal' && (
                                <div>
                                  <label className="block text-[10px] font-medium text-gray-600 mb-0.5">Dia do mês (1 a 28)</label>
                                  <input
                                    type="number"
                                    min="1"
                                    max="28"
                                    value={formData.dia_mes_acerto || ''}
                                    onChange={(e) => setFormData({...formData, dia_mes_acerto: e.target.value})}
                                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                    placeholder="Ex: 5"
                                  />
                                </div>
                              )}

                              {formData.tipo_acerto_entrega === 'quinzenal' && (
                                <div className="bg-blue-50 p-1.5 rounded text-[10px] text-blue-700">
                                  ℹ️ Acerto nos dias <strong>1</strong> e <strong>15</strong>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 🤝 Toggle de Parceiro (Sistema de Comissões) */}
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-lg border border-green-200">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <FiDollarSign className="text-green-600" size={20} />
                        <label className="text-sm font-medium text-gray-700">
                          Ativar como parceiro (comissões)
                        </label>
                        
                        {/* 🟢 Badge indicador de parceiro ativo */}
                        {formData.parceiro_ativo && (
                          <div className="flex items-center gap-1.5 px-3 py-1 bg-green-600 text-white rounded-full text-xs font-semibold animate-fade-in">
                            <FiCheck size={14} className="font-bold" />
                            <span>Parceiro habilitado para comissão</span>
                          </div>
                        )}
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.parceiro_ativo}
                          onChange={(e) => setFormData({
                            ...formData, 
                            parceiro_ativo: e.target.checked,
                            parceiro_desde: e.target.checked && !formData.parceiro_desde ? new Date().toISOString().split('T')[0] : (formData.parceiro_desde || '')
                          })}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                      </label>
                    </div>
                    <p className="text-xs text-gray-500 ml-7">
                      Ao ativar, esta pessoa poderá receber comissões de vendas, independente do tipo de cadastro
                    </p>
                    {formData.parceiro_ativo && (
                      <div className="mt-3 ml-7">
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Observações do parceiro (opcional)
                        </label>
                        <textarea
                          value={formData.parceiro_observacoes}
                          onChange={(e) => setFormData({...formData, parceiro_observacoes: e.target.value})}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none"
                          placeholder="Ex: Especialista em produtos de higiene..."
                          rows="2"
                        />
                      </div>
                    )}
                  </div>

                  {/* Tipo de Pessoa */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {formData.tipo_pessoa === 'PJ' ? 'Tipo de pessoa jurídica *' : 'Tipo de pessoa *'}
                    </label>
                    <div className="flex gap-4">
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="PF"
                          checked={formData.tipo_pessoa === 'PF'}
                          onChange={(e) => setFormData({...formData, tipo_pessoa: e.target.value})}
                          className="mr-2"
                        />
                        <span className="text-sm">Pessoa Física</span>
                      </label>
                      <label className="flex items-center cursor-pointer">
                        <input
                          type="radio"
                          value="PJ"
                          checked={formData.tipo_pessoa === 'PJ'}
                          onChange={(e) => setFormData({...formData, tipo_pessoa: e.target.value})}
                          className="mr-2"
                        />
                        <span className="text-sm">Pessoa Jurídica</span>
                      </label>
                    </div>
                  </div>

                  {/* Campos Pessoa Física */}
                  {formData.tipo_pessoa === 'PF' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Nome completo *
                        </label>
                        <input
                          type="text"
                          value={formData.nome}
                          onChange={(e) => setFormData({...formData, nome: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="Digite o nome completo"
                          required
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          CPF
                        </label>
                        <input
                          type="text"
                          value={formData.cpf}
                          onChange={(e) => setFormData({...formData, cpf: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="000.000.000-00"
                          maxLength="14"
                        />
                      </div>

                      {/* Campo CRMV para Veterinários */}
                      {formData.tipo_cadastro === 'veterinario' && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            CRMV
                          </label>
                          <input
                            type="text"
                            value={formData.crmv}
                            onChange={(e) => setFormData({...formData, crmv: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                            placeholder="CRMV XX 1234"
                            maxLength="20"
                          />
                        </div>
                      )}
                    </>
                  )}

                  {/* Campos Pessoa Jurídica */}
                  {formData.tipo_pessoa === 'PJ' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Razão Social *
                        </label>
                        <input
                          type="text"
                          value={formData.razao_social}
                          onChange={(e) => setFormData({...formData, razao_social: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="Razão social da empresa"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Nome Fantasia *
                        </label>
                        <input
                          type="text"
                          value={formData.nome}
                          onChange={(e) => setFormData({...formData, nome: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="Nome fantasia da empresa"
                          required
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            CNPJ *
                          </label>
                          <input
                            type="text"
                            value={formData.cnpj}
                            onChange={(e) => setFormData({...formData, cnpj: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                            placeholder="00.000.000/0000-00"
                            maxLength="18"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Inscrição Estadual
                          </label>
                          <input
                            type="text"
                            value={formData.inscricao_estadual}
                            onChange={(e) => setFormData({...formData, inscricao_estadual: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                            placeholder="IE"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Responsável / Contato
                        </label>
                        <input
                          type="text"
                          value={formData.responsavel}
                          onChange={(e) => setFormData({...formData, responsavel: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="Nome do responsável ou contato"
                        />
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Step 2: Contatos */}
              {currentStep === 2 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Contatos</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Celular *
                    </label>
                    <input
                      type="text"
                      value={formData.celular}
                      onChange={(e) => setFormData({...formData, celular: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="(00) 00000-0000"
                    />
                  </div>

                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-700">Este número é WhatsApp?</span>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          checked={formData.celular_whatsapp === true}
                          onChange={() => setFormData({...formData, celular_whatsapp: true})}
                          className="text-blue-600"
                        />
                        <span className="text-sm">Sim</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          checked={formData.celular_whatsapp === false}
                          onChange={() => setFormData({...formData, celular_whatsapp: false})}
                          className="text-blue-600"
                        />
                        <span className="text-sm">Não</span>
                      </label>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Telefone fixo
                    </label>
                    <input
                      type="text"
                      value={formData.telefone}
                      onChange={(e) => setFormData({...formData, telefone: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="(00) 0000-0000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      E-mail
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="email@exemplo.com"
                    />
                  </div>
                </div>
              )}

              {/* Step 3: Endereço */}
              {currentStep === 3 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Endereço</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      CEP
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={formData.cep}
                        onChange={(e) => {
                          const cep = e.target.value;
                          setFormData({...formData, cep});
                          if (cep.replace(/\D/g, '').length === 8) {
                            buscarCep(cep);
                          }
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        placeholder="00000-000"
                        maxLength="9"
                      />
                      <button
                        type="button"
                        onClick={() => buscarCep(formData.cep)}
                        disabled={loadingCep}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
                      >
                        {loadingCep ? 'Buscando...' : 'Buscar'}
                      </button>
                    </div>
                    {cepError && (
                      <p className="text-xs text-red-500 mt-1">{cepError}</p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">Digite o CEP para preencher o endereço automaticamente</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Endereço
                    </label>
                    <input
                      type="text"
                      value={formData.endereco}
                      onChange={(e) => setFormData({...formData, endereco: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="Rua, Avenida..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Número
                      </label>
                      <input
                        type="text"
                        value={formData.numero}
                        onChange={(e) => setFormData({...formData, numero: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        placeholder="123"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Complemento
                      </label>
                      <input
                        type="text"
                        value={formData.complemento}
                        onChange={(e) => setFormData({...formData, complemento: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        placeholder="Apto, Bloco..."
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bairro
                    </label>
                    <input
                      type="text"
                      value={formData.bairro}
                      onChange={(e) => setFormData({...formData, bairro: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Cidade
                      </label>
                      <input
                        type="text"
                        value={formData.cidade}
                        onChange={(e) => setFormData({...formData, cidade: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Estado
                      </label>
                      <input
                        type="text"
                        value={formData.estado}
                        onChange={(e) => setFormData({...formData, estado: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        maxLength="2"
                        placeholder="SP"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Step 4: Informações Complementares */}
              {currentStep === 4 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Informações complementares</h3>
                  
                  {/* Endereços Adicionais */}
                  <div className="border-b pb-4 mb-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="text-md font-semibold text-gray-800">Endereços Adicionais</h4>
                        <p className="text-sm text-gray-600">
                          Cadastre múltiplos endereços para entrega, cobrança, etc.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => abrirModalEndereco()}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Adicionar Endereço
                      </button>
                    </div>

                    {/* Cards minimizados dos endereços */}
                    {enderecosAdicionais.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                        {/* ✅ key={index} é aceitável aqui: lista não reordena e não há ID único do backend */}
                        {enderecosAdicionais.map((endereco, index) => (
                          <div 
                            key={index}
                            className="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                                    endereco.tipo === 'entrega' ? 'bg-blue-100 text-blue-800' :
                                    endereco.tipo === 'cobranca' ? 'bg-green-100 text-green-800' :
                                    endereco.tipo === 'comercial' ? 'bg-purple-100 text-purple-800' :
                                    endereco.tipo === 'residencial' ? 'bg-orange-100 text-orange-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {endereco.tipo === 'entrega' ? '📦 Entrega' :
                                     endereco.tipo === 'cobranca' ? '💰 Cobrança' :
                                     endereco.tipo === 'comercial' ? '🏢 Comercial' :
                                     endereco.tipo === 'residencial' ? '🏠 Residencial' :
                                     '📍 Trabalho'}
                                  </span>
                                  <span className="text-xs font-medium text-gray-500">
                                    +{index + 1}
                                  </span>
                                </div>
                                {endereco.apelido && (
                                  <p className="text-sm font-semibold text-gray-900 mb-1">
                                    {endereco.apelido}
                                  </p>
                                )}
                                <p className="text-sm text-gray-700">
                                  {endereco.endereco}, {endereco.numero}
                                  {endereco.complemento && ` - ${endereco.complemento}`}
                                </p>
                                <p className="text-xs text-gray-600 mt-1">
                                  {endereco.bairro}, {endereco.cidade}/{endereco.estado}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">
                                  CEP: {endereco.cep}
                                </p>
                              </div>
                              <div className="flex gap-1 ml-2">
                                <button
                                  type="button"
                                  onClick={() => abrirModalEndereco(index)}
                                  className="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                  title="Editar"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                  </svg>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => removerEndereco(index)}
                                  className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                                  title="Excluir"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500 text-sm">
                        <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Nenhum endereço adicional cadastrado
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Marcações / Tags
                    </label>
                    <input
                      type="text"
                      value={formData.tags}
                      onChange={(e) => setFormData({...formData, tags: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="Ex: Bom pagador, Cliente fiel, VIP"
                    />
                    <p className="text-xs text-gray-500 mt-1">Separe por vírgula para múltiplas tags</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Observações
                    </label>
                    <textarea
                      value={formData.observacoes}
                      onChange={(e) => setFormData({...formData, observacoes: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      rows="4"
                      placeholder="Informações adicionais sobre o cliente..."
                    />
                  </div>
                </div>
              )}

              {/* Step 5: Animais - SIMPLIFICADO */}
              {currentStep === 5 && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                        <PawPrint className="text-blue-600" size={24} />
                        Pets do Cliente
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">
                        Use o módulo dedicado para gerenciar pets com informações completas
                      </p>
                    </div>
                  </div>

                  {/* Aviso importante */}
                  <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-5">
                    <div className="flex items-start gap-3">
                      <PawPrint className="text-blue-600 flex-shrink-0 mt-1" size={24} />
                      <div>
                        <h4 className="font-semibold text-blue-900 mb-2">
                          🎯 Gestão Profissional de Pets
                        </h4>
                        <p className="text-sm text-blue-800 mb-3">
                          Agora os pets possuem um <strong>módulo dedicado</strong> com funcionalidades completas:
                          histórico médico, vacinas, consultas, serviços e muito mais.
                        </p>
                        <ul className="text-sm text-blue-800 space-y-1 mb-4">
                          <li>✅ Cadastro completo com campos veterinários</li>
                          <li>✅ Histórico de saúde e medicações</li>
                          <li>✅ Controle de vacinas e consultas</li>
                          <li>✅ Timeline de eventos</li>
                          <li>✅ Preparado para uso clínico real</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* Lista simples de pets (se houver) */}
                  {pets.length > 0 && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-3">
                        Pets cadastrados ({pets.length})
                      </h4>
                      <div className="space-y-2">
                        {pets.map((pet) => (
                          <div 
                            key={pet.id || pet.nome} 
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                          >
                            <div className="flex items-center gap-3">
                              <PawPrint className="text-blue-600" size={20} />
                              <div>
                                <p className="font-medium text-gray-900">{pet.nome}</p>
                                <p className="text-sm text-gray-600">
                                  {pet.especie} {pet.raca && `• ${pet.raca}`}
                                </p>
                              </div>
                            </div>
                            {pet.id && (
                              <button
                                onClick={() => navigate(`/pets/${pet.id}`)}
                                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors"
                              >
                                Ver Detalhes
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Botões de ação */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button
                      type="button"
                      onClick={() => {
                        if (editingCliente?.id) {
                          navigate(`/pets?cliente_id=${editingCliente.id}`);
                        } else {
                          alert('⚠️ Salve o cliente primeiro para gerenciar pets');
                        }
                      }}
                      className="flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all font-semibold shadow-md"
                    >
                      <PawPrint size={24} />
                      <div className="text-left">
                        <div>🐾 Gerenciar Pets</div>
                        <div className="text-xs font-normal opacity-90">
                          Módulo completo de gestão
                        </div>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        if (editingCliente?.id) {
                          navigate('/pets/novo', { state: { clienteId: editingCliente.id } });
                        } else {
                          alert('⚠️ Salve o cliente primeiro para adicionar pets');
                        }
                      }}
                      className="flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-lg transition-all font-semibold shadow-md"
                    >
                      <FiPlus size={24} />
                      <div className="text-left">
                        <div>➕ Adicionar Pet</div>
                        <div className="text-xs font-normal opacity-90">
                          Cadastro completo
                        </div>
                      </div>
                    </button>
                  </div>

                  {/* Mensagem informativa */}
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-yellow-800">
                      💡 <strong>Dica:</strong> Pets podem ser adicionados agora ou depois. 
                      Todas as informações médicas e histórico ficam no módulo dedicado de pets.
                    </p>
                  </div>

                  {!editingCliente && (
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      <p className="text-sm text-orange-800">
                        ⚠️ <strong>Atenção:</strong> Salve o cliente primeiro (etapa 6) para poder gerenciar seus pets.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Step 6: Financeiro */}
              {currentStep === 6 && (
                <div className="space-y-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <FiDollarSign className="text-green-600" />
                    Informações Financeiras
                  </h3>

                  {/* Card de Saldo de Crédito */}
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-green-800 mb-1">💰 Saldo de Crédito</p>
                        <p className="text-3xl font-bold text-green-600">
                          R$ {editingCliente?.credito 
                            ? parseFloat(editingCliente.credito).toFixed(2).replace('.', ',') 
                            : '0,00'}
                        </p>
                        <p className="text-xs text-green-700 mt-1">
                          Disponível para uso em compras
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50"
                          disabled={!editingCliente}
                          onClick={async () => {
                            if (!editingCliente) {
                              alert('Salve o cliente primeiro antes de adicionar crédito');
                              return;
                            }
                            
                            const valor = prompt('Digite o valor a adicionar ao crédito:');
                            if (!valor || isNaN(parseFloat(valor))) return;
                            
                            const valorNum = parseFloat(valor);
                            if (valorNum <= 0) {
                              alert('Valor deve ser maior que zero');
                              return;
                            }
                            
                            const motivo = prompt('Motivo da adição de crédito:', 'Ajuste manual');
                            if (!motivo) return;
                            
                            try {
                              const response = await api.post(`/clientes/${editingCliente.id}/credito/adicionar`, {
                                valor: valorNum,
                                motivo: motivo
                              });
                              
                              alert(`✅ ${response.data.message}\n\nCrédito anterior: R$ ${response.data.credito_anterior.toFixed(2)}\nValor adicionado: R$ ${response.data.valor_adicionado.toFixed(2)}\nNovo saldo: R$ ${response.data.credito_atual.toFixed(2)}`);
                              
                              // Atualizar crédito no estado local
                              setEditingCliente({
                                ...editingCliente,
                                credito: response.data.credito_atual
                              });
                              
                              // Recarregar lista de clientes
                              loadClientes();
                            } catch (error) {
                              console.error('Erro ao adicionar crédito:', error);
                              alert('❌ Erro ao adicionar crédito: ' + (error.response?.data?.detail || error.message));
                            }
                          }}
                        >
                          <FiTrendingUp /> Adicionar Crédito
                        </button>
                        <button
                          type="button"
                          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50"
                          disabled={!editingCliente}
                          onClick={async () => {
                            if (!editingCliente) {
                              alert('Salve o cliente primeiro antes de remover crédito');
                              return;
                            }
                            
                            const creditoAtual = parseFloat(editingCliente.credito || 0);
                            if (creditoAtual <= 0) {
                              alert('Cliente não possui crédito para remover');
                              return;
                            }
                            
                            const valor = prompt(`Digite o valor a remover (máx: R$ ${creditoAtual.toFixed(2)}):`);
                            if (!valor || isNaN(parseFloat(valor))) return;
                            
                            const valorNum = parseFloat(valor);
                            if (valorNum <= 0) {
                              alert('Valor deve ser maior que zero');
                              return;
                            }
                            
                            if (valorNum > creditoAtual) {
                              alert(`Valor excede o crédito disponível (R$ ${creditoAtual.toFixed(2)})`);
                              return;
                            }
                            
                            const motivo = prompt('Motivo da remoção de crédito:', 'Ajuste manual');
                            if (!motivo) return;
                            
                            try {
                              const response = await api.post(`/clientes/${editingCliente.id}/credito/remover`, {
                                valor: valorNum,
                                motivo: motivo
                              });
                              
                              alert(`✅ ${response.data.message}\n\nCrédito anterior: R$ ${response.data.credito_anterior.toFixed(2)}\nValor removido: R$ ${response.data.valor_removido.toFixed(2)}\nNovo saldo: R$ ${response.data.credito_atual.toFixed(2)}`);
                              
                              // Atualizar crédito no estado local
                              setEditingCliente({
                                ...editingCliente,
                                credito: response.data.credito_atual
                              });
                              
                              // Recarregar lista de clientes
                              loadClientes();
                            } catch (error) {
                              console.error('Erro ao remover crédito:', error);
                              alert('❌ Erro ao remover crédito: ' + (error.response?.data?.detail || error.message));
                            }
                          }}
                        >
                          <FiTrendingDown /> Remover Crédito
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Resumo Financeiro Compacto - Nova abordagem leve */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                    <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center gap-2">
                      <FiCreditCard />
                      Resumo Financeiro (Últimos 90 dias)
                    </h4>
                    
                    {editingCliente ? (
                      <div className="space-y-4">
                        {loadingResumo ? (
                          <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto"></div>
                            <p className="mt-2 text-gray-600 text-sm">Carregando resumo...</p>
                          </div>
                        ) : (
                          <>
                            {resumoFinanceiro ? (
                              <>
                                {/* Grid de Métricas */}
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                  {/* Total Vendas */}
                                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                                    <p className="text-xs text-gray-600 mb-1">💰 Total Comprado</p>
                                    <p className="text-2xl font-bold text-blue-600">
                                      R$ {resumoFinanceiro.total_vendas?.toFixed(2).replace('.', ',') || '0,00'}
                                    </p>
                                    <p className="text-xs text-gray-500 mt-1">
                                      {resumoFinanceiro.quantidade_vendas || 0} vendas
                                    </p>
                                  </div>

                                  {/* Total em Aberto */}
                                  <div className={`rounded-lg p-4 border ${
                                    resumoFinanceiro.tem_debitos_vencidos 
                                      ? 'bg-red-50 border-red-300' 
                                      : resumoFinanceiro.tem_debitos 
                                        ? 'bg-orange-50 border-orange-200'
                                        : 'bg-green-50 border-green-200'
                                  }`}>
                                    <p className="text-xs text-gray-600 mb-1">
                                      {resumoFinanceiro.tem_debitos_vencidos ? '⚠️' : '📋'} Em Aberto
                                    </p>
                                    <p className={`text-2xl font-bold ${
                                      resumoFinanceiro.tem_debitos_vencidos 
                                        ? 'text-red-600'
                                        : resumoFinanceiro.tem_debitos 
                                          ? 'text-orange-600'
                                          : 'text-green-600'
                                    }`}>
                                      R$ {resumoFinanceiro.total_em_aberto?.toFixed(2).replace('.', ',') || '0,00'}
                                    </p>
                                    {resumoFinanceiro.tem_debitos_vencidos && (
                                      <p className="text-xs text-red-600 font-semibold mt-1">
                                        R$ {resumoFinanceiro.total_vencido?.toFixed(2).replace('.', ',') || '0,00'} vencido
                                      </p>
                                    )}
                                  </div>

                                  {/* Ticket Médio */}
                                  <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                                    <p className="text-xs text-gray-600 mb-1">📊 Ticket Médio</p>
                                    <p className="text-2xl font-bold text-purple-600">
                                      R$ {resumoFinanceiro.ticket_medio?.toFixed(2).replace('.', ',') || '0,00'}
                                    </p>
                                    <p className="text-xs text-gray-500 mt-1">
                                      por compra
                                    </p>
                                  </div>

                                  {/* Última Compra */}
                                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                    <p className="text-xs text-gray-600 mb-1">🕐 Última Compra</p>
                                    {resumoFinanceiro.ultima_compra ? (
                                      <>
                                        <p className="text-2xl font-bold text-gray-700">
                                          R$ {resumoFinanceiro.ultima_compra.valor?.toFixed(2).replace('.', ',') || '0,00'}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">
                                          {new Date(resumoFinanceiro.ultima_compra.data).toLocaleDateString('pt-BR')}
                                          {' '}(há {resumoFinanceiro.ultima_compra.dias_atras} dias)
                                        </p>
                                      </>
                                    ) : (
                                      <p className="text-sm text-gray-500 mt-2">Nenhuma compra</p>
                                    )}
                                  </div>
                                </div>
                              </>
                            ) : (
                              <div className="text-center py-6 text-gray-500">
                                <p className="mb-2">📋 Nenhuma informação financeira</p>
                                <p className="text-sm">Dados aparecerão após a primeira venda</p>
                              </div>
                            )}

                            {/* Botão Ver Histórico Completo - SEMPRE VISÍVEL */}
                            <button
                              type="button"
                              onClick={() => navigate(`/clientes/${editingCliente.id}/financeiro`)}
                              className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg transition-all flex items-center justify-center gap-2 font-semibold shadow-md"
                            >
                              <FiCreditCard />
                              📊 Ver Histórico Financeiro Completo
                              {resumoFinanceiro && (
                                <span className="text-xs bg-white bg-opacity-20 px-2 py-1 rounded">
                                  {resumoFinanceiro.total_transacoes_historico || 0} transações
                                </span>
                              )}
                            </button>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                        <p className="text-blue-800 text-sm">
                          ℹ️ Salve o cliente primeiro para visualizar o resumo financeiro
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-yellow-800">
                      💡 <strong>Dica:</strong> O crédito pode ser gerado automaticamente nas devoluções de produtos 
                      e utilizado como forma de pagamento no PDV.
                    </p>
                  </div>

                  {/* Card de Segmentação */}
                  {editingCliente && (
                    <ClienteSegmentos clienteId={editingCliente.id} />
                  )}

                  {/* Card de Insights Operacionais */}
                  {editingCliente && (
                    <ClienteInsights 
                      clienteId={editingCliente.id}
                      cliente={editingCliente}
                      metricas={resumoFinanceiro}
                    />
                  )}

                  {/* Bloco WhatsApp */}
                  {editingCliente && editingCliente.celular && (
                    <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 shadow-sm">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <FiMessageCircle className="text-green-600" size={24} />
                          <h3 className="text-lg font-semibold text-gray-900">💬 WhatsApp</h3>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const celular = editingCliente.celular.replace(/\D/g, '');
                            window.open(`https://wa.me/55${celular}`, '_blank');
                          }}
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium"
                        >
                          <FiMessageCircle />
                          Abrir conversa
                        </button>
                      </div>
                      
                      <WhatsAppHistorico clienteId={editingCliente.id} />
                    </div>
                  )}

                  {/* Timeline Recente do Cliente/Fornecedor */}
                  {editingCliente && (
                    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                      <ClienteTimeline 
                        clienteId={editingCliente.tipo_cadastro === 'cliente' ? editingCliente.id : null}
                        fornecedorId={editingCliente.tipo_cadastro === 'fornecedor' ? editingCliente.id : null}
                        tipo={editingCliente.tipo_cadastro === 'fornecedor' ? 'fornecedor' : 'cliente'}
                        limit={5}
                        showHeader={true}
                        onVerMais={() => navigate(`/clientes/${editingCliente.id}/timeline`)}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer Navigation */}
            <div className="border-t border-gray-200 p-4 bg-gray-50 flex justify-between">
              <button
                onClick={prevStep}
                disabled={currentStep === 1}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FiArrowLeft /> Voltar
              </button>

              {currentStep < 6 ? (
                <button
                  onClick={nextStep}
                  className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Avançar <FiArrowRight />
                </button>
              ) : (
                <button
                  onClick={handleSubmitFinal}
                  className="flex items-center gap-2 px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                >
                  <FiSave /> Salvar Cliente
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal de Endereço Adicional */}
      {mostrarFormEndereco && enderecoAtual && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            {/* Header do Modal */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
              <h3 className="text-xl font-bold text-gray-900">
                {enderecoAtual.index !== undefined ? 'Editar Endereço' : 'Adicionar Novo Endereço'}
              </h3>
              <button
                onClick={fecharModalEndereco}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Conteúdo do Modal */}
            <div className="p-6 space-y-4">
              {/* Tipo e Apelido */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Endereço *
                  </label>
                  <select
                    value={enderecoAtual.tipo}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, tipo: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  >
                    <option value="entrega">📦 Entrega</option>
                    <option value="cobranca">💰 Cobrança</option>
                    <option value="comercial">🏢 Comercial</option>
                    <option value="residencial">🏠 Residencial</option>
                    <option value="trabalho">📍 Trabalho</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Apelido (opcional)
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.apelido}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, apelido: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Ex: Casa da mãe, Escritório, Loja"
                  />
                </div>
              </div>

              {/* CEP */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CEP *
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={enderecoAtual.cep}
                      onChange={(e) => {
                        const value = e.target.value.replace(/\D/g, '');
                        const formatted = value.length > 5 ? `${value.slice(0, 5)}-${value.slice(5, 8)}` : value;
                        setEnderecoAtual({...enderecoAtual, cep: formatted});
                      }}
                      onBlur={(e) => buscarCepModal(e.target.value)}
                      maxLength="9"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="00000-000"
                    />
                    {loadingCep && (
                      <div className="absolute right-2 top-2">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Endereço e Número */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Endereço *
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.endereco}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, endereco: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Rua, Avenida, etc."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.numero}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, numero: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="123"
                  />
                </div>
              </div>

              {/* Complemento e Bairro */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Complemento
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.complemento}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, complemento: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Apto, Bloco, Sala..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Bairro
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.bairro}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, bairro: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="Centro, Jardim..."
                  />
                </div>
              </div>

              {/* Cidade e Estado */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cidade *
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.cidade}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, cidade: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    placeholder="São Paulo"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estado
                  </label>
                  <input
                    type="text"
                    value={enderecoAtual.estado}
                    onChange={(e) => setEnderecoAtual({...enderecoAtual, estado: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    maxLength="2"
                    placeholder="SP"
                  />
                </div>
              </div>

              <p className="text-xs text-gray-500">* Campos obrigatórios</p>
            </div>

            {/* Footer do Modal */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={fecharModalEndereco}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={salvarEndereco}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Salvar Endereço
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Importação */}
      <ModalImportacaoPessoas
        isOpen={showModalImportacao}
        onClose={() => {
          setShowModalImportacao(false);
          fetchClientes();
        }}
      />
      
      {/* Estilos para animação do badge de parceiro */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        
        .animate-fade-in {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default Pessoas;
