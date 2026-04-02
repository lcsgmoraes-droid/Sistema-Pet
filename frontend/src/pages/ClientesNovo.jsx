import { PawPrint } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import {
  FiAlertCircle,
  FiArrowLeft,
  FiArrowRight,
  FiCheck,
  FiDollarSign,
  FiEdit2,
  FiMessageCircle,
  FiPlus,
  FiSave,
  FiSearch,
  FiTrash2,
  FiUploadCloud,
  FiUser,
  FiX,
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ClienteSegmentoBadgeWrapper from "../components/ClienteSegmentoBadgeWrapper";
import ClientesNovoCadastroStep from "../components/clientes/ClientesNovoCadastroStep";
import ClientesNovoContatosStep from "../components/clientes/ClientesNovoContatosStep";
import ClientesNovoDuplicadoWarning from "../components/clientes/ClientesNovoDuplicadoWarning";
import ClientesNovoEnderecoModal from "../components/clientes/ClientesNovoEnderecoModal";
import ClientesNovoFinanceiroStep from "../components/clientes/ClientesNovoFinanceiroStep";
import ClientesNovoPetsStep from "../components/clientes/ClientesNovoPetsStep";
import ModalAdicionarCredito from "../components/ModalAdicionarCredito";
import ModalImportacaoPessoas from "../components/ModalImportacaoPessoas";
import ModalRemoverCredito from "../components/ModalRemoverCredito";
import { useClientesNovoEnderecos } from "../hooks/useClientesNovoEnderecos";
import { useClientesNovoListagem } from "../hooks/useClientesNovoListagem";
import { debugLog } from "../utils/debug";

const Pessoas = () => {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [showModalImportacao, setShowModalImportacao] = useState(false);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] =
    useState(false);
  const [mostrarModalRemoverCredito, setMostrarModalRemoverCredito] =
    useState(false);
  const [refreshKeyCredito, setRefreshKeyCredito] = useState(0);
  const [editingCliente, setEditingCliente] = useState(null);
  const [error, setError] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState("todos"); // Filtro por tipo: todos, cliente, fornecedor, veterinario, funcionario

  // Estados de paginação
  const [loadingCep, setLoadingCep] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [pets, setPets] = useState([]);
  const [editingPetIndex, setEditingPetIndex] = useState(null);
  const [cepError, setCepError] = useState("");
  const [clienteDuplicado, setClienteDuplicado] = useState(null);
  const [showDuplicadoWarning, setShowDuplicadoWarning] = useState(false);
  const [showConfirmacaoRemocao, setShowConfirmacaoRemocao] = useState(false);
  const [racas, setRacas] = useState([]);
  const [expandedPets, setExpandedPets] = useState({});
  const [highlightedPetId, setHighlightedPetId] = useState(null);
  const [petIdToEdit, setPetIdToEdit] = useState(null);
  const [resumoFinanceiro, setResumoFinanceiro] = useState(null);
  const [loadingResumo, setLoadingResumo] = useState(false);
  const [saldoCampanhas, setSaldoCampanhas] = useState(null);
  const [lancandoCarimbo, setLancandoCarimbo] = useState(false);
  const {
    clientes,
    loading,
    carregamentoInicialConcluido,
    searchTerm,
    setSearchTerm,
    paginaAtual,
    setPaginaAtual,
    totalRegistros,
    registrosPorPagina,
    setRegistrosPorPagina,
    filteredClientes,
    loadClientes,
    getClientePorCodigoExato,
  } = useClientesNovoListagem({ tipoFiltro, setError });

  // Form states
  const [formData, setFormData] = useState({
    tipo_cadastro: "cliente", // cliente, fornecedor, veterinario
    tipo_pessoa: "PF", // PF ou PJ
    nome: "",
    data_nascimento: "",
    cpf: "",
    email: "",
    telefone: "",
    celular: "",
    celular_whatsapp: true,
    // Campos PJ
    cnpj: "",
    inscricao_estadual: "",
    razao_social: "",
    nome_fantasia: "",
    responsavel: "",
    // Campo veterinário
    crmv: "",
    // Sistema de parceiros (comissões)
    parceiro_ativo: false,
    parceiro_desde: "",
    parceiro_observacoes: "",
    // Endereço
    cep: "",
    endereco: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    estado: "",
    // Endereços de entrega
    endereco_entrega: "",
    endereco_entrega_2: "",
    // Campos de entrega (Sprint 1 - Bloco 4)
    is_entregador: false,
    entregador_ativo: true,
    entregador_padrao: false,
    tipo_vinculo_entrega: "",
    // Funcionário com controla RH
    controla_rh: false,
    gera_conta_pagar_custo_entrega: false,
    media_entregas_configurada: "",
    custo_rh_ajustado: "",
    // Terceirizado/Eventual
    modelo_custo_entrega: "",
    taxa_fixa_entrega: "",
    valor_por_km_entrega: "",
    // Moto
    moto_propria: true,
    // 📆 Acerto financeiro (ETAPA 4)
    tipo_acerto_entrega: "",
    dia_semana_acerto: "",
    dia_mes_acerto: "",
    // Legado (manter compatibilidade)
    is_terceirizado: false,
    recebe_repasse: false,
    gera_conta_pagar: false,
    observacoes: "",
    tags: "",
  });

  // Estado para endereços adicionais
  const {
    enderecosAdicionais,
    setEnderecosAdicionais,
    enderecoAtual,
    setEnderecoAtual,
    mostrarFormEndereco,
    loadingCepEndereco,
    abrirModalEndereco,
    fecharModalEndereco,
    buscarCepModal,
    salvarEndereco,
    removerEndereco,
  } = useClientesNovoEnderecos();

  const [currentPet, setCurrentPet] = useState({
    nome: "",
    especie: "",
    raca: "",
    sexo: "",
    data_nascimento: "",
    cor: "",
    peso: "",
    observacoes: "",
    castrado: false,
    porte: "",
    microchip: "",
    alergias: "",
    doencas_cronicas: "",
    medicamentos_continuos: "",
    historico_clinico: "",
    foto_url: "",
    idade_aproximada: "",
  });

  const steps = [
    { number: 1, title: "Informações do cliente" },
    { number: 2, title: "Contatos" },
    { number: 3, title: "Endereço" },
    { number: 4, title: "Informações complementares" },
    { number: 5, title: "Animais" },
    { number: 6, title: "Financeiro" },
  ];

  // Debounce para busca (aguarda 500ms após usuário parar de digitar)
  useEffect(() => {
    const timer = setTimeout(() => {
      // Resetar para página 1 ao buscar
      if (paginaAtual !== 1) {
        setPaginaAtual(1);
      } else {
        loadClientes();
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [searchTerm]);

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
      const petIndex = pets.findIndex((p) => p.id === petIdToEdit);
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
      console.error("Erro ao carregar raças:", err);
      setRacas([]);
    }
  };

  const buscarCep = async (cep) => {
    const cepLimpo = cep.replace(/\D/g, "");

    if (cepLimpo.length !== 8) return;

    setLoadingCep(true);
    setCepError("");
    setError("");
    try {
      const response = await fetch(
        `https://viacep.com.br/ws/${cepLimpo}/json/`,
      );
      const data = await response.json();

      if (data.erro) {
        setCepError("CEP não encontrado");
        return;
      }

      setFormData((prev) => ({
        ...prev,
        endereco: data.logradouro || "",
        bairro: data.bairro || "",
        cidade: data.localidade || "",
        estado: data.uf || "",
        cep: cep,
      }));
    } catch (err) {
      console.error("Erro ao buscar CEP:", err);
    } finally {
      setLoadingCep(false);
    }
  };

  // Funções de gerenciamento de endereços adicionais

  const handleSubmitFinal = async () => {
    setError("");

    try {
      // ✅ VALIDAÇÕES DE CAMPOS OBRIGATÓRIOS
      const errosValidacao = [];

      // Nome é obrigatório para todos
      if (!formData.nome || formData.nome.trim() === "") {
        errosValidacao.push("Nome");
      }

      // Validações específicas para Pessoa Jurídica
      if (formData.tipo_pessoa === "PJ") {
        if (!formData.cnpj || formData.cnpj.trim() === "") {
          errosValidacao.push("CNPJ");
        }
        if (!formData.razao_social || formData.razao_social.trim() === "") {
          errosValidacao.push("Razão Social");
        }
      }

      // Validações específicas para Pessoa Física
      if (formData.tipo_pessoa === "PF") {
        if (
          formData.tipo_cadastro === "cliente" &&
          (!formData.cpf || formData.cpf.trim() === "")
        ) {
          // CPF opcional para clientes PF (muitos não têm)
          // Removido pois é opcional
        }
      }

      // Se houver erros de validação, mostrar e parar
      if (errosValidacao.length > 0) {
        const mensagem =
          "❌ Faltam os seguintes campos obrigatórios:\n\n" +
          errosValidacao.map((campo) => `• ${campo}`).join("\n");
        alert(mensagem);
        setError(mensagem);
        return;
      }

      // ✅ VALIDAÇÕES DE ENTREGADOR (ETAPA 4)
      if (formData.is_entregador) {
        // Validar tipo de acerto
        if (!formData.tipo_acerto_entrega) {
          alert(
            "Informe o tipo de acerto do entregador (semanal, quinzenal ou mensal)",
          );
          return;
        }

        // Validar dia da semana para acerto semanal
        if (
          formData.tipo_acerto_entrega === "semanal" &&
          !formData.dia_semana_acerto
        ) {
          alert("Informe o dia da semana para o acerto semanal");
          return;
        }

        // Validar dia do mês para acerto mensal
        if (
          formData.tipo_acerto_entrega === "mensal" &&
          !formData.dia_mes_acerto
        ) {
          alert("Informe o dia do mês para o acerto mensal");
          return;
        }

        // Validar range do dia do mês (1-28)
        if (formData.tipo_acerto_entrega === "mensal") {
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
        if (clienteData.tipo_cadastro === "funcionario") {
          clienteData.tipo_vinculo_entrega = "funcionario";
          clienteData.is_terceirizado = false;
        }
        // Se é fornecedor → is_terceirizado = true e tipo_vinculo = "terceirizado" automaticamente
        else if (clienteData.tipo_cadastro === "fornecedor") {
          clienteData.is_terceirizado = true;
          clienteData.tipo_vinculo_entrega = "terceirizado";
        }
      }

      // Adicionar endereços adicionais aos dados do cliente
      clienteData.enderecos_adicionais =
        enderecosAdicionais.length > 0 ? enderecosAdicionais : null;

      // Remover campos vazios (transformar "" em null)
      Object.keys(clienteData).forEach((key) => {
        if (clienteData[key] === "") {
          clienteData[key] = null;
        }
      });

      // Garantir que tipo_cadastro nunca seja 'todos'
      if (clienteData.tipo_cadastro === "todos") {
        clienteData.tipo_cadastro = "cliente";
      }

      // 🐛 DEBUG: Verificar entregador_padrao
      // debugLog('🐛 entregador_padrao antes do envio:', clienteData.entregador_padrao);
      // debugLog('🐛 is_entregador:', clienteData.is_entregador);

      // debugLog('Dados enviados:', clienteData);

      let clienteId;

      if (editingCliente) {
        // Atualizar cliente existente
        await api.put(`/clientes/${editingCliente.id}`, clienteData);
        clienteId = editingCliente.id;
      } else {
        // Criar novo cliente
        const clienteResponse = await api.post("/clientes/", clienteData);
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
        Object.keys(petData).forEach((key) => {
          if (petData[key] === "") {
            petData[key] = null;
          }
        });

        // Converter peso para float se houver valor
        if (petData.peso !== null && petData.peso !== undefined) {
          petData.peso = parseFloat(petData.peso) || null;
        }

        if (petId) {
          // Atualizar pet existente
          debugLog(`Atualizando pet ${petId}:`, petData);
          await api.put(`/clientes/pets/${petId}`, petData);
        } else {
          // Criar novo pet
          debugLog("Criando novo pet:", petData);
          await api.post(`/clientes/${clienteId}/pets`, petData);
        }
      }

      loadClientes();
      closeModal();
    } catch (err) {
      const errorDetails = err.response?.data?.details;
      console.error("Erro completo:", err.response?.data);
      console.error("Detalhes de validação:", errorDetails);

      // 🔍 Mapeamento de campos técnicos para nomes amigáveis
      const camposPtBr = {
        nome: "Nome",
        data_nascimento: "Data de Nascimento",
        cpf: "CPF",
        cnpj: "CNPJ",
        razao_social: "Razão Social",
        nome_fantasia: "Nome Fantasia",
        inscricao_estadual: "Inscrição Estadual",
        responsavel: "Responsável",
        telefone: "Telefone",
        celular: "Celular",
        email: "E-mail",
        cep: "CEP",
        endereco: "Endereço",
        numero: "Número",
        bairro: "Bairro",
        cidade: "Cidade",
        estado: "Estado",
        tipo_pessoa: "Tipo de Pessoa",
        tipo_cadastro: "Tipo de Cadastro",
        crmv: "CRMV",
        tipo_acerto_entrega: "Tipo de Acerto",
        dia_semana_acerto: "Dia da Semana para Acerto",
        dia_mes_acerto: "Dia do Mês para Acerto",
        tipo_vinculo_entrega: "Tipo de Vínculo",
      };

      // ✅ Processar erros de validação do backend
      let mensagemErro = "";

      if (errorDetails && Array.isArray(errorDetails)) {
        const camposFaltando = [];

        errorDetails.forEach((detail) => {
          // Extrair nome do campo (último elemento do array loc)
          const campo = detail.loc[detail.loc.length - 1];
          const nomeCampo = camposPtBr[campo] || campo;

          // Identificar o tipo de erro
          if (
            detail.type === "missing" ||
            detail.type === "value_error.missing"
          ) {
            camposFaltando.push(nomeCampo);
          } else if (detail.msg) {
            camposFaltando.push(`${nomeCampo}: ${detail.msg}`);
          }

          console.error(
            `Campo: ${nomeCampo} | Tipo: ${detail.type} | Mensagem: ${detail.msg}`,
          );
        });

        if (camposFaltando.length > 0) {
          mensagemErro =
            "❌ Faltam os seguintes campos obrigatórios:\n\n" +
            camposFaltando.map((campo) => `• ${campo}`).join("\n");
        }
      }

      // Usar a mensagem personalizada ou a genérica
      const errorMessage =
        mensagemErro || err.response?.data?.message || "Erro ao salvar cliente";
      setError(errorMessage);

      // Mostrar alert para maior visibilidade
      if (mensagemErro) {
        alert(mensagemErro);
      }
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Tem certeza que deseja excluir este cliente?")) return;

    try {
      debugLog("Excluindo cliente ID:", id);
      const response = await api.delete(`/clientes/${id}`);
      debugLog("Cliente excluído com sucesso:", response);
      await loadClientes();
    } catch (err) {
      console.error("Erro ao excluir cliente:", err);
      console.error("Resposta do erro:", err.response);
      setError(err.response?.data?.detail || "Erro ao excluir cliente");
    }
  };

  const handleDeletePet = async (petId) => {
    if (!confirm("Tem certeza que deseja excluir este pet?")) return;

    try {
      debugLog("Excluindo pet ID:", petId);
      await api.delete(`/clientes/pets/${petId}`);
      debugLog("Pet excluído com sucesso");

      // Limpar estado de expansão para forçar re-render
      setExpandedPets({});

      // Atualizar lista de clientes
      await loadClientes();
      debugLog("Lista de clientes atualizada");
    } catch (err) {
      console.error("Erro ao excluir pet:", err);
      alert(err.response?.data?.detail || "Erro ao excluir pet");
    }
  };

  const loadSaldoCampanhas = async (clienteId) => {
    if (!clienteId) return;
    try {
      const res = await api.get(`/campanhas/clientes/${clienteId}/saldo`);
      setSaldoCampanhas(res.data);
    } catch {
      setSaldoCampanhas(null);
    }
  };

  const lancarCarimboManual = async () => {
    if (!editingCliente?.id) return;
    setLancandoCarimbo(true);
    try {
      const res = await api.post("/campanhas/carimbos/manual", {
        customer_id: editingCliente.id,
      });
      await loadSaldoCampanhas(editingCliente.id);
      alert(`✅ Carimbo lançado! Total: ${res.data.total_carimbos} carimbo(s)`);
    } catch (e) {
      alert(e?.response?.data?.detail || "Erro ao lançar carimbo.");
    } finally {
      setLancandoCarimbo(false);
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
        console.error("Erro ao carregar resumo financeiro:", err);
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
      debugLog("🐛 Cliente carregado do backend:", {
        id: cliente.id,
        nome: cliente.nome,
        is_entregador: cliente.is_entregador,
        entregador_padrao: cliente.entregador_padrao,
        entregador_padrao_tipo: typeof cliente.entregador_padrao,
      });

      setFormData({
        tipo_cadastro: cliente.tipo_cadastro || "cliente",
        tipo_pessoa: cliente.tipo_pessoa || "PF",
        nome: cliente.nome,
        data_nascimento: cliente.data_nascimento
          ? String(cliente.data_nascimento).slice(0, 10)
          : "",
        cpf: cliente.cpf || "",
        email: cliente.email || "",
        telefone: cliente.telefone || "",
        celular: cliente.celular || "",
        celular_whatsapp: true,
        cnpj: cliente.cnpj || "",
        inscricao_estadual: cliente.inscricao_estadual || "",
        razao_social: cliente.razao_social || "",
        nome_fantasia: cliente.nome_fantasia || "",
        responsavel: cliente.responsavel || "",
        crmv: cliente.crmv || "",
        // Sistema de parceiros
        parceiro_ativo: cliente.parceiro_ativo || false,
        parceiro_desde: cliente.parceiro_desde || "",
        parceiro_observacoes: cliente.parceiro_observacoes || "",
        cep: cliente.cep || "",
        endereco: cliente.endereco || "",
        numero: cliente.numero || "",
        complemento: cliente.complemento || "",
        bairro: cliente.bairro || "",
        cidade: cliente.cidade || "",
        estado: cliente.estado || "",
        endereco_entrega: cliente.endereco_entrega || "",
        endereco_entrega_2: cliente.endereco_entrega_2 || "",
        // Campos de entrega
        is_entregador: cliente.is_entregador || false,
        entregador_ativo:
          cliente.entregador_ativo !== undefined
            ? cliente.entregador_ativo
            : true,
        entregador_padrao: cliente.entregador_padrao || false,
        tipo_vinculo_entrega: cliente.tipo_vinculo_entrega || "",
        // Funcionário com controla RH
        controla_rh: cliente.controla_rh || false,
        gera_conta_pagar_custo_entrega:
          cliente.gera_conta_pagar_custo_entrega || false,
        media_entregas_configurada: cliente.media_entregas_configurada || "",
        custo_rh_ajustado: cliente.custo_rh_ajustado || "",
        // Terceirizado/Eventual
        modelo_custo_entrega: cliente.modelo_custo_entrega || "",
        taxa_fixa_entrega: cliente.taxa_fixa_entrega || "",
        valor_por_km_entrega: cliente.valor_por_km_entrega || "",
        // Moto
        moto_propria:
          cliente.moto_propria !== undefined ? cliente.moto_propria : true,
        // 📆 Acerto financeiro (ETAPA 4)
        tipo_acerto_entrega: cliente.tipo_acerto_entrega || "",
        dia_semana_acerto: cliente.dia_semana_acerto || "",
        dia_mes_acerto: cliente.dia_mes_acerto || "",
        // Legado (manter compatibilidade)
        is_terceirizado: cliente.is_terceirizado || false,
        recebe_repasse: cliente.recebe_repasse || false,
        gera_conta_pagar: cliente.gera_conta_pagar || false,
        observacoes: cliente.observacoes || "",
        tags: "",
      });
      setPets(cliente.pets || []);

      // Carregar endereços adicionais
      setEnderecosAdicionais(cliente.enderecos_adicionais || []);

      // Carregar apenas resumo financeiro leve (não histórico completo)
      loadResumoFinanceiro(cliente.id);
      loadSaldoCampanhas(cliente.id);

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
      const tipoCadastro =
        tipo || (tipoFiltro === "todos" ? "cliente" : tipoFiltro);
      // Fornecedor deve ser PJ por padrão
      const tipoPessoa = tipoCadastro === "fornecedor" ? "PJ" : "PF";

      setFormData({
        tipo_cadastro: tipoCadastro,
        tipo_pessoa: tipoPessoa,
        nome: "",
        data_nascimento: "",
        cpf: "",
        email: "",
        telefone: "",
        celular: "",
        celular_whatsapp: true,
        cnpj: "",
        inscricao_estadual: "",
        razao_social: "",
        nome_fantasia: "",
        responsavel: "",
        crmv: "",
        // Sistema de parceiros
        parceiro_ativo: false,
        parceiro_desde: "",
        parceiro_observacoes: "",
        cep: "",
        endereco: "",
        numero: "",
        complemento: "",
        bairro: "",
        cidade: "",
        estado: "",
        // Campos de entrega
        is_entregador: false,
        entregador_ativo: true,
        tipo_vinculo_entrega: "",
        // Funcionário com controla RH
        controla_rh: false,
        media_entregas_configurada: "",
        custo_rh_ajustado: "",
        // Terceirizado/Eventual
        modelo_custo_entrega: "",
        taxa_fixa_entrega: "",
        valor_por_km_entrega: "",
        // Moto
        moto_propria: true,
        // Legado (manter compatibilidade)
        is_terceirizado: false,
        recebe_repasse: false,
        gera_conta_pagar: false,
        observacoes: "",
        tags: "",
      });
      setPets([]);
      setEnderecosAdicionais([]); // Limpar endereços adicionais
      setCurrentStep(1);
    }
    setShowModal(true);
    setError("");
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
    setSaldoCampanhas(null);
  };

  const verificarDuplicata = async () => {
    try {
      const params = new URLSearchParams();

      if (formData.cpf) params.append("cpf", formData.cpf);
      if (formData.cnpj) params.append("cnpj", formData.cnpj);
      if (formData.telefone) params.append("telefone", formData.telefone);
      if (formData.celular) params.append("celular", formData.celular);
      if (formData.crmv) params.append("crmv", formData.crmv);
      if (editingCliente) params.append("cliente_id", editingCliente.id);

      if (params.toString()) {
        const response = await api.get(
          `/clientes/verificar-duplicata/campo?${params.toString()}`,
        );

        if (response.data.duplicado) {
          setClienteDuplicado(response.data);
          setShowDuplicadoWarning(true);
          return true;
        }
      }
      return false;
    } catch (err) {
      console.error("Erro ao verificar duplicata:", err);
      return false;
    }
  };

  const nextStep = async () => {
    if (currentStep < 6) {
      setError("");
      setCepError("");

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

  // Verificar se o campo é um documento único (não pode ser transferido)
  const isDocumentoUnico = (campo) => {
    return ["cpf", "cnpj", "crmv"].includes(campo);
  };

  const continuarMesmoDuplicado = () => {
    // Mostrar confirmação de remoção
    setShowConfirmacaoRemocao(true);
  };

  const confirmarRemocaoEContinuar = async () => {
    try {
      setLoading(true);

      // Calcular próximo código disponível
      const proximoCodigo =
        editingCliente?.codigo ||
        (clientes.length > 0
          ? Math.max(...clientes.map((c) => c.codigo)) + 1
          : 1);

      // Remover campo duplicado do cadastro antigo
      await api.put(
        `/clientes/${clienteDuplicado.cliente.id}/remover-campo`,
        null,
        {
          params: {
            campo: clienteDuplicado.campo,
            novo_cliente_codigo: proximoCodigo,
          },
        },
      );

      // Fechar avisos e continuar
      setShowConfirmacaoRemocao(false);
      setShowDuplicadoWarning(false);
      setClienteDuplicado(null);
      setCurrentStep(currentStep + 1);
    } catch (err) {
      setError(err.response?.data?.detail || "Erro ao remover campo duplicado");
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
    const elemento = document.getElementById(
      `cliente-${clienteDuplicado.cliente.id}`,
    );
    if (elemento) {
      elemento.scrollIntoView({ behavior: "smooth", block: "center" });
      elemento.classList.add("ring-4", "ring-yellow-400");
      setTimeout(() => {
        elemento.classList.remove("ring-4", "ring-yellow-400");
      }, 3000);
    }
  };

  const editarClienteExistente = () => {
    // Carregar o cliente existente para edição
    const clienteParaEditar = clientes.find(
      (c) => c.id === clienteDuplicado.cliente.id,
    );
    if (clienteParaEditar) {
      // Fechar aviso de duplicata
      setShowDuplicadoWarning(false);
      setClienteDuplicado(null);
      setShowConfirmacaoRemocao(false);
      // Abrir modal com o cliente para edição
      openModal(clienteParaEditar);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setError("");
      setCepError("");
      setCurrentStep(currentStep - 1);
    }
  };

  const addPet = () => {
    if (!currentPet.nome || !currentPet.especie) {
      setError("Nome e espécie são obrigatórios");
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
        codigo: originalPet.codigo,
      };
      setPets(updatedPets);
      setEditingPetIndex(null);
    } else {
      // Adicionar novo pet
      setPets([...pets, { ...currentPet }]);
    }

    setCurrentPet({
      nome: "",
      especie: "",
      raca: "",
      sexo: "",
      data_nascimento: "",
      cor: "",
      peso: "",
      observacoes: "",
      castrado: false,
      porte: "",
      microchip: "",
      alergias: "",
      doencas_cronicas: "",
      medicamentos_continuos: "",
      historico_clinico: "",
      foto_url: "",
      idade_aproximada: "",
    });
    setError("");
    setHighlightedPetId(null); // Limpar destaque
  };

  const editPet = (index) => {
    const pet = pets[index];
    setCurrentPet({
      nome: pet.nome || "",
      especie: pet.especie || "",
      raca: pet.raca || "",
      sexo: pet.sexo || "",
      data_nascimento: pet.data_nascimento || "",
      cor: pet.cor || "",
      peso: pet.peso || "",
      observacoes: pet.observacoes || "",
      castrado: pet.castrado || false,
      porte: pet.porte || "",
      microchip: pet.microchip || "",
      alergias: pet.alergias || "",
      doencas_cronicas: pet.doencas_cronicas || "",
      medicamentos_continuos: pet.medicamentos_continuos || "",
      historico_clinico: pet.historico_clinico || "",
      foto_url: pet.foto_url || "",
      idade_aproximada: pet.idade_aproximada || "",
    });
    setEditingPetIndex(index);
    // Destacar o pet sendo editado
    if (pet?.id) {
      setHighlightedPetId(pet.id);
    }
  };

  const cancelEditPet = () => {
    setCurrentPet({
      nome: "",
      especie: "",
      raca: "",
      sexo: "",
      data_nascimento: "",
      cor: "",
      peso: "",
      observacoes: "",
      castrado: false,
      porte: "",
      microchip: "",
      alergias: "",
      doencas_cronicas: "",
      medicamentos_continuos: "",
      historico_clinico: "",
      foto_url: "",
      idade_aproximada: "",
    });
    setEditingPetIndex(null);
  };

  const removePet = (index) => {
    setPets(pets.filter((_, i) => i !== index));
  };

  const abrirPessoaPorCodigoNoEnter = () => {
    const termo = String(searchTerm || "").trim();
    if (!termo) return;

    const clienteCodigoExato = getClientePorCodigoExato(termo);

    if (clienteCodigoExato) {
      openModal(clienteCodigoExato);
    }
  };

  // ============================================================================
  // COMPONENTE: ClienteSegmentoBadgeWrapper (lazy load badge na lista)
  const isCarregamentoInicial = loading && !carregamentoInicialConcluido;

  if (isCarregamentoInicial) {
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
        <p className="text-gray-600 mt-1">
          Gerenciamento de clientes, fornecedores, veterinários, funcionários e
          pets
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex gap-2">
          <button
            onClick={() => {
              setTipoFiltro("todos");
              setPaginaAtual(1);
            }}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === "todos"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => {
              setTipoFiltro("cliente");
              setPaginaAtual(1);
            }}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === "cliente"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            Clientes
          </button>
          <button
            onClick={() => {
              setTipoFiltro("fornecedor");
              setPaginaAtual(1);
            }}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === "fornecedor"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            Fornecedores
          </button>
          <button
            onClick={() => {
              setTipoFiltro("veterinario");
              setPaginaAtual(1);
            }}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === "veterinario"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            Veterinários
          </button>
          <button
            onClick={() => {
              setTipoFiltro("funcionario");
              setPaginaAtual(1);
            }}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              tipoFiltro === "funcionario"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
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
            placeholder="Buscar por código, nome, CPF/CNPJ, email ou telefone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                abrirPessoaPorCodigoNoEnter();
              }
            }}
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
            <FiPlus /> Novo{" "}
            {tipoFiltro === "cliente"
              ? "Cliente"
              : tipoFiltro === "fornecedor"
                ? "Fornecedor"
                : tipoFiltro === "veterinario"
                  ? "Veterinário"
                  : tipoFiltro === "funcionario"
                    ? "Funcionário"
                    : "Cadastro"}
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

      {/* Paginação Superior */}
      {!loading && totalRegistros > 0 && (
        <div className="px-4 py-3 bg-gray-50 border border-gray-200 rounded-t-lg flex items-center justify-between mb-0">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              Mostrando {(paginaAtual - 1) * registrosPorPagina + 1} a{" "}
              {Math.min(paginaAtual * registrosPorPagina, totalRegistros)} de{" "}
              {totalRegistros} pessoas
            </span>
            <select
              value={registrosPorPagina}
              onChange={(e) => {
                setRegistrosPorPagina(Number(e.target.value));
                setPaginaAtual(1);
              }}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value={10}>10 por página</option>
              <option value={20}>20 por página</option>
              <option value={30}>30 por página</option>
              <option value={50}>50 por página</option>
              <option value={100}>100 por página</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPaginaAtual(1)}
              disabled={paginaAtual === 1}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Primeira
            </button>
            <button
              onClick={() => setPaginaAtual((prev) => Math.max(prev - 1, 1))}
              disabled={paginaAtual === 1}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anterior
            </button>

            {/* Páginas numeradas */}
            <div className="flex items-center gap-1">
              {Array.from(
                {
                  length: Math.min(
                    Math.ceil(totalRegistros / registrosPorPagina),
                    5,
                  ),
                },
                (_, i) => {
                  const totalPaginas = Math.ceil(
                    totalRegistros / registrosPorPagina,
                  );
                  let pageNum;
                  if (totalPaginas <= 5) {
                    pageNum = i + 1;
                  } else if (paginaAtual <= 3) {
                    pageNum = i + 1;
                  } else if (paginaAtual >= totalPaginas - 2) {
                    pageNum = totalPaginas - 4 + i;
                  } else {
                    pageNum = paginaAtual - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPaginaAtual(pageNum)}
                      className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                        paginaAtual === pageNum
                          ? "bg-purple-600 text-white"
                          : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                },
              )}
            </div>

            <button
              onClick={() =>
                setPaginaAtual((prev) =>
                  Math.min(
                    prev + 1,
                    Math.ceil(totalRegistros / registrosPorPagina),
                  ),
                )
              }
              disabled={
                paginaAtual === Math.ceil(totalRegistros / registrosPorPagina)
              }
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Próxima
            </button>
            <button
              onClick={() =>
                setPaginaAtual(Math.ceil(totalRegistros / registrosPorPagina))
              }
              disabled={
                paginaAtual === Math.ceil(totalRegistros / registrosPorPagina)
              }
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Última
            </button>
          </div>
        </div>
      )}

      {/* Clientes Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {filteredClientes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    ID
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Nome
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    CPF/CNPJ
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Celular
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Pets
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    Segmento
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
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
                          <span className="text-sm font-medium text-gray-900">
                            {cliente.nome}
                          </span>
                          {cliente.tipo_pessoa === "PJ" &&
                            cliente.razao_social && (
                              <span className="text-xs text-gray-500">
                                {cliente.razao_social}
                              </span>
                            )}
                          {cliente.parceiro_ativo && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full w-fit">
                              <FiDollarSign size={12} />
                              Parceiro
                            </span>
                          )}
                          {cliente.de_parceiro && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full w-fit">
                              Pet Shop Parceiro
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {cliente.tipo_pessoa === "PF"
                          ? cliente.cpf || "-"
                          : cliente.cnpj || "-"}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {cliente.celular || "-"}
                      </td>
                      <td
                        className="px-4 py-3 whitespace-nowrap"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() =>
                            setExpandedPets({
                              ...expandedPets,
                              [cliente.id]: !expandedPets[cliente.id],
                            })
                          }
                          className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 transition-colors"
                        >
                          <PawPrint size={16} className="text-gray-400" />
                          <span>{cliente.pets?.length || 0}</span>
                          {cliente.pets && cliente.pets.length > 0 && (
                            <FiArrowRight
                              size={14}
                              className={`transform transition-transform ${expandedPets[cliente.id] ? "rotate-90" : ""}`}
                            />
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {/* Desabilitado: causa muitas requisições 404 na listagem */}
                        {/* <ClienteSegmentoBadgeWrapper clienteId={cliente.id} /> */}
                        <span className="text-xs text-gray-400">-</span>
                      </td>
                      <td
                        className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex items-center justify-end gap-2">
                          {cliente.celular && (
                            <button
                              onClick={() => {
                                const celular = cliente.celular.replace(
                                  /\D/g,
                                  "",
                                );
                                window.open(
                                  `https://wa.me/55${celular}`,
                                  "_blank",
                                );
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
                          {!cliente.de_parceiro && (
                          <button
                            onClick={() => handleDelete(cliente.id)}
                            className="text-red-600 hover:text-red-900 transition-colors"
                            title="Excluir"
                          >
                            <FiTrash2 size={16} />
                          </button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Pets Row */}
                    {expandedPets[cliente.id] &&
                      cliente.pets &&
                      cliente.pets.length > 0 && (
                        <tr>
                          <td colSpan="7" className="px-4 py-3 bg-gray-50">
                            <div className="space-y-2">
                              <p className="text-xs font-semibold text-gray-700 mb-2">
                                Pets de {cliente.nome}:
                              </p>
                              {cliente.pets.map((pet) => (
                                <div
                                  key={pet.id}
                                  className={`bg-white rounded-lg p-3 flex justify-between items-start border border-gray-200 ${
                                    highlightedPetId === pet.id
                                      ? "ring-2 ring-blue-400 shadow-lg bg-blue-50"
                                      : ""
                                  }`}
                                >
                                  <div className="flex-1 grid grid-cols-4 gap-4">
                                    <div>
                                      <p className="text-xs text-gray-500">
                                        Nome
                                      </p>
                                      <p className="text-sm font-medium text-gray-900">
                                        {pet.nome}
                                      </p>
                                    </div>
                                    <div>
                                      <p className="text-xs text-gray-500">
                                        Espécie/Raça
                                      </p>
                                      <p className="text-sm text-gray-700">
                                        {pet.especie}{" "}
                                        {pet.raca && `- ${pet.raca}`}
                                      </p>
                                    </div>
                                    <div>
                                      <p className="text-xs text-gray-500">
                                        Sexo
                                      </p>
                                      <p className="text-sm text-gray-700">
                                        {pet.sexo || "-"}
                                      </p>
                                    </div>
                                    <div>
                                      <p className="text-xs text-gray-500">
                                        Nascimento
                                      </p>
                                      <p className="text-sm text-gray-700">
                                        {pet.data_nascimento
                                          ? new Date(
                                              pet.data_nascimento,
                                            ).toLocaleDateString("pt-BR")
                                          : "-"}
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

        {/* Paginação Inferior */}
        {!loading && totalRegistros > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                Mostrando {(paginaAtual - 1) * registrosPorPagina + 1} a{" "}
                {Math.min(paginaAtual * registrosPorPagina, totalRegistros)} de{" "}
                {totalRegistros} pessoas
              </span>
              <select
                value={registrosPorPagina}
                onChange={(e) => {
                  setRegistrosPorPagina(Number(e.target.value));
                  setPaginaAtual(1);
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value={10}>10 por página</option>
                <option value={20}>20 por página</option>
                <option value={30}>30 por página</option>
                <option value={50}>50 por página</option>
                <option value={100}>100 por página</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPaginaAtual(1)}
                disabled={paginaAtual === 1}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Primeira
              </button>
              <button
                onClick={() => setPaginaAtual((prev) => Math.max(prev - 1, 1))}
                disabled={paginaAtual === 1}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>

              {/* Páginas numeradas */}
              <div className="flex items-center gap-1">
                {Array.from(
                  {
                    length: Math.min(
                      Math.ceil(totalRegistros / registrosPorPagina),
                      5,
                    ),
                  },
                  (_, i) => {
                    const totalPaginas = Math.ceil(
                      totalRegistros / registrosPorPagina,
                    );
                    let pageNum;
                    if (totalPaginas <= 5) {
                      pageNum = i + 1;
                    } else if (paginaAtual <= 3) {
                      pageNum = i + 1;
                    } else if (paginaAtual >= totalPaginas - 2) {
                      pageNum = totalPaginas - 4 + i;
                    } else {
                      pageNum = paginaAtual - 2 + i;
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPaginaAtual(pageNum)}
                        className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                          paginaAtual === pageNum
                            ? "bg-purple-600 text-white"
                            : "text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  },
                )}
              </div>

              <button
                onClick={() =>
                  setPaginaAtual((prev) =>
                    Math.min(
                      prev + 1,
                      Math.ceil(totalRegistros / registrosPorPagina),
                    ),
                  )
                }
                disabled={
                  paginaAtual === Math.ceil(totalRegistros / registrosPorPagina)
                }
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Próxima
              </button>
              <button
                onClick={() =>
                  setPaginaAtual(Math.ceil(totalRegistros / registrosPorPagina))
                }
                disabled={
                  paginaAtual === Math.ceil(totalRegistros / registrosPorPagina)
                }
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Última
              </button>
            </div>
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
                    ? `Editar ${editingCliente.tipo_cadastro === "cliente" ? "Cliente" : editingCliente.tipo_cadastro === "fornecedor" ? "Fornecedor" : "Veterinário"}`
                    : `Adicionar ${formData.tipo_cadastro === "cliente" ? "Cliente" : formData.tipo_cadastro === "fornecedor" ? "Fornecedor" : "Veterinário"}`}
                </h2>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600"
                >
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
                          currentStep > step.number
                            ? "bg-green-500 text-white hover:bg-green-600"
                            : currentStep === step.number
                              ? "bg-blue-500 text-white hover:bg-blue-600"
                              : "bg-gray-300 text-gray-600 hover:bg-gray-400"
                        }`}
                        type="button"
                        title={`Ir para: ${step.title}`}
                      >
                        {currentStep > step.number ? <FiCheck /> : step.number}
                      </button>
                      <span className="text-xs mt-1 text-center hidden md:block">
                        {step.title}
                      </span>
                    </div>
                    {index < steps.length - 1 && (
                      <div
                        className={`h-0.5 flex-1 ${currentStep > step.number ? "bg-green-500" : "bg-gray-300"}`}
                      />
                    )}
                  </div>
                ))}
              </div>
              <div className="text-center text-sm text-gray-600">
                {currentStep}/6
              </div>
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
                <ClientesNovoDuplicadoWarning
                  clienteDuplicado={clienteDuplicado}
                  clientes={clientes}
                  editingCliente={editingCliente}
                  isDocumentoUnico={isDocumentoUnico}
                  loading={loading}
                  onCancelarRemocao={cancelarRemocao}
                  onConfirmarRemocao={confirmarRemocaoEContinuar}
                  onContinuarMesmoDuplicado={continuarMesmoDuplicado}
                  onEditarClienteExistente={editarClienteExistente}
                  onIrParaClienteExistente={irParaClienteExistente}
                  showConfirmacaoRemocao={showConfirmacaoRemocao}
                />
              )}

                            {/* Step 1: Informacoes do Cliente */}
              {currentStep === 1 && (
                <ClientesNovoCadastroStep
                  formData={formData}
                  setFormData={setFormData}
                  setShowDuplicadoWarning={setShowDuplicadoWarning}
                  setClienteDuplicado={setClienteDuplicado}
                />
              )}

              {/* Step 2: Contatos */}
              {currentStep === 2 && (
                <ClientesNovoContatosStep
                  formData={formData}
                  setFormData={setFormData}
                  setShowDuplicadoWarning={setShowDuplicadoWarning}
                  setClienteDuplicado={setClienteDuplicado}
                />
              )}

              {/* Step 3: Endere?o */}
              {currentStep === 3 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Endereço
                  </h3>

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
                          setFormData({ ...formData, cep });
                          if (cep.replace(/\D/g, "").length === 8) {
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
                        {loadingCep ? "Buscando..." : "Buscar"}
                      </button>
                    </div>
                    {cepError && (
                      <p className="text-xs text-red-500 mt-1">{cepError}</p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      Digite o CEP para preencher o endereço automaticamente
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Endereço
                    </label>
                    <input
                      type="text"
                      value={formData.endereco}
                      onChange={(e) =>
                        setFormData({ ...formData, endereco: e.target.value })
                      }
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
                        onChange={(e) =>
                          setFormData({ ...formData, numero: e.target.value })
                        }
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
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            complemento: e.target.value,
                          })
                        }
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
                      onChange={(e) =>
                        setFormData({ ...formData, bairro: e.target.value })
                      }
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
                        onChange={(e) =>
                          setFormData({ ...formData, cidade: e.target.value })
                        }
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
                        onChange={(e) =>
                          setFormData({ ...formData, estado: e.target.value })
                        }
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
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Informações complementares
                  </h3>

                  {/* Endereços Adicionais */}
                  <div className="border-b pb-4 mb-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="text-md font-semibold text-gray-800">
                          Endereços Adicionais
                        </h4>
                        <p className="text-sm text-gray-600">
                          Cadastre múltiplos endereços para entrega, cobrança,
                          etc.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => abrirModalEndereco()}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 4v16m8-8H4"
                          />
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
                                  <span
                                    className={`px-2 py-1 text-xs font-medium rounded ${
                                      endereco.tipo === "entrega"
                                        ? "bg-blue-100 text-blue-800"
                                        : endereco.tipo === "cobranca"
                                          ? "bg-green-100 text-green-800"
                                          : endereco.tipo === "comercial"
                                            ? "bg-purple-100 text-purple-800"
                                            : endereco.tipo === "residencial"
                                              ? "bg-orange-100 text-orange-800"
                                              : "bg-gray-100 text-gray-800"
                                    }`}
                                  >
                                    {endereco.tipo === "entrega"
                                      ? "📦 Entrega"
                                      : endereco.tipo === "cobranca"
                                        ? "💰 Cobrança"
                                        : endereco.tipo === "comercial"
                                          ? "🏢 Comercial"
                                          : endereco.tipo === "residencial"
                                            ? "🏠 Residencial"
                                            : "📍 Trabalho"}
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
                                  {endereco.complemento &&
                                    ` - ${endereco.complemento}`}
                                </p>
                                <p className="text-xs text-gray-600 mt-1">
                                  {endereco.bairro}, {endereco.cidade}/
                                  {endereco.estado}
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
                                  <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                    />
                                  </svg>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => removerEndereco(index)}
                                  className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                                  title="Excluir"
                                >
                                  <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                    />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500 text-sm">
                        <svg
                          className="w-12 h-12 mx-auto mb-2 text-gray-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                          />
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                          />
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
                      onChange={(e) =>
                        setFormData({ ...formData, tags: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="Ex: Bom pagador, Cliente fiel, VIP"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Separe por vírgula para múltiplas tags
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Observações
                    </label>
                    <textarea
                      value={formData.observacoes}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          observacoes: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      rows="4"
                      placeholder="Informações adicionais sobre o cliente..."
                    />
                  </div>
                </div>
              )}

              {/* Step 5: Animais - SIMPLIFICADO */}
              {currentStep === 5 && (
                <ClientesNovoPetsStep
                  pets={pets}
                  editingCliente={editingCliente}
                  navigate={navigate}
                />
              )}

              {/* Step 6: Financeiro */}
              {currentStep === 6 && (
                <ClientesNovoFinanceiroStep
                  editingCliente={editingCliente}
                  refreshKeyCredito={refreshKeyCredito}
                  resumoFinanceiro={resumoFinanceiro}
                  loadingResumo={loadingResumo}
                  saldoCampanhas={saldoCampanhas}
                  setMostrarModalAdicionarCredito={setMostrarModalAdicionarCredito}
                  setMostrarModalRemoverCredito={setMostrarModalRemoverCredito}
                  navigate={navigate}
                />
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

      {/* Modal de Endereco Adicional */}
      {mostrarFormEndereco && enderecoAtual && (
        <ClientesNovoEnderecoModal
          enderecoAtual={enderecoAtual}
          fecharModalEndereco={fecharModalEndereco}
          loadingCepEndereco={loadingCepEndereco}
          salvarEndereco={salvarEndereco}
          buscarCepModal={buscarCepModal}
          setEnderecoAtual={setEnderecoAtual}
        />
      )}

      {/* Modal de Importação */}
      <ModalImportacaoPessoas
        isOpen={showModalImportacao}
        onClose={() => {
          setShowModalImportacao(false);
          fetchClientes();
        }}
      />

      {/* Modal de Adicionar Crédito */}
      {mostrarModalAdicionarCredito && editingCliente && (
        <ModalAdicionarCredito
          cliente={editingCliente}
          onConfirmar={(novoSaldo) => {
            setEditingCliente({ ...editingCliente, credito: novoSaldo });
            setRefreshKeyCredito((k) => k + 1);
            loadClientes();
          }}
          onClose={() => setMostrarModalAdicionarCredito(false)}
        />
      )}

      {/* Modal de Remover Crédito */}
      {mostrarModalRemoverCredito && editingCliente && (
        <ModalRemoverCredito
          cliente={editingCliente}
          onConfirmar={(novoSaldo) => {
            setEditingCliente({ ...editingCliente, credito: novoSaldo });
            setRefreshKeyCredito((k) => k + 1);
            loadClientes();
          }}
          onClose={() => setMostrarModalRemoverCredito(false)}
        />
      )}

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

