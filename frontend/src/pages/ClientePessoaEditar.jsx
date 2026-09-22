import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { DollarSign, MapPin, Phone, Settings, User } from "lucide-react";
import { FiChevronLeft } from "react-icons/fi";
import { PawPrint } from "lucide-react";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import { useModulos } from "../contexts/ModulosContext";
import EmptyState from "../components/ui/EmptyState";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import AbasNavegacao from "../components/v2/AbasNavegacao/AbasNavegacao";
import BotaoSalva from "../components/v2/BotaoSalva/BotaoSalva";
import LinkPadrao from "../components/v2/LinkPadrao/LinkPadrao";
import ModalAdicionarCredito from "../components/ModalAdicionarCredito";
import ModalRemoverCredito from "../components/ModalRemoverCredito";
import UsuarioAcessoInicialModal from "../components/usuarios/UsuarioAcessoInicialModal";
import ClientePessoaAnimaisTab from "../components/clientes/ClientePessoaAnimaisTab";
import ClientePessoaComplementaresTab from "../components/clientes/ClientePessoaComplementaresTab";
import ClientePessoaContatosTab from "../components/clientes/ClientePessoaContatosTab";
import ClientePessoaDadosGeraisTab from "../components/clientes/ClientePessoaDadosGeraisTab";
import ClientePessoaEnderecoModal from "../components/clientes/ClientePessoaEnderecoModal";
import ClientePessoaEnderecoTab from "../components/clientes/ClientePessoaEnderecoTab";
import ClientePessoaFinanceiroTab from "../components/clientes/ClientePessoaFinanceiroTab";
import { useClientesNovoEnderecos } from "../hooks/useClientesNovoEnderecos";
import { canManageAppAccessProfiles } from "../utils/appAccessProfiles";
import { normalizeClienteAlertasPdv } from "../utils/clienteAlertasPdv";
import { normalizePessoaAppLogin } from "../utils/pessoaAppLogin";
import {
  buildInitialAccessCredentials,
  resolveTenantLoginReference,
} from "../utils/usuarioAcessoInicial";

function buildFormDataFromCliente(cliente) {
  return {
    tipo_cadastro: cliente.tipo_cadastro || "cliente",
    origem_cliente: cliente.origem_cliente ?? null,
    tipo_pessoa: cliente.tipo_pessoa || "PF",
    nome: cliente.nome || "",
    data_nascimento: cliente.data_nascimento ? String(cliente.data_nascimento).slice(0, 10) : "",
    cpf: cliente.cpf || "",
    email: cliente.email || "",
    telefone: cliente.telefone || "",
    celular: cliente.celular || "",
    celular_whatsapp: true,
    auth_user_id: cliente.auth_user_id || null,
    app_login: null,
    app_access_profiles: cliente.app_access_profiles || [],
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
    codigo_municipio: cliente.codigo_municipio || "",
    endereco_entrega: cliente.endereco_entrega || "",
    endereco_entrega_2: cliente.endereco_entrega_2 || "",
    is_entregador: cliente.is_entregador || false,
    entregador_ativo: cliente.entregador_ativo !== undefined ? cliente.entregador_ativo : true,
    entregador_padrao: cliente.entregador_padrao || false,
    tipo_vinculo_entrega: cliente.tipo_vinculo_entrega || "",
    controla_rh: cliente.controla_rh || false,
    gera_conta_pagar_custo_entrega: cliente.gera_conta_pagar_custo_entrega || false,
    media_entregas_configurada: cliente.media_entregas_configurada || "",
    custo_rh_ajustado: cliente.custo_rh_ajustado || "",
    modelo_custo_entrega: cliente.modelo_custo_entrega || "",
    taxa_fixa_entrega: cliente.taxa_fixa_entrega || "",
    valor_por_km_entrega: cliente.valor_por_km_entrega || "",
    moto_propria: cliente.moto_propria !== undefined ? cliente.moto_propria : true,
    tipo_acerto_entrega: cliente.tipo_acerto_entrega || "",
    dia_semana_acerto: cliente.dia_semana_acerto || "",
    dia_mes_acerto: cliente.dia_mes_acerto || "",
    is_terceirizado: cliente.is_terceirizado || false,
    recebe_repasse: cliente.recebe_repasse || false,
    gera_conta_pagar: cliente.gera_conta_pagar || false,
    observacoes: cliente.observacoes || "",
    alertas_pdv: normalizeClienteAlertasPdv(cliente.alertas_pdv),
    tags: "",
  };
}

