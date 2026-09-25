import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { AlertTriangle, DollarSign, ExternalLink, MapPin, PawPrint, Phone, User } from "lucide-react";
import { FiChevronLeft } from "react-icons/fi";
import api from "../api";
import { useModulos } from "../contexts/ModulosContext";
import EmptyState from "../components/ui/EmptyState";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import AbasNavegacao from "../components/v2/AbasNavegacao/AbasNavegacao";
import BotaoInteracao from "../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../components/v2/BotaoSalva/BotaoSalva";
import LinkPadrao from "../components/v2/LinkPadrao/LinkPadrao";
import ModalAdicionarCredito from "../components/ModalAdicionarCredito";
import ModalRemoverCredito from "../components/ModalRemoverCredito";
import ClientePessoaAlertasPdvSection from "../components/clientes/ClientePessoaAlertasPdvSection";
import ClientePessoaComplementaresTab from "../components/clientes/ClientePessoaComplementaresTab";
import ClientePessoaContatosTab from "../components/clientes/ClientePessoaContatosTab";
import ClientePessoaDadosGeraisTab from "../components/clientes/ClientePessoaDadosGeraisTab";
import ClientePessoaEnderecoModal from "../components/clientes/ClientePessoaEnderecoModal";
import ClientePessoaEnderecoTab from "../components/clientes/ClientePessoaEnderecoTab";
import ClientePessoaFinanceiroTab from "../components/clientes/ClientePessoaFinanceiroTab";
import { useClientesNovoEnderecos } from "../hooks/useClientesNovoEnderecos";
import { normalizeClienteAlertasPdv } from "../utils/clienteAlertasPdv";

