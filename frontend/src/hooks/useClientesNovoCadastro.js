import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { debugLog } from "../utils/debug";
import { useClientesNovoEnderecos } from "./useClientesNovoEnderecos";

const STEPS = [
  { number: 1, title: "Informacoes do cliente" },
  { number: 2, title: "Contatos" },
  { number: 3, title: "Endereco" },
  { number: 4, title: "Informacoes complementares" },
  { number: 5, title: "Animais" },
  { number: 6, title: "Financeiro" },
];

function buildNovoClienteFormData(tipoCadastro, tipoPessoa) {
  return {
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
    endereco_entrega: "",
    endereco_entrega_2: "",
    is_entregador: false,
    entregador_ativo: true,
    entregador_padrao: false,
    tipo_vinculo_entrega: "",
    controla_rh: false,
    gera_conta_pagar_custo_entrega: false,
    media_entregas_configurada: "",
    custo_rh_ajustado: "",
    modelo_custo_entrega: "",
    taxa_fixa_entrega: "",
    valor_por_km_entrega: "",
    moto_propria: true,
    tipo_acerto_entrega: "",
    dia_semana_acerto: "",
    dia_mes_acerto: "",
    is_terceirizado: false,
    recebe_repasse: false,
    gera_conta_pagar: false,
    observacoes: "",
    tags: "",
  };
}

function buildClienteFormData(cliente) {
  return {
    tipo_cadastro: cliente.tipo_cadastro || "cliente",
    tipo_pessoa: cliente.tipo_pessoa || "PF",
    nome: cliente.nome || "",
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
    is_entregador: cliente.is_entregador || false,
    entregador_ativo:
      cliente.entregador_ativo !== undefined ? cliente.entregador_ativo : true,
    entregador_padrao: cliente.entregador_padrao || false,
    tipo_vinculo_entrega: cliente.tipo_vinculo_entrega || "",
    controla_rh: cliente.controla_rh || false,
    gera_conta_pagar_custo_entrega:
      cliente.gera_conta_pagar_custo_entrega || false,
    media_entregas_configurada: cliente.media_entregas_configurada || "",
    custo_rh_ajustado: cliente.custo_rh_ajustado || "",
    modelo_custo_entrega: cliente.modelo_custo_entrega || "",
    taxa_fixa_entrega: cliente.taxa_fixa_entrega || "",
    valor_por_km_entrega: cliente.valor_por_km_entrega || "",
    moto_propria:
      cliente.moto_propria !== undefined ? cliente.moto_propria : true,
    tipo_acerto_entrega: cliente.tipo_acerto_entrega || "",
    dia_semana_acerto: cliente.dia_semana_acerto || "",
    dia_mes_acerto: cliente.dia_mes_acerto || "",
    is_terceirizado: cliente.is_terceirizado || false,
    recebe_repasse: cliente.recebe_repasse || false,
    gera_conta_pagar: cliente.gera_conta_pagar || false,
    observacoes: cliente.observacoes || "",
    tags: "",
  };
}