function validarFormData(formData) {
  const erros = {};
  if (!formData.nome || !formData.nome.trim()) erros.nome = "Informe o nome.";

  if (formData.tipo_pessoa === "PJ") {
    if (!formData.cnpj || !formData.cnpj.trim()) erros.cnpj = "Informe o CNPJ.";
    if (!formData.razao_social || !formData.razao_social.trim()) {
      erros.razao_social = "Informe a razão social.";
    }
  }

  if (formData.tipo_cadastro === "veterinario" && (!formData.crmv || !formData.crmv.trim())) {
    erros.crmv = "Informe o CRMV.";
  }

  if (formData.tipo_cadastro === "cliente") {
    const digitos = `${formData.telefone || ""}${formData.celular || ""}`.replace(/\D/g, "");
    if (digitos.length < 10) erros.celular = "Informe telefone ou celular.";
  }

  return erros;
}

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

function formatarDataHoraCadastro(valor) {
  if (!valor) return "Data não registrada";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "Data não registrada";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data);
}

export default function ClientePessoaEditar() {
  const { clienteId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const canManageAppAccess = canManageAppAccessProfiles(user);
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");

  const [cliente, setCliente] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [naoEncontrado, setNaoEncontrado] = useState(false);
  const [formData, setFormData] = useState(null);
  const [pets, setPets] = useState([]);
  const [abaAtiva, setAbaAtiva] = useState(location.state?.abaInicial || "dados-gerais");
  const [salvando, setSalvando] = useState(false);

  const [usuariosAcessoApp, setUsuariosAcessoApp] = useState([]);
  const [rolesAcessoApp, setRolesAcessoApp] = useState([]);
  const [loadingUsuariosAcessoApp, setLoadingUsuariosAcessoApp] = useState(false);
  const [resumoFinanceiro, setResumoFinanceiro] = useState(null);
  const [loadingResumo, setLoadingResumo] = useState(false);
  const [saldoCampanhas, setSaldoCampanhas] = useState(null);
  const [refreshKeyCredito, setRefreshKeyCredito] = useState(0);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] = useState(false);
  const [mostrarModalRemoverCredito, setMostrarModalRemoverCredito] = useState(false);
  const [initialAccessCredentials, setInitialAccessCredentials] = useState(null);

  const tenantLoginReference = resolveTenantLoginReference(
    user,
    typeof window === "undefined" ? null : window.localStorage.getItem("selectedTenant"),
  );

  const {
    enderecosAdicionais,
    setEnderecosAdicionais,
    enderecoAtual,
    setEnderecoAtual,
    loadingCepEndereco,
    abrirModalEndereco,
    fecharModalEndereco,
    buscarCepModal,
    salvarEndereco,
    removerEndereco,
  } = useClientesNovoEnderecos();

  const carregar = useCallback(async () => {
    setCarregando(true);
    setNaoEncontrado(false);
    try {
      const { data } = await api.get(`/clientes/${clienteId}`);
      setCliente(data);
      setFormData(buildFormDataFromCliente(data));
      setPets(data.pets || []);
      setEnderecosAdicionais(data.enderecos_adicionais || []);
    } catch (error) {
      if (error.response?.status === 404) {
        setNaoEncontrado(true);
      } else {
        toast.error(mensagemErro(error, "Não foi possível carregar esta pessoa."));
      }
    } finally {
      setCarregando(false);
    }
  }, [clienteId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    if (!canManageAppAccess) return;
    setLoadingUsuariosAcessoApp(true);
    api
      .get("/clientes/acessos-app/usuarios", { params: { cliente_id: clienteId } })
      .then((response) => setUsuariosAcessoApp(response.data || []))
      .catch(() => setUsuariosAcessoApp([]))
      .finally(() => setLoadingUsuariosAcessoApp(false));
    api
      .get("/roles")
      .then((response) => setRolesAcessoApp(response.data || []))
      .catch(() => setRolesAcessoApp([]));
  }, [canManageAppAccess, clienteId]);

  useEffect(() => {
    setLoadingResumo(true);
    api
      .get(`/financeiro/cliente/${clienteId}/resumo`)
      .then((response) => setResumoFinanceiro(response.data.resumo))
      .catch((error) => {
        if (error.response?.status !== 404) {
          console.error("Erro ao carregar resumo financeiro:", error);
        }
        setResumoFinanceiro(null);
      })
      .finally(() => setLoadingResumo(false));
  }, [clienteId, refreshKeyCredito]);

  useEffect(() => {
    if (!moduloCampanhasAtivo) {
      setSaldoCampanhas(null);
      return;
    }
    api
      .get(`/campanhas/clientes/${clienteId}/saldo`)
      .then((response) => setSaldoCampanhas(response.data))
      .catch(() => setSaldoCampanhas(null));
  }, [clienteId, moduloCampanhasAtivo]);

  const CAMPOS_ENDERECO_PRINCIPAL = [
    "cep",
    "endereco",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "estado",
  ];

  const abrirEndereco = (alvo) => {
    if (alvo === "principal") {
      setEnderecoAtual({
        tipo: "principal",
        apelido: "",
        ...Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, formData[campo] || ""])),
        index: "principal",
      });
      return;
    }
    abrirModalEndereco(alvo);
  };

  const confirmarEndereco = () => {
    if (enderecoAtual?.index === "principal") {
      if (!enderecoAtual.cep || !enderecoAtual.endereco || !enderecoAtual.cidade) {
        toast.error("Preencha pelo menos CEP, Endereço e Cidade.");
        return;
      }
      setFormData((prev) => ({
        ...prev,
        ...Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, enderecoAtual[campo]])),
      }));
      fecharModalEndereco();
      return;
    }
    salvarEndereco();
  };

  const excluirEndereco = (alvo) => {
    if (alvo === "principal") {
      setFormData((prev) => ({
        ...prev,
        ...Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, ""])),
      }));
      return;
    }
    removerEndereco(alvo);
  };

  const erros = useMemo(() => (formData ? validarFormData(formData) : {}), [formData]);

  const abas = useMemo(() => {
    const todasAbas = [
      {
        id: "dados-gerais",
        label: "Dados gerais",
        icon: User,
        descricao: "Identificação, documento e tipo de cadastro",
        invalida: Boolean(erros.nome || erros.cnpj || erros.razao_social || erros.crmv),
      },
      {
        id: "contatos",
        label: "Contatos",
        icon: Phone,
        descricao: "Telefone, celular e e-mail",
        invalida: Boolean(erros.celular),
      },
      {
        id: "endereco",
        label: "Endereço",
        icon: MapPin,
        descricao: "Endereço principal e endereços adicionais",
        invalida: false,
      },
      {
        id: "complementares",
        label: "Complementares",
        icon: Settings,
        descricao: "Entrega, parceiro, alertas do PDV e acesso ao app",
        invalida: false,
      },
      {
        id: "animais",
        label: "Animais",
        icon: PawPrint,
        descricao: "Pets vinculados a esta pessoa",
        invalida: false,
      },
      {
        id: "financeiro",
        label: "Financeiro",
        icon: DollarSign,
        descricao: "Crédito, histórico e indicadores financeiros",
        invalida: false,
      },
    ];

    if (formData?.tipo_cadastro === "veterinario") {
      return todasAbas.filter((aba) => ["dados-gerais", "contatos", "endereco", "complementares"].includes(aba.id));
    }
    return todasAbas;
  }, [erros, formData?.tipo_cadastro]);

  useEffect(() => {
    if (!abas.some((aba) => aba.id === abaAtiva)) {
      setAbaAtiva(abas[0]?.id || "dados-gerais");
    }
  }, [abas, abaAtiva]);

  async function salvar() {
    if (Object.keys(erros).length > 0) {
      setAbaAtiva((atual) => {
        const abaComErro = abas.find((aba) => aba.invalida);
        return abaComErro ? abaComErro.id : atual;
      });
      toast.error("Corrija os campos destacados antes de salvar.");
      return;
    }

    setSalvando(true);
    try {
      const appLoginNovo = formData.app_login;
      const { celular_whatsapp: _celularWhatsapp, tags: _tags, ...clienteData } = formData;
      clienteData.alertas_pdv = normalizeClienteAlertasPdv(clienteData.alertas_pdv);
      clienteData.app_login = normalizePessoaAppLogin(clienteData.app_login);

      if (!canManageAppAccess) {
        delete clienteData.auth_user_id;
        delete clienteData.app_login;
        delete clienteData.app_access_profiles;
      }

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
        if (clienteData[key] === "") clienteData[key] = null;
      });

      const { data: clienteSalvo } = await api.put(`/clientes/${clienteId}`, clienteData);
      setCliente(clienteSalvo);
      setFormData(buildFormDataFromCliente(clienteSalvo));

      const credenciais = buildInitialAccessCredentials({
        tenant: tenantLoginReference,
        username: appLoginNovo?.username,
        password: appLoginNovo?.password,
        personName: clienteSalvo?.nome || formData.nome,
      });
      if (credenciais) setInitialAccessCredentials(credenciais);

      toast.success("Alterações salvas.");
    } catch (error) {
      const errorDetails = error.response?.data?.details;
      let mensagem = "";
      if (errorDetails && Array.isArray(errorDetails)) {
        const camposFaltando = errorDetails
          .map((detail) => detail.msg)
          .filter(Boolean);
        if (camposFaltando.length > 0) {
          mensagem = camposFaltando.join(" · ");
        }
      }
      toast.error(mensagem || mensagemErro(error, "Não foi possível salvar as alterações."));
    } finally {
      setSalvando(false);
    }
  }

  if (carregando) {
    return <LoadingState label="Carregando cadastro..." />;
  }

  if (naoEncontrado || !cliente || !formData) {
    return (
      <div className="space-y-6 p-6">
        <LinkPadrao to={location.state?.from || "/clientes"}>
          <FiChevronLeft aria-hidden="true" />
          Voltar para Pessoas
        </LinkPadrao>
        <EmptyState title="Pessoa não encontrada" description="Este cadastro pode ter sido removido." />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <LinkPadrao to={location.state?.from || "/clientes"}>
        <FiChevronLeft aria-hidden="true" />
        Voltar para Pessoas
      </LinkPadrao>

      <PageHeader
        icon={User}
        title={cliente.nome}
        subtitle={
          <>
            Código {cliente.codigo || cliente.id} · Editando cadastro · Criado em{" "}
            {formatarDataHoraCadastro(cliente.created_at)} · Criado por{" "}
            {cliente.criado_por_nome || cliente.criado_por_email || "Usuário não registrado"}
          </>
        }
        actions={
          <BotaoSalva onClick={salvar} loading={salvando} tamanho="grande">
            Salvar
          </BotaoSalva>
        }
      />

      <Panel padding="none">
        <AbasNavegacao abas={abas} ativa={abaAtiva} onChange={setAbaAtiva} className="px-4" />
        <div className="p-4">
          {abaAtiva === "dados-gerais" ? (
            <ClientePessoaDadosGeraisTab erros={erros} formData={formData} setFormData={setFormData} />
          ) : null}

          {abaAtiva === "contatos" ? (
            <ClientePessoaContatosTab erros={erros} formData={formData} setFormData={setFormData} />
          ) : null}

          {abaAtiva === "endereco" ? (
            <ClientePessoaEnderecoTab
              abrirModalEndereco={abrirEndereco}
              enderecosAdicionais={enderecosAdicionais}
              formData={formData}
              removerEndereco={excluirEndereco}
            />
          ) : null}

          {abaAtiva === "complementares" ? (
            <ClientePessoaComplementaresTab
              formData={formData}
              loadingUsuariosAcessoApp={loadingUsuariosAcessoApp}
              rolesAcessoApp={rolesAcessoApp}
              setFormData={setFormData}
              usuariosAcessoApp={usuariosAcessoApp}
            />
          ) : null}

          {abaAtiva === "animais" ? (
            <ClientePessoaAnimaisTab cliente={cliente} navigate={navigate} pets={pets} />
          ) : null}

          {abaAtiva === "financeiro" ? (
            <ClientePessoaFinanceiroTab
              cliente={cliente}
              loadingResumo={loadingResumo}
              navigate={navigate}
              refreshKeyCredito={refreshKeyCredito}
              resumoFinanceiro={resumoFinanceiro}
              saldoCampanhas={saldoCampanhas}
              setMostrarModalAdicionarCredito={setMostrarModalAdicionarCredito}
              setMostrarModalRemoverCredito={setMostrarModalRemoverCredito}
            />
          ) : null}
        </div>
      </Panel>

      <UsuarioAcessoInicialModal
        credentials={initialAccessCredentials}
        onClose={() => setInitialAccessCredentials(null)}
      />

      {enderecoAtual ? (
        <ClientePessoaEnderecoModal
          enderecoAtual={enderecoAtual}
          fecharModalEndereco={fecharModalEndereco}
          loadingCepEndereco={loadingCepEndereco}
          salvarEndereco={confirmarEndereco}
          buscarCepModal={buscarCepModal}
          setEnderecoAtual={setEnderecoAtual}
        />
      ) : null}

      {mostrarModalAdicionarCredito ? (
        <ModalAdicionarCredito
          cliente={cliente}
          onConfirmar={(novoSaldo) => {
            setCliente((prev) => ({ ...prev, credito: novoSaldo }));
            setRefreshKeyCredito((k) => k + 1);
          }}
          onClose={() => setMostrarModalAdicionarCredito(false)}
        />
      ) : null}

      {mostrarModalRemoverCredito ? (
        <ModalRemoverCredito
          cliente={cliente}
          onConfirmar={(novoSaldo) => {
            setCliente((prev) => ({ ...prev, credito: novoSaldo }));
            setRefreshKeyCredito((k) => k + 1);
          }}
          onClose={() => setMostrarModalRemoverCredito(false)}
        />
      ) : null}
    </div>
  );
}
