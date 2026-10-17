import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { AlertTriangle, DollarSign, MapPin, Phone, User } from "lucide-react";
import api from "../../api";
import { useModulos } from "../../contexts/ModulosContext";
import AbasNavegacao from "../v2/AbasNavegacao/AbasNavegacao";
import ModalAdicionarCredito from "../ModalAdicionarCredito";
import ModalRemoverCredito from "../ModalRemoverCredito";
import { useClientesNovoEnderecos } from "../../hooks/useClientesNovoEnderecos";
import { normalizeClienteAlertasPdv } from "../../utils/clienteAlertasPdv";
import ClientePessoaAlertasPdvSection from "./ClientePessoaAlertasPdvSection";
import ClientePessoaComplementaresTab from "./ClientePessoaComplementaresTab";
import ClientePessoaContatosTab from "./ClientePessoaContatosTab";
import ClientePessoaDadosGeraisTab from "./ClientePessoaDadosGeraisTab";
import ClientePessoaEnderecoModal from "./ClientePessoaEnderecoModal";
import ClientePessoaEnderecoTab from "./ClientePessoaEnderecoTab";
import ClientePessoaFinanceiroTab from "./ClientePessoaFinanceiroTab";
import ClientePessoaHistoricoPanel from "./ClientePessoaHistoricoPanel";

const CAMPOS_ENDERECO_PRINCIPAL = [
  "cep",
  "endereco",
  "numero",
  "complemento",
  "bairro",
  "cidade",
  "estado",
];

// Mapeia o `loc` que o backend devolve num erro de validação (ex.: ["body", "crmv"]) pra
// aba onde o campo mora — é o que permite trocar pra aba certa automaticamente quando o
// erro só aparece no servidor (regra que o formulário local não previu).
const CAMPO_PARA_ABA = {
  tipos_cadastro: "dados-gerais",
  tipo_pessoa: "dados-gerais",
  nome: "dados-gerais",
  cpf: "dados-gerais",
  cnpj: "dados-gerais",
  razao_social: "dados-gerais",
  nome_fantasia: "dados-gerais",
  inscricao_estadual: "dados-gerais",
  responsavel: "dados-gerais",
  crmv: "dados-gerais",
  origem_cliente: "dados-gerais",
  data_nascimento: "dados-gerais",
  celular: "contatos",
  telefone: "contatos",
  email: "contatos",
  observacoes: "contatos",
  contatos_adicionais: "contatos",
  cep: "endereco",
  endereco: "endereco",
  numero: "endereco",
  complemento: "endereco",
  bairro: "endereco",
  cidade: "endereco",
  estado: "endereco",
  codigo_municipio: "endereco",
  alertas_pdv: "alertas-pdv",
};

function buildFormDataNovo() {
  return {
    is_cliente: false,
    is_fornecedor: false,
    is_veterinario: false,
    is_funcionario: false,
    origem_cliente: null,
    tipo_pessoa: "PF",
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
    codigo_municipio: "",
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
    alertas_pdv: [],
    contatos_adicionais: [],
    tags: "",
  };
}

