import { useEffect, useState } from "react";
import { FiAlertCircle } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ClientesNovoActionsBar from "../components/clientes/ClientesNovoActionsBar";
import ClientesNovoModalsLayer from "../components/clientes/ClientesNovoModalsLayer";
import ClientesNovoTabelaSection from "../components/clientes/ClientesNovoTabelaSection";
import ClientesNovoTabsBar from "../components/clientes/ClientesNovoTabsBar";
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

      <ClientesNovoTabsBar
        tipoFiltro={tipoFiltro}
        setTipoFiltro={setTipoFiltro}
        setPaginaAtual={setPaginaAtual}
      />
      <ClientesNovoActionsBar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        abrirPessoaPorCodigoNoEnter={abrirPessoaPorCodigoNoEnter}
        setShowModalImportacao={setShowModalImportacao}
        openModal={openModal}
        tipoFiltro={tipoFiltro}
      />
      {error && !showModal && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <FiAlertCircle />
          <span>{error}</span>
        </div>
      )}
      <ClientesNovoTabelaSection
        loading={loading}
        totalRegistros={totalRegistros}
        paginaAtual={paginaAtual}
        registrosPorPagina={registrosPorPagina}
        setRegistrosPorPagina={setRegistrosPorPagina}
        setPaginaAtual={setPaginaAtual}
        filteredClientes={filteredClientes}
        expandedPets={expandedPets}
        setExpandedPets={setExpandedPets}
        highlightedPetId={highlightedPetId}
        setHighlightedPetId={setHighlightedPetId}
        openModal={openModal}
        handleDelete={handleDelete}
        handleDeletePet={handleDeletePet}
      />

      <ClientesNovoModalsLayer
        showModal={showModal}
        editingCliente={editingCliente}
        formData={formData}
        closeModal={closeModal}
        steps={steps}
        currentStep={currentStep}
        setCurrentStep={setCurrentStep}
        error={error}
        showDuplicadoWarning={showDuplicadoWarning}
        clienteDuplicado={clienteDuplicado}
        clientes={clientes}
        isDocumentoUnico={isDocumentoUnico}
        loading={loading}
        cancelarRemocao={cancelarRemocao}
        confirmarRemocaoEContinuar={confirmarRemocaoEContinuar}
        continuarMesmoDuplicado={continuarMesmoDuplicado}
        editarClienteExistente={editarClienteExistente}
        irParaClienteExistente={irParaClienteExistente}
        showConfirmacaoRemocao={showConfirmacaoRemocao}
        setShowDuplicadoWarning={setShowDuplicadoWarning}
        setClienteDuplicado={setClienteDuplicado}
        setFormData={setFormData}
        buscarCep={buscarCep}
        loadingCep={loadingCep}
        cepError={cepError}
        enderecosAdicionais={enderecosAdicionais}
        abrirModalEndereco={abrirModalEndereco}
        removerEndereco={removerEndereco}
        pets={pets}
        navigate={navigate}
        refreshKeyCredito={refreshKeyCredito}
        resumoFinanceiro={resumoFinanceiro}
        loadingResumo={loadingResumo}
        saldoCampanhas={saldoCampanhas}
        setMostrarModalAdicionarCredito={setMostrarModalAdicionarCredito}
        setMostrarModalRemoverCredito={setMostrarModalRemoverCredito}
        prevStep={prevStep}
        nextStep={nextStep}
        handleSubmitFinal={handleSubmitFinal}
        mostrarFormEndereco={mostrarFormEndereco}
        enderecoAtual={enderecoAtual}
        fecharModalEndereco={fecharModalEndereco}
        loadingCepEndereco={loadingCepEndereco}
        salvarEndereco={salvarEndereco}
        buscarCepModal={buscarCepModal}
        setEnderecoAtual={setEnderecoAtual}
        showModalImportacao={showModalImportacao}
        setShowModalImportacao={setShowModalImportacao}
        fetchClientes={loadClientes}
        mostrarModalAdicionarCredito={mostrarModalAdicionarCredito}
        mostrarModalRemoverCredito={mostrarModalRemoverCredito}
        setEditingCliente={setEditingCliente}
        setRefreshKeyCredito={setRefreshKeyCredito}
        loadClientes={loadClientes}
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