export function useClientesNovoCadastro({
  tipoFiltro,
  clientes,
  loadClientes,
  onClienteCriado,
  error,
  setError,
}) {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [showModalImportacao, setShowModalImportacao] = useState(false);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] =
    useState(false);
  const [mostrarModalRemoverCredito, setMostrarModalRemoverCredito] =
    useState(false);
  const [refreshKeyCredito, setRefreshKeyCredito] = useState(0);
  const [editingCliente, setEditingCliente] = useState(null);
  const [loadingCep, setLoadingCep] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [pets, setPets] = useState([]);
  const [cepError, setCepError] = useState("");
  const [clienteDuplicado, setClienteDuplicado] = useState(null);
  const [showDuplicadoWarning, setShowDuplicadoWarning] = useState(false);
  const [showConfirmacaoRemocao, setShowConfirmacaoRemocao] = useState(false);
  const [highlightedPetId, setHighlightedPetId] = useState(null);
  const [resumoFinanceiro, setResumoFinanceiro] = useState(null);
  const [loadingResumo, setLoadingResumo] = useState(false);
  const [saldoCampanhas, setSaldoCampanhas] = useState(null);
  const [loadingCadastro, setLoadingCadastro] = useState(false);
  const [formData, setFormData] = useState(
    buildNovoClienteFormData("cliente", "PF"),
  );

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

  const buscarCep = async (cep) => {
    const cepLimpo = cep.replace(/\D/g, "");
    if (cepLimpo.length !== 8) return;

    setLoadingCep(true);
    setCepError("");
    setError("");

    try {
      const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
      const data = await response.json();

      if (data.erro) {
        setCepError("CEP nao encontrado");
        return;
      }

      setFormData((prev) => ({
        ...prev,
        endereco: data.logradouro || "",
        bairro: data.bairro || "",
        cidade: data.localidade || "",
        estado: data.uf || "",
        cep,
      }));
    } catch (err) {
      console.error("Erro ao buscar CEP:", err);
    } finally {
      setLoadingCep(false);
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

  const loadResumoFinanceiro = async (clienteId) => {
    if (!clienteId) return;

    try {
      setLoadingResumo(true);
      const response = await api.get(`/financeiro/cliente/${clienteId}/resumo`);
      setResumoFinanceiro(response.data.resumo);
    } catch (err) {
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

      debugLog("Cliente carregado do backend:", {
        id: cliente.id,
        nome: cliente.nome,
        is_entregador: cliente.is_entregador,
        entregador_padrao: cliente.entregador_padrao,
        entregador_padrao_tipo: typeof cliente.entregador_padrao,
      });

      setFormData(buildClienteFormData(cliente));
      setPets(cliente.pets || []);
      setEnderecosAdicionais(cliente.enderecos_adicionais || []);
      loadResumoFinanceiro(cliente.id);
      loadSaldoCampanhas(cliente.id);
      setCurrentStep(petIdToEdit ? 5 : 1);
    } else {
      const tipoCadastro =
        tipo || (tipoFiltro === "todos" ? "cliente" : tipoFiltro);
      const tipoPessoa = tipoCadastro === "fornecedor" ? "PJ" : "PF";

      setEditingCliente(null);
      setFormData(buildNovoClienteFormData(tipoCadastro, tipoPessoa));
      setPets([]);
      setEnderecosAdicionais([]);
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
    setResumoFinanceiro(null);
    setSaldoCampanhas(null);
    setCepError("");
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

      if (!params.toString()) {
        return false;
      }

      const response = await api.get(
        `/clientes/verificar-duplicata/campo?${params.toString()}`,
      );

      if (response.data.duplicado) {
        setClienteDuplicado(response.data);
        setShowDuplicadoWarning(true);
        return true;
      }

      return false;
    } catch (err) {
      console.error("Erro ao verificar duplicata:", err);
      return false;
    }
  };

  const nextStep = async () => {
    if (currentStep >= 6) return;

    setError("");
    setCepError("");

    if (currentStep === 1 || currentStep === 2) {
      const temDuplicata = await verificarDuplicata();
      if (temDuplicata) {
        return;
      }
    }

    setCurrentStep((step) => step + 1);
  };

  const prevStep = () => {
    if (currentStep <= 1) return;
    setError("");
    setCepError("");
    setCurrentStep((step) => step - 1);
  };

  const isDocumentoUnico = (campo) => ["cpf", "cnpj", "crmv"].includes(campo);

  const continuarMesmoDuplicado = () => {
    setShowConfirmacaoRemocao(true);
  };

  const confirmarRemocaoEContinuar = async () => {
    try {
      setLoadingCadastro(true);

      const proximoCodigo =
        editingCliente?.codigo ||
        (clientes.length > 0
          ? Math.max(...clientes.map((c) => c.codigo)) + 1
          : 1);

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

      setShowConfirmacaoRemocao(false);
      setShowDuplicadoWarning(false);
      setClienteDuplicado(null);
      setCurrentStep((step) => step + 1);
    } catch (err) {
      setError(err.response?.data?.detail || "Erro ao remover campo duplicado");
    } finally {
      setLoadingCadastro(false);
    }
  };

  const cancelarRemocao = () => {
    setShowConfirmacaoRemocao(false);
  };

  const irParaClienteExistente = () => {
    closeModal();

    const elemento = document.getElementById(
      `cliente-${clienteDuplicado.cliente.id}`,
    );

    if (!elemento) {
      return;
    }

    elemento.scrollIntoView({ behavior: "smooth", block: "center" });
    elemento.classList.add("ring-4", "ring-yellow-400");
    setTimeout(() => {
      elemento.classList.remove("ring-4", "ring-yellow-400");
    }, 3000);
  };

  const editarClienteExistente = () => {
    const clienteParaEditar = clientes.find(
      (cliente) => cliente.id === clienteDuplicado.cliente.id,
    );

    if (!clienteParaEditar) {
      return;
    }

    setShowDuplicadoWarning(false);
    setClienteDuplicado(null);
    setShowConfirmacaoRemocao(false);
    openModal(clienteParaEditar);
  };

  const handleSubmitFinal = async () => {
    setError("");

    try {
      const isEdicao = Boolean(editingCliente);
      const errosValidacao = [];

      if (!formData.nome || formData.nome.trim() === "") {
        errosValidacao.push("Nome");
      }

      if (formData.tipo_pessoa === "PJ") {
        if (!formData.cnpj || formData.cnpj.trim() === "") {
          errosValidacao.push("CNPJ");
        }
        if (!formData.razao_social || formData.razao_social.trim() === "") {
          errosValidacao.push("Razao Social");
        }
      }

      if (errosValidacao.length > 0) {
        const mensagem =
          "Faltam os seguintes campos obrigatorios:\n\n" +
          errosValidacao.map((campo) => `- ${campo}`).join("\n");
        alert(mensagem);
        setError(mensagem);
        return;
      }

      if (formData.is_entregador) {
        if (!formData.tipo_acerto_entrega) {
          alert(
            "Informe o tipo de acerto do entregador (semanal, quinzenal ou mensal)",
          );
          return;
        }

        if (
          formData.tipo_acerto_entrega === "semanal" &&
          !formData.dia_semana_acerto
        ) {
          alert("Informe o dia da semana para o acerto semanal");
          return;
        }

        if (
          formData.tipo_acerto_entrega === "mensal" &&
          !formData.dia_mes_acerto
        ) {
          alert("Informe o dia do mes para o acerto mensal");
          return;
        }

        if (formData.tipo_acerto_entrega === "mensal") {
          const dia = parseInt(formData.dia_mes_acerto, 10);
          if (dia < 1 || dia > 28) {
            alert("O dia do mes deve estar entre 1 e 28");
            return;
          }
        }
      }

      const { celular_whatsapp, tags, ...clienteData } = formData;

      if (clienteData.is_entregador) {
        if (clienteData.tipo_cadastro === "funcionario") {
          clienteData.tipo_vinculo_entrega = "funcionario";
          clienteData.is_terceirizado = false;
        } else if (clienteData.tipo_cadastro === "fornecedor") {
          clienteData.is_terceirizado = true;
          clienteData.tipo_vinculo_entrega = "terceirizado";
        }
      }

      clienteData.enderecos_adicionais =
        enderecosAdicionais.length > 0 ? enderecosAdicionais : null;

      Object.keys(clienteData).forEach((key) => {
        if (clienteData[key] === "") {
          clienteData[key] = null;
        }
      });

      if (clienteData.tipo_cadastro === "todos") {
        clienteData.tipo_cadastro = "cliente";
      }

      let clienteId;
      let clienteSalvo = null;

      if (isEdicao) {
        const response = await api.put(`/clientes/${editingCliente.id}`, clienteData);
        clienteId = editingCliente.id;
        clienteSalvo = response.data;
      } else {
        const clienteResponse = await api.post("/clientes/", clienteData);
        clienteId = clienteResponse.data.id;
        clienteSalvo = clienteResponse.data;
      }

      for (const pet of pets) {
        const petId = pet.id;
        const petData = { ...pet };

        delete petData.id;
        delete petData.created_at;
        delete petData.updated_at;
        delete petData.cliente_id;
        delete petData.user_id;
        delete petData.ativo;
        delete petData.codigo;

        Object.keys(petData).forEach((key) => {
          if (petData[key] === "") {
            petData[key] = null;
          }
        });

        if (petData.peso !== null && petData.peso !== undefined) {
          petData.peso = parseFloat(petData.peso) || null;
        }

        if (petId) {
          debugLog(`Atualizando pet ${petId}:`, petData);
          await api.put(`/clientes/pets/${petId}`, petData);
        } else {
          debugLog("Criando novo pet:", petData);
          await api.post(`/clientes/${clienteId}/pets`, petData);
        }
      }

      closeModal();

      if (!isEdicao && typeof onClienteCriado === "function") {
        await Promise.resolve(onClienteCriado(clienteSalvo));
      } else {
        await loadClientes();
      }
    } catch (err) {
      const errorDetails = err.response?.data?.details;
      console.error("Erro completo:", err.response?.data);
      console.error("Detalhes de validacao:", errorDetails);

      const camposPtBr = {
        nome: "Nome",
        data_nascimento: "Data de Nascimento",
        cpf: "CPF",
        cnpj: "CNPJ",
        razao_social: "Razao Social",
        nome_fantasia: "Nome Fantasia",
        inscricao_estadual: "Inscricao Estadual",
        responsavel: "Responsavel",
        telefone: "Telefone",
        celular: "Celular",
        email: "E-mail",
        cep: "CEP",
        endereco: "Endereco",
        numero: "Numero",
        bairro: "Bairro",
        cidade: "Cidade",
        estado: "Estado",
        tipo_pessoa: "Tipo de Pessoa",
        tipo_cadastro: "Tipo de Cadastro",
        crmv: "CRMV",
        tipo_acerto_entrega: "Tipo de Acerto",
        dia_semana_acerto: "Dia da Semana para Acerto",
        dia_mes_acerto: "Dia do Mes para Acerto",
        tipo_vinculo_entrega: "Tipo de Vinculo",
      };

      let mensagemErro = "";

      if (errorDetails && Array.isArray(errorDetails)) {
        const camposFaltando = [];

        errorDetails.forEach((detail) => {
          const campo = detail.loc[detail.loc.length - 1];
          const nomeCampo = camposPtBr[campo] || campo;

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
            "Faltam os seguintes campos obrigatorios:\n\n" +
            camposFaltando.map((campo) => `- ${campo}`).join("\n");
        }
      }

      const errorMessage =
        mensagemErro || err.response?.data?.message || "Erro ao salvar cliente";
      setError(errorMessage);

      if (mensagemErro) {
        alert(mensagemErro);
      }
    }
  };

  const modalsLayerProps = useMemo(
    () => ({
      showModal,
      editingCliente,
      formData,
      closeModal,
      steps: STEPS,
      currentStep,
      setCurrentStep,
      error,
      showDuplicadoWarning,
      clienteDuplicado,
      clientes,
      isDocumentoUnico,
      loading: loadingCadastro,
      cancelarRemocao,
      confirmarRemocaoEContinuar,
      continuarMesmoDuplicado,
      editarClienteExistente,
      irParaClienteExistente,
      showConfirmacaoRemocao,
      setShowDuplicadoWarning,
      setClienteDuplicado,
      setFormData,
      buscarCep,
      loadingCep,
      cepError,
      enderecosAdicionais,
      abrirModalEndereco,
      removerEndereco,
      pets,
      navigate,
      refreshKeyCredito,
      resumoFinanceiro,
      loadingResumo,
      saldoCampanhas,
      setMostrarModalAdicionarCredito,
      setMostrarModalRemoverCredito,
      prevStep,
      nextStep,
      handleSubmitFinal,
      mostrarFormEndereco,
      enderecoAtual,
      fecharModalEndereco,
      loadingCepEndereco,
      salvarEndereco,
      buscarCepModal,
      setEnderecoAtual,
      showModalImportacao,
      setShowModalImportacao,
      fetchClientes: loadClientes,
      mostrarModalAdicionarCredito,
      mostrarModalRemoverCredito,
      setEditingCliente,
      setRefreshKeyCredito,
      loadClientes,
    }),
    [
      abrirModalEndereco,
      buscarCep,
      buscarCepModal,
      cancelarRemocao,
      clienteDuplicado,
      clientes,
      closeModal,
      confirmarRemocaoEContinuar,
      continuarMesmoDuplicado,
      currentStep,
      editarClienteExistente,
      enderecosAdicionais,
      enderecoAtual,
      error,
      fecharModalEndereco,
      formData,
      handleSubmitFinal,
      irParaClienteExistente,
      loadClientes,
      loadingCadastro,
      loadingCep,
      loadingCepEndereco,
      loadingResumo,
      mostrarFormEndereco,
      mostrarModalAdicionarCredito,
      mostrarModalRemoverCredito,
      navigate,
      nextStep,
      pets,
      prevStep,
      refreshKeyCredito,
      removerEndereco,
      resumoFinanceiro,
      saldoCampanhas,
      salvarEndereco,
      setEnderecoAtual,
      setFormData,
      setShowDuplicadoWarning,
      showConfirmacaoRemocao,
      showDuplicadoWarning,
      showModal,
      showModalImportacao,
      onClienteCriado,
    ],
  );

  return {
    showModal,
    highlightedPetId,
    setHighlightedPetId,
    openModal,
    setShowModalImportacao,
    modalsLayerProps,
  };
}
