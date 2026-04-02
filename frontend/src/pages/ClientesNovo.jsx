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
import ClientesNovoComplementaresStep from "../components/clientes/ClientesNovoComplementaresStep";
import ClientesNovoContatosStep from "../components/clientes/ClientesNovoContatosStep";
import ClientesNovoDuplicadoWarning from "../components/clientes/ClientesNovoDuplicadoWarning";
import ClientesNovoEnderecoStep from "../components/clientes/ClientesNovoEnderecoStep";
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

  // Estados de paginaÃ§Ã£o
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
    // Campo veterinÃ¡rio
    crmv: "",
    // Sistema de parceiros (comissÃµes)
    parceiro_ativo: false,
    parceiro_desde: "",
    parceiro_observacoes: "",
    // EndereÃ§o
    cep: "",
    endereco: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    estado: "",
    // EndereÃ§os de entrega
    endereco_entrega: "",
    endereco_entrega_2: "",
    // Campos de entrega (Sprint 1 - Bloco 4)
    is_entregador: false,
    entregador_ativo: true,
    entregador_padrao: false,
    tipo_vinculo_entrega: "",
    // FuncionÃ¡rio com controla RH
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
    // ðŸ“† Acerto financeiro (ETAPA 4)
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

  // Estado para endereÃ§os adicionais
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
    { number: 1, title: "InformaÃ§Ãµes do cliente" },
    { number: 2, title: "Contatos" },
    { number: 3, title: "EndereÃ§o" },
    { number: 4, title: "InformaÃ§Ãµes complementares" },
    { number: 5, title: "Animais" },
    { number: 6, title: "Financeiro" },
  ];

  // Debounce para busca (aguarda 500ms apÃ³s usuÃ¡rio parar de digitar)
  useEffect(() => {
    const timer = setTimeout(() => {
      // Resetar para pÃ¡gina 1 ao buscar
      if (paginaAtual !== 1) {
        setPaginaAtual(1);
      } else {
        loadClientes();
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Carregar raÃ§as quando espÃ©cie mudar
  useEffect(() => {
    if (currentPet && currentPet.especie) {
      loadRacas(currentPet.especie);
    } else {
      setRacas([]);
    }
  }, [currentPet?.especie]);

  // Editar pet automaticamente quando pets sÃ£o carregados
  useEffect(() => {
    if (petIdToEdit && pets.length > 0) {
      const petIndex = pets.findIndex((p) => p.id === petIdToEdit);
      if (petIndex !== -1) {
        editPet(petIndex);
        setPetIdToEdit(null); // Limpar apÃ³s editar
      }
    }
  }, [pets, petIdToEdit]);

  const loadRacas = async (especie) => {
    try {
      const response = await api.get(`/clientes/racas?especie=${especie}`);
      setRacas(response.data);
    } catch (err) {
      console.error("Erro ao carregar raÃ§as:", err);
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
        setCepError("CEP nÃ£o encontrado");
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

  // FunÃ§Ãµes de gerenciamento de endereÃ§os adicionais

  const handleSubmitFinal = async () => {
    setError("");

    try {
      // âœ… VALIDAÃ‡Ã•ES DE CAMPOS OBRIGATÃ“RIOS
      const errosValidacao = [];

      // Nome Ã© obrigatÃ³rio para todos
      if (!formData.nome || formData.nome.trim() === "") {
        errosValidacao.push("Nome");
      }

      // ValidaÃ§Ãµes especÃ­ficas para Pessoa JurÃ­dica
      if (formData.tipo_pessoa === "PJ") {
        if (!formData.cnpj || formData.cnpj.trim() === "") {
          errosValidacao.push("CNPJ");
        }
        if (!formData.razao_social || formData.razao_social.trim() === "") {
          errosValidacao.push("RazÃ£o Social");
        }
      }

      // ValidaÃ§Ãµes especÃ­ficas para Pessoa FÃ­sica
      if (formData.tipo_pessoa === "PF") {
        if (
          formData.tipo_cadastro === "cliente" &&
          (!formData.cpf || formData.cpf.trim() === "")
        ) {
          // CPF opcional para clientes PF (muitos nÃ£o tÃªm)
          // Removido pois Ã© opcional
        }
      }

      // Se houver erros de validaÃ§Ã£o, mostrar e parar
      if (errosValidacao.length > 0) {
        const mensagem =
          "âŒ Faltam os seguintes campos obrigatÃ³rios:\n\n" +
          errosValidacao.map((campo) => `â€¢ ${campo}`).join("\n");
        alert(mensagem);
        setError(mensagem);
        return;
      }

      // âœ… VALIDAÃ‡Ã•ES DE ENTREGADOR (ETAPA 4)
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

        // Validar dia do mÃªs para acerto mensal
        if (
          formData.tipo_acerto_entrega === "mensal" &&
          !formData.dia_mes_acerto
        ) {
          alert("Informe o dia do mÃªs para o acerto mensal");
          return;
        }

        // Validar range do dia do mÃªs (1-28)
        if (formData.tipo_acerto_entrega === "mensal") {
          const dia = parseInt(formData.dia_mes_acerto);
          if (dia < 1 || dia > 28) {
            alert("O dia do mÃªs deve estar entre 1 e 28");
            return;
          }
        }
      }

      // Remover campos que nÃ£o existem no backend
      const { celular_whatsapp, tags, ...clienteData } = formData;

      // ðŸšš LÃ“GICA AUTOMÃTICA DE ENTREGA baseada em tipo_cadastro
      if (clienteData.is_entregador) {
        // Se Ã© funcionÃ¡rio â†’ tipo_vinculo = "funcionario" automaticamente
        if (clienteData.tipo_cadastro === "funcionario") {
          clienteData.tipo_vinculo_entrega = "funcionario";
          clienteData.is_terceirizado = false;
        }
        // Se Ã© fornecedor â†’ is_terceirizado = true e tipo_vinculo = "terceirizado" automaticamente
        else if (clienteData.tipo_cadastro === "fornecedor") {
          clienteData.is_terceirizado = true;
          clienteData.tipo_vinculo_entrega = "terceirizado";
        }
      }

      // Adicionar endereÃ§os adicionais aos dados do cliente
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

      // ðŸ› DEBUG: Verificar entregador_padrao
      // debugLog('ðŸ› entregador_padrao antes do envio:', clienteData.entregador_padrao);
      // debugLog('ðŸ› is_entregador:', clienteData.is_entregador);

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
      console.error("Detalhes de validaÃ§Ã£o:", errorDetails);

      // ðŸ” Mapeamento de campos tÃ©cnicos para nomes amigÃ¡veis
      const camposPtBr = {
        nome: "Nome",
        data_nascimento: "Data de Nascimento",
        cpf: "CPF",
        cnpj: "CNPJ",
        razao_social: "RazÃ£o Social",
        nome_fantasia: "Nome Fantasia",
        inscricao_estadual: "InscriÃ§Ã£o Estadual",
        responsavel: "ResponsÃ¡vel",
        telefone: "Telefone",
        celular: "Celular",
        email: "E-mail",
        cep: "CEP",
        endereco: "EndereÃ§o",
        numero: "NÃºmero",
        bairro: "Bairro",
        cidade: "Cidade",
        estado: "Estado",
        tipo_pessoa: "Tipo de Pessoa",
        tipo_cadastro: "Tipo de Cadastro",
        crmv: "CRMV",
        tipo_acerto_entrega: "Tipo de Acerto",
        dia_semana_acerto: "Dia da Semana para Acerto",
        dia_mes_acerto: "Dia do MÃªs para Acerto",
        tipo_vinculo_entrega: "Tipo de VÃ­nculo",
      };

      // âœ… Processar erros de validaÃ§Ã£o do backend
      let mensagemErro = "";

      if (errorDetails && Array.isArray(errorDetails)) {
        const camposFaltando = [];

        errorDetails.forEach((detail) => {
          // Extrair nome do campo (Ãºltimo elemento do array loc)
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
            "âŒ Faltam os seguintes campos obrigatÃ³rios:\n\n" +
            camposFaltando.map((campo) => `â€¢ ${campo}`).join("\n");
        }
      }

      // Usar a mensagem personalizada ou a genÃ©rica
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
      debugLog("Cliente excluÃ­do com sucesso:", response);
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
      debugLog("Pet excluÃ­do com sucesso");

      // Limpar estado de expansÃ£o para forÃ§ar re-render
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
      alert(`âœ… Carimbo lanÃ§ado! Total: ${res.data.total_carimbos} carimbo(s)`);
    } catch (e) {
      alert(e?.response?.data?.detail || "Erro ao lanÃ§ar carimbo.");
    } finally {
      setLancandoCarimbo(false);
    }
  };

  // Carregar apenas resumo financeiro leve (nÃ£o o histÃ³rico completo)
  const loadResumoFinanceiro = async (clienteId) => {
    if (!clienteId) return;

    try {
      setLoadingResumo(true);
      // Nova rota otimizada - apenas agregaÃ§Ãµes
      const response = await api.get(`/financeiro/cliente/${clienteId}/resumo`);
      setResumoFinanceiro(response.data.resumo);
    } catch (err) {
      // Silencioso se 404 (cliente sem histÃ³rico financeiro ainda)
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

      // ðŸ› DEBUG: Verificar o que vem do backend
      debugLog("ðŸ› Cliente carregado do backend:", {
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
        // FuncionÃ¡rio com controla RH
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
        // ðŸ“† Acerto financeiro (ETAPA 4)
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

      // Carregar endereÃ§os adicionais
      setEnderecosAdicionais(cliente.enderecos_adicionais || []);

      // Carregar apenas resumo financeiro leve (nÃ£o histÃ³rico completo)
      loadResumoFinanceiro(cliente.id);
      loadSaldoCampanhas(cliente.id);

      // Se um pet especÃ­fico deve ser editado, marcar para ediÃ§Ã£o
      if (petIdToEdit) {
        setPetIdToEdit(petIdToEdit);
        setCurrentStep(5);
      } else {
        setCurrentStep(1);
        setPetIdToEdit(null);
      }
    } else {
      setEditingCliente(null);
      // Se tipoFiltro for 'todos', usar 'cliente' como padrÃ£o
      const tipoCadastro =
        tipo || (tipoFiltro === "todos" ? "cliente" : tipoFiltro);
      // Fornecedor deve ser PJ por padrÃ£o
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
        // FuncionÃ¡rio com controla RH
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
      setEnderecosAdicionais([]); // Limpar endereÃ§os adicionais
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
          return; // NÃ£o avanÃ§a se houver duplicata
        }
      }

      // Verificar duplicatas na aba 2 (contatos: telefone/celular)
      if (currentStep === 2) {
        const temDuplicata = await verificarDuplicata();
        if (temDuplicata) {
          return; // NÃ£o avanÃ§a se houver duplicata
        }
      }

      setCurrentStep(currentStep + 1);
    }
  };

  // Verificar se o campo Ã© um documento Ãºnico (nÃ£o pode ser transferido)
  const isDocumentoUnico = (campo) => {
    return ["cpf", "cnpj", "crmv"].includes(campo);
  };

  const continuarMesmoDuplicado = () => {
    // Mostrar confirmaÃ§Ã£o de remoÃ§Ã£o
    setShowConfirmacaoRemocao(true);
  };

  const confirmarRemocaoEContinuar = async () => {
    try {
      setLoading(true);

      // Calcular prÃ³ximo cÃ³digo disponÃ­vel
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
    // Scroll atÃ© o cliente existente
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
    // Carregar o cliente existente para ediÃ§Ã£o
    const clienteParaEditar = clientes.find(
      (c) => c.id === clienteDuplicado.cliente.id,
    );
    if (clienteParaEditar) {
      // Fechar aviso de duplicata
      setShowDuplicadoWarning(false);
      setClienteDuplicado(null);
      setShowConfirmacaoRemocao(false);
      // Abrir modal com o cliente para ediÃ§Ã£o
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
      setError("Nome e espÃ©cie sÃ£o obrigatÃ³rios");
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
          Gerenciamento de clientes, fornecedores, veterinÃ¡rios, funcionÃ¡rios e
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
            VeterinÃ¡rios
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
            FuncionÃ¡rios
          </button>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6 flex flex-col sm:flex-row gap-4 justify-between">
        <div className="relative flex-1 max-w-md">
          <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por cÃ³digo, nome, CPF/CNPJ, email ou telefone..."
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
                  ? "VeterinÃ¡rio"
                  : tipoFiltro === "funcionario"
                    ? "FuncionÃ¡rio"
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

      {/* PaginaÃ§Ã£o Superior */}
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
              <option value={10}>10 por pÃ¡gina</option>
              <option value={20}>20 por pÃ¡gina</option>
              <option value={30}>30 por pÃ¡gina</option>
              <option value={50}>50 por pÃ¡gina</option>
              <option value={100}>100 por pÃ¡gina</option>
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

            {/* PÃ¡ginas numeradas */}
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
              PrÃ³xima
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
              Ãšltima
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
                    AÃ§Ãµes
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
                        {/* Desabilitado: causa muitas requisiÃ§Ãµes 404 na listagem */}
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
                                        EspÃ©cie/RaÃ§a
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

        {/* PaginaÃ§Ã£o Inferior */}
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
                <option value={10}>10 por pÃ¡gina</option>
                <option value={20}>20 por pÃ¡gina</option>
                <option value={30}>30 por pÃ¡gina</option>
                <option value={50}>50 por pÃ¡gina</option>
                <option value={100}>100 por pÃ¡gina</option>
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

              {/* PÃ¡ginas numeradas */}
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
                PrÃ³xima
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
                Ãšltima
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
                    ? `Editar ${editingCliente.tipo_cadastro === "cliente" ? "Cliente" : editingCliente.tipo_cadastro === "fornecedor" ? "Fornecedor" : "VeterinÃ¡rio"}`
                    : `Adicionar ${formData.tipo_cadastro === "cliente" ? "Cliente" : formData.tipo_cadastro === "fornecedor" ? "Fornecedor" : "VeterinÃ¡rio"}`}
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
                <ClientesNovoEnderecoStep
                  formData={formData}
                  setFormData={setFormData}
                  buscarCep={buscarCep}
                  loadingCep={loadingCep}
                  cepError={cepError}
                />
              )}
              {/* Step 4: Informacoes Complementares */}
              {currentStep === 4 && (
                <ClientesNovoComplementaresStep
                  formData={formData}
                  setFormData={setFormData}
                  enderecosAdicionais={enderecosAdicionais}
                  abrirModalEndereco={abrirModalEndereco}
                  removerEndereco={removerEndereco}
                />
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
                  AvanÃ§ar <FiArrowRight />
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

      {/* Modal de ImportaÃ§Ã£o */}
      <ModalImportacaoPessoas
        isOpen={showModalImportacao}
        onClose={() => {
          setShowModalImportacao(false);
          fetchClientes();
        }}
      />

      {/* Modal de Adicionar CrÃ©dito */}
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

      {/* Modal de Remover CrÃ©dito */}
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

      {/* Estilos para animaÃ§Ã£o do badge de parceiro */}
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