function buildFormDataFromCliente(cliente) {
  return {
    tipo_cadastro: cliente.tipo_cadastro || "cliente",
    is_cliente: cliente.is_cliente || false,
    is_fornecedor: cliente.is_fornecedor || false,
    is_veterinario: cliente.is_veterinario || false,
    is_funcionario: cliente.is_funcionario || false,
    origem_cliente: cliente.origem_cliente ?? null,
    tipo_pessoa: cliente.tipo_pessoa || "PF",
    nome: cliente.nome || "",
    data_nascimento: cliente.data_nascimento ? String(cliente.data_nascimento).slice(0, 10) : "",
    cpf: cliente.cpf || "",
    email: cliente.email || "",
    telefone: cliente.telefone || "",
    celular: cliente.celular || "",
    celular_whatsapp: cliente.celular_whatsapp || false,
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

  if (formData.is_veterinario && (!formData.crmv || !formData.crmv.trim())) {
    erros.crmv = "Informe o CRMV.";
  }

  if (formData.is_cliente) {
    const digitos = `${formData.telefone || ""}${formData.celular || ""}`.replace(/\D/g, "");
    if (digitos.length < 10) erros.celular = "Informe telefone ou celular.";
  }

  if (
    !formData.is_cliente &&
    !formData.is_fornecedor &&
    !formData.is_veterinario &&
    !formData.is_funcionario
  ) {
    erros.tipos_cadastro = "Selecione ao menos um tipo de cadastro.";
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
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");

  const [cliente, setCliente] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [naoEncontrado, setNaoEncontrado] = useState(false);
  const [formData, setFormData] = useState(null);
  const [abaAtiva, setAbaAtiva] = useState(location.state?.abaInicial || "dados-gerais");
  const [salvando, setSalvando] = useState(false);

  const [resumoFinanceiro, setResumoFinanceiro] = useState(null);
  const [loadingResumo, setLoadingResumo] = useState(false);
  const [saldoCampanhas, setSaldoCampanhas] = useState(null);
  const [refreshKeyCredito, setRefreshKeyCredito] = useState(0);
  const [mostrarModalAdicionarCredito, setMostrarModalAdicionarCredito] = useState(false);
  const [mostrarModalRemoverCredito, setMostrarModalRemoverCredito] = useState(false);

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

  const principalTemDados = formData
    ? CAMPOS_ENDERECO_PRINCIPAL.some((campo) => formData[campo])
    : false;

  // Promove `entrada` (novo endereço ou um adicional existente) a principal. Se o principal atual
  // tiver dados, ele vira uma entrada normal na lista, com o tipo escolhido na confirmação — nunca
  // fica mais de um endereço marcado como principal ao mesmo tempo.
  const promoverAPrincipal = (entrada, tipoAntigoPrincipal) => {
    const principalAntigo = {
      tipo: tipoAntigoPrincipal,
      apelido: "",
      ...Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, formData[campo] || ""])),
    };

    setFormData((prev) => ({
      ...prev,
      ...Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, entrada[campo] || ""])),
    }));

    setEnderecosAdicionais((prev) => {
      let proximos = typeof entrada.index === "number" ? prev.filter((_, i) => i !== entrada.index) : [...prev];
      if (principalTemDados) {
        proximos = [...proximos, principalAntigo];
      }
      return proximos;
    });

    fecharModalEndereco();
    toast.success("Endereço principal atualizado.");
  };

  const confirmarEndereco = (tipoAntigoPrincipal) => {
    if (!enderecoAtual?.cep || !enderecoAtual?.endereco || !enderecoAtual?.cidade) {
      toast.error("Preencha pelo menos CEP, Endereço e Cidade.");
      return;
    }

    if (enderecoAtual.index === "principal") {
      setFormData((prev) => ({
        ...prev,
        ...Object.fromEntries(CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, enderecoAtual[campo]])),
      }));
      fecharModalEndereco();
      return;
    }

    if (enderecoAtual.tipo === "principal") {
      promoverAPrincipal(enderecoAtual, tipoAntigoPrincipal);
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

  const alertasPdvAtivosCount = (formData?.alertas_pdv || []).filter(
    (alerta) => alerta.ativo !== false,
  ).length;

  const abas = useMemo(
    () => [
      {
        id: "dados-gerais",
        label: "Dados gerais",
        icon: User,
        descricao: "Identificação e complementares",
        invalida: Boolean(
          erros.nome || erros.cnpj || erros.razao_social || erros.crmv || erros.tipos_cadastro,
        ),
      },
      {
        id: "contatos",
        label: "Contatos",
        icon: Phone,
        descricao: "Telefone, e-mail e observações",
        invalida: Boolean(erros.celular),
      },
      {
        id: "endereco",
        label: "Endereço",
        icon: MapPin,
        descricao: "Endereço principal e adicionais",
        invalida: false,
      },
      {
        id: "alertas-pdv",
        label: "Alertas do PDV",
        icon: AlertTriangle,
        descricao: "Mensagens automáticas ao atender esta pessoa",
        invalida: false,
        contador: alertasPdvAtivosCount,
      },
      {
        id: "financeiro",
        label: "Financeiro",
        icon: DollarSign,
        descricao: "Crédito, histórico e indicadores financeiros",
        invalida: false,
      },
    ],
    [erros, alertasPdvAtivosCount],
  );

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
      const { tags: _tags, ...clienteData } = formData;
      clienteData.alertas_pdv = normalizeClienteAlertasPdv(clienteData.alertas_pdv);

      if (clienteData.is_entregador) {
        if (clienteData.is_funcionario) {
          clienteData.tipo_vinculo_entrega = "funcionario";
          clienteData.is_terceirizado = false;
        } else if (clienteData.is_fornecedor) {
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
          <div className="flex items-center gap-2">
            <BotaoInteracao
              icon={PawPrint}
              tamanho="grande"
              onClick={() =>
                window.open(`/pets?cliente_id=${cliente.id}`, "_blank", "noopener,noreferrer")
              }
            >
              Gerenciar pets
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="sr-only"> (abre em nova aba)</span>
            </BotaoInteracao>
            <BotaoSalva onClick={salvar} loading={salvando} tamanho="grande">
              Salvar
            </BotaoSalva>
          </div>
        }
      />

      <Panel padding="none">
        <AbasNavegacao abas={abas} ativa={abaAtiva} onChange={setAbaAtiva} className="px-4" />
        <div className="p-4">
          {abaAtiva === "dados-gerais" ? (
            <div className="space-y-8">
              <ClientePessoaDadosGeraisTab erros={erros} formData={formData} setFormData={setFormData} />

              <div className="border-t border-slate-200 pt-6 dark:border-slate-700">
                <h3 className="mb-4 text-base font-semibold text-slate-900 dark:text-slate-100">
                  Complementares
                </h3>
                <ClientePessoaComplementaresTab formData={formData} setFormData={setFormData} />
              </div>
            </div>
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

          {abaAtiva === "alertas-pdv" ? (
            <ClientePessoaAlertasPdvSection formData={formData} setFormData={setFormData} />
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

      {enderecoAtual ? (
        <ClientePessoaEnderecoModal
          enderecoAtual={enderecoAtual}
          fecharModalEndereco={fecharModalEndereco}
          loadingCepEndereco={loadingCepEndereco}
          principalTemDados={principalTemDados}
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