function buildFormDataFromCliente(cliente) {
  return {
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
    contatos_adicionais: (cliente.contatos_adicionais || []).map(({ numero, vinculo }) => ({
      numero,
      vinculo,
    })),
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

  // Mesma regra do backend (_validar_numero_endereco_cliente) checada aqui também, pra
  // não deixar o usuário só descobrir isso depois de tentar salvar.
  if ((formData.cep || formData.endereco || formData.bairro) && !(formData.numero || "").trim()) {
    erros.numero = "Informe o número do endereço. Se não houver, use S/N ou sem número.";
  }

  const numerosVistos = new Set(
    [formData.celular, formData.telefone]
      .map((numero) => String(numero || "").replace(/\D/g, ""))
      .filter(Boolean),
  );
  const errosContatos = {};
  (formData.contatos_adicionais || []).forEach((contato, index) => {
    const numero = String(contato.numero || "").trim();
    const vinculo = String(contato.vinculo || "").trim();
    if (!numero && !vinculo) return; // linha recém-adicionada, ainda vazia

    const erroItem = {};
    const digitos = numero.replace(/\D/g, "");
    if (digitos.length !== 11) {
      erroItem.numero = "Informe um celular com DDD (11 dígitos).";
    } else if (numerosVistos.has(digitos)) {
      erroItem.numero = "Esse número já está em outro contato desta pessoa.";
    } else {
      numerosVistos.add(digitos);
    }
    if (!vinculo) erroItem.vinculo = "Informe o vínculo (mãe, irmã...).";

    if (Object.keys(erroItem).length > 0) errosContatos[index] = erroItem;
  });
  if (Object.keys(errosContatos).length > 0) {
    erros.contatos_adicionais = errosContatos;
  }

  return erros;
}

// Converte os erros que o backend devolve (`details`: [{loc, msg}, ...], já com a
// mensagem real do validador desde a correção do sanitizador) num mapa por campo,
// pra reaproveitar o mesmo mecanismo visual (`erros.campo`) que já pinta os inputs
// de vermelho — e descobre a primeira aba afetada, pra trocar pra ela sozinho.
function mapearErrosServidor(details) {
  const errosPorCampo = {};
  let primeiraAba = null;

  for (const detalhe of details || []) {
    const loc = Array.isArray(detalhe.loc) ? detalhe.loc : [];
    const campoRaiz = loc[1];
    if (!campoRaiz) continue;

    if (campoRaiz === "contatos_adicionais" && typeof loc[2] === "number") {
      const index = loc[2];
      const subcampo = loc[3];
      errosPorCampo.contatos_adicionais = errosPorCampo.contatos_adicionais || {};
      errosPorCampo.contatos_adicionais[index] = {
        ...errosPorCampo.contatos_adicionais[index],
        [subcampo || "numero"]: detalhe.msg,
      };
    } else {
      errosPorCampo[campoRaiz] = detalhe.msg;
    }

    const aba = CAMPO_PARA_ABA[campoRaiz];
    if (aba && !primeiraAba) primeiraAba = aba;
  }

  return { errosPorCampo, primeiraAba };
}

/**
 * Corpo reutilizável do cadastro de Pessoa (Cliente/Fornecedor/Veterinário/Funcionário):
 * abas, validação e salvar. Usado tanto pela página de edição completa
 * (`ClientePessoaEditar.jsx`, que monta isto dentro da própria casca de página) quanto
 * pela modal única de cadastro rápido (`PessoaFormularioModal.jsx`) — o mesmo formulário,
 * só muda onde ele é exibido.
 */
export default function PessoaFormulario({
  abaInicial = "dados-gerais",
  formId = "pessoa-formulario",
  onSalvandoChange,
  onSalvo,
  prefill,
  pessoa,
}) {
  const navigate = useNavigate();
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");

  const [formData, setFormData] = useState(() => {
    const base = pessoa ? buildFormDataFromCliente(pessoa) : buildFormDataNovo();
    return prefill ? { ...base, ...prefill } : base;
  });
  const [pessoaAtual, setPessoaAtual] = useState(pessoa || null);
  const [abaAtiva, setAbaAtiva] = useState(abaInicial);
  const [tocados, setTocados] = useState({});
  const [salvando, setSalvando] = useState(false);
  const [errosServidor, setErrosServidor] = useState({});

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

  useEffect(() => {
    setPessoaAtual(pessoa || null);
    setEnderecosAdicionais(pessoa?.enderecos_adicionais || []);
  }, [pessoa?.id, pessoa?.enderecos_adicionais, setEnderecosAdicionais]);

  const abrirEndereco = (alvo) => {
    if (alvo === "principal") {
      setEnderecoAtual({
        tipo: "principal",
        apelido: "",
        ...Object.fromEntries(
          CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, formData[campo] || ""]),
        ),
        index: "principal",
      });
      return;
    }
    abrirModalEndereco(alvo);
  };

  const principalTemDados = CAMPOS_ENDERECO_PRINCIPAL.some((campo) => formData[campo]);

  const promoverAPrincipal = (entrada, tipoAntigoPrincipal) => {
    const principalAntigo = {
      tipo: tipoAntigoPrincipal,
      apelido: "",
      ...Object.fromEntries(
        CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, formData[campo] || ""]),
      ),
    };

    setFormData((prev) => ({
      ...prev,
      ...Object.fromEntries(
        CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, entrada[campo] || ""]),
      ),
    }));

    setEnderecosAdicionais((prev) => {
      let proximos =
        typeof entrada.index === "number" ? prev.filter((_, i) => i !== entrada.index) : [...prev];
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
        ...Object.fromEntries(
          CAMPOS_ENDERECO_PRINCIPAL.map((campo) => [campo, enderecoAtual[campo]]),
        ),
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

  const errosLocais = useMemo(() => validarFormData(formData), [formData]);
  // Erros do servidor somam aos locais (um erro que só o backend pegou continua visível
  // até o campo mudar de novo) — campo que o usuário já reeditou localmente não carrega
  // mais o aviso antigo do servidor.
  const erros = useMemo(() => ({ ...errosServidor, ...errosLocais }), [errosServidor, errosLocais]);

  // `erros` alimenta o ícone de pendência nas abas (AbasNavegacao), sempre fiel ao estado
  // real. `errosVisiveis` é o que de fato aparece pintado de vermelho nos campos — só depois
  // que o campo foi tocado (blur) ou de uma tentativa de salvar, pra não abrir a tela já toda
  // vermelha antes do usuário sequer começar a preencher.
  const [tentouSalvar, setTentouSalvar] = useState(false);
  const marcarTocado = (campo) => setTocados((atual) => ({ ...atual, [campo]: true }));
  const errosVisiveis = useMemo(() => {
    if (tentouSalvar) return erros;
    const visiveis = {};
    Object.keys(erros).forEach((campo) => {
      if (tocados[campo]) visiveis[campo] = erros[campo];
    });
    return visiveis;
  }, [erros, tocados, tentouSalvar]);

  const alertasPdvAtivosCount = (formData.alertas_pdv || []).filter(
    (alerta) => alerta.ativo !== false,
  ).length;

  const temPessoaSalva = Boolean(pessoaAtual?.id);

  const abas = useMemo(() => {
    const base = [
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
        descricao: "Telefone, e-mail, observações e contatos adicionais",
        invalida: Boolean(erros.celular || erros.contatos_adicionais),
      },
      {
        id: "endereco",
        label: "Endereço",
        icon: MapPin,
        descricao: "Endereço principal e adicionais",
        invalida: Boolean(erros.numero),
      },
      {
        id: "alertas-pdv",
        label: "Alertas do PDV",
        icon: AlertTriangle,
        descricao: "Mensagens automáticas ao atender esta pessoa",
        invalida: false,
        contador: alertasPdvAtivosCount,
      },
    ];

    if (temPessoaSalva) {
      base.push({
        id: "financeiro",
        label: "Financeiro",
        icon: DollarSign,
        descricao: "Crédito, histórico e indicadores financeiros",
        invalida: false,
      });
    }

    return base;
  }, [erros, alertasPdvAtivosCount, temPessoaSalva]);

  useEffect(() => {
    if (!abas.some((aba) => aba.id === abaAtiva)) {
      setAbaAtiva(abas[0]?.id || "dados-gerais");
    }
  }, [abas, abaAtiva]);

  useEffect(() => {
    if (!temPessoaSalva) return undefined;
    let ativo = true;
    setLoadingResumo(true);
    api
      .get(`/financeiro/cliente/${pessoaAtual.id}/resumo`)
      .then((response) => {
        if (ativo) setResumoFinanceiro(response.data.resumo);
      })
      .catch((error) => {
        if (error.response?.status !== 404) {
          console.error("Erro ao carregar resumo financeiro:", error);
        }
        if (ativo) setResumoFinanceiro(null);
      })
      .finally(() => {
        if (ativo) setLoadingResumo(false);
      });
    return () => {
      ativo = false;
    };
  }, [temPessoaSalva, pessoaAtual?.id, refreshKeyCredito]);

  useEffect(() => {
    if (!temPessoaSalva || !moduloCampanhasAtivo) {
      setSaldoCampanhas(null);
      return;
    }
    api
      .get(`/campanhas/clientes/${pessoaAtual.id}/saldo`)
      .then((response) => setSaldoCampanhas(response.data))
      .catch(() => setSaldoCampanhas(null));
  }, [temPessoaSalva, pessoaAtual?.id, moduloCampanhasAtivo]);

  useEffect(() => {
    onSalvandoChange?.(salvando);
  }, [salvando, onSalvandoChange]);

  async function handleSubmit(event) {
    event?.preventDefault();
    setTentouSalvar(true);

    if (Object.keys(errosLocais).length > 0) {
      const abaComErro = abas.find((aba) => aba.invalida);
      if (abaComErro) setAbaAtiva(abaComErro.id);
      toast.error("Corrija os campos destacados antes de salvar.");
      return;
    }

    setSalvando(true);
    setErrosServidor({});
    try {
      const { tags: _tags, ...clienteData } = formData;
      clienteData.alertas_pdv = normalizeClienteAlertasPdv(clienteData.alertas_pdv);
      clienteData.contatos_adicionais = (clienteData.contatos_adicionais || []).filter(
        (contato) => (contato.numero || "").trim() || (contato.vinculo || "").trim(),
      );

      if (clienteData.is_entregador) {
        if (clienteData.is_funcionario) {
          clienteData.tipo_vinculo_entrega = "funcionario";
          clienteData.is_terceirizado = false;
        } else if (clienteData.is_fornecedor) {
          clienteData.is_terceirizado = true;
          clienteData.tipo_vinculo_entrega = "terceirizado";
        }
      }

      clienteData.enderecos_adicionais = enderecosAdicionais;

      Object.keys(clienteData).forEach((key) => {
        if (clienteData[key] === "") clienteData[key] = null;
      });

      const { data: pessoaSalva } = temPessoaSalva
        ? await api.put(`/clientes/${pessoaAtual.id}`, clienteData)
        : await api.post("/clientes/", clienteData);

      toast.success(temPessoaSalva ? "Alterações salvas." : "Cadastro criado.");
      setPessoaAtual(pessoaSalva);
      setFormData(buildFormDataFromCliente(pessoaSalva));
      onSalvo?.(pessoaSalva);
    } catch (error) {
      const details = error.response?.data?.details;
      if (Array.isArray(details) && details.length > 0) {
        const { errosPorCampo, primeiraAba } = mapearErrosServidor(details);
        setErrosServidor(errosPorCampo);
        if (primeiraAba) setAbaAtiva(primeiraAba);
        const mensagens = details.map((detalhe) => detalhe.msg).filter(Boolean);
        toast.error(
          mensagens.join(" · ") || "Não foi possível salvar — corrija os campos destacados.",
        );
      } else {
        toast.error(error.response?.data?.detail || "Não foi possível salvar as alterações.");
      }
    } finally {
      setSalvando(false);
    }
  }

  return (
    <>
      <form id={formId} onSubmit={handleSubmit} noValidate>
        <AbasNavegacao abas={abas} ativa={abaAtiva} onChange={setAbaAtiva} className="mb-4" />

        {abaAtiva === "dados-gerais" ? (
          <div className="space-y-8">
            <ClientePessoaDadosGeraisTab
              erros={errosVisiveis}
              formData={formData}
              onBlurCampo={marcarTocado}
              setFormData={setFormData}
            />

            {temPessoaSalva ? (
              <ClientePessoaHistoricoPanel
                clienteId={pessoaAtual.id}
                origemTenantId={pessoaAtual?.origem_tenant_id}
                versao={pessoaAtual}
              />
            ) : null}

            <div className="border-t border-slate-200 pt-6 dark:border-slate-700">
              <h3 className="mb-4 text-base font-semibold text-slate-900 dark:text-slate-100">
                Complementares
              </h3>
              <ClientePessoaComplementaresTab formData={formData} setFormData={setFormData} />
            </div>
          </div>
        ) : null}

        {abaAtiva === "contatos" ? (
          <ClientePessoaContatosTab
            erros={errosVisiveis}
            formData={formData}
            onBlurCampo={marcarTocado}
            setFormData={setFormData}
          />
        ) : null}

        {abaAtiva === "endereco" ? (
          <ClientePessoaEnderecoTab
            abrirModalEndereco={abrirEndereco}
            enderecosAdicionais={enderecosAdicionais}
            erroEnderecoPrincipal={errosVisiveis.numero}
            formData={formData}
            removerEndereco={excluirEndereco}
          />
        ) : null}

        {abaAtiva === "alertas-pdv" ? (
          <ClientePessoaAlertasPdvSection formData={formData} setFormData={setFormData} />
        ) : null}

        {abaAtiva === "financeiro" && temPessoaSalva ? (
          <ClientePessoaFinanceiroTab
            cliente={pessoaAtual}
            loadingResumo={loadingResumo}
            navigate={navigate}
            refreshKeyCredito={refreshKeyCredito}
            resumoFinanceiro={resumoFinanceiro}
            saldoCampanhas={saldoCampanhas}
            setMostrarModalAdicionarCredito={setMostrarModalAdicionarCredito}
            setMostrarModalRemoverCredito={setMostrarModalRemoverCredito}
          />
        ) : null}
      </form>

      {mostrarModalAdicionarCredito ? (
        <ModalAdicionarCredito
          cliente={pessoaAtual}
          onConfirmar={(novoSaldo) => {
            setPessoaAtual((prev) => ({ ...prev, credito: novoSaldo }));
            setRefreshKeyCredito((k) => k + 1);
          }}
          onClose={() => setMostrarModalAdicionarCredito(false)}
        />
      ) : null}

      {mostrarModalRemoverCredito ? (
        <ModalRemoverCredito
          cliente={pessoaAtual}
          onConfirmar={(novoSaldo) => {
            setPessoaAtual((prev) => ({ ...prev, credito: novoSaldo }));
            setRefreshKeyCredito((k) => k + 1);
          }}
          onClose={() => setMostrarModalRemoverCredito(false)}
        />
      ) : null}

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
    </>
  );
}
