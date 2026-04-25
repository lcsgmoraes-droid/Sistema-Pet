import { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Stethoscope,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Save,
  X,
  Lock,
  Calculator,
  MessageSquare,
  FlaskConical,
  Syringe,
  BedDouble,
} from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { formatMoneyBRL, formatPercent } from "../../utils/formatters";
import NovoPetButton from "../../components/veterinario/NovoPetButton";
import NovoPetModal from "../../components/veterinario/NovoPetModal";
import ExameChatIAAvancada from "./components/ExameChatIAAvancada";
import CalculadoraDoseModal from "./consultaForm/CalculadoraDoseModal";
import InsumoRapidoModal from "./consultaForm/InsumoRapidoModal";
import NovoExameConsultaModal from "./consultaForm/NovoExameConsultaModal";
import TimelineConsultaPanel from "./consultaForm/TimelineConsultaPanel";
import {
  ETAPAS,
  css,
  hojeIso,
  obterResumoProcedimentoSelecionado,
  parseNumero,
} from "./consultaForm/consultaFormUtils";

// ---------- helpers ----------
function campo(label, obrigatorio = false) {
  return function renderCampo(children) {
    return (
      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-600">
          {label} {obrigatorio && <span className="text-red-400">*</span>}
        </label>
        {children}
      </div>
    );
  };
}

// ---------- componente principal ----------
export default function VetConsultaForm() {
  const navigate = useNavigate();
  const { consultaId } = useParams();
  const [searchParams] = useSearchParams();
  const isEdicao = Boolean(consultaId);
  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const tipoQuery = searchParams.get("tipo") || "consulta";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

  const [etapa, setEtapa] = useState(0);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);
  const [consultaIdAtual, setConsultaIdAtual] = useState(consultaId ?? null);
  const [finalizado, setFinalizado] = useState(false);
  const [carregando, setCarregando] = useState(isEdicao);
  const [assinatura, setAssinatura] = useState(null);
  const [baixandoPdf, setBaixandoPdf] = useState(false);
  const [modalCalculadoraAberto, setModalCalculadoraAberto] = useState(false);
  const [modalNovoExameAberto, setModalNovoExameAberto] = useState(false);
  const [salvandoNovoExame, setSalvandoNovoExame] = useState(false);
  const [modalNovoPetAberto, setModalNovoPetAberto] = useState(false);
  const [refreshExamesToken, setRefreshExamesToken] = useState(0);
  const modoSomenteLeitura = isEdicao && finalizado;
  const tituloConsulta = modoSomenteLeitura
    ? "Consulta finalizada (somente visualização)"
    : isEdicao
      ? "Continuar consulta"
      : "Nova consulta";

  // listas externas
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);
  const [medicamentosCatalogo, setMedicamentosCatalogo] = useState([]);
  const [procedimentosCatalogo, setProcedimentosCatalogo] = useState([]);
  const [buscaTutor, setBuscaTutor] = useState("");
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [tutoresSugeridos, setTutoresSugeridos] = useState([]);
  const [listaPetsExpandida, setListaPetsExpandida] = useState(false);
  const [novoExameForm, setNovoExameForm] = useState({
    tipo: "laboratorial",
    nome: "",
    data_solicitacao: hojeIso(),
    laboratorio: "",
    observacoes: "",
  });
  const [novoExameArquivo, setNovoExameArquivo] = useState(null);
  const [calculadoraForm, setCalculadoraForm] = useState({
    medicamento_id: "",
    peso_kg: "",
    dose_mg_kg: "",
    frequencia_horas: "12",
    dias: "7",
  });
  const [timelineConsulta, setTimelineConsulta] = useState([]);
  const [carregandoTimeline, setCarregandoTimeline] = useState(false);
  const [modalInsumoAberto, setModalInsumoAberto] = useState(false);
  const [salvandoInsumoRapido, setSalvandoInsumoRapido] = useState(false);
  const [insumoRapidoSelecionado, setInsumoRapidoSelecionado] = useState(null);
  const [insumoRapidoForm, setInsumoRapidoForm] = useState({
    quantidade_utilizada: "1",
    quantidade_desperdicio: "",
    observacoes: "",
  });

  // ---------- Form state ----------
  const [form, setForm] = useState({
    // Etapa 1 — Triagem
    pet_id: "",
    veterinario_id: "",
    motivo_consulta: "",
    peso_kg: "",
    temperatura: "",
    freq_cardiaca: "",
    freq_respiratoria: "",
    tpc: "",
    mucosa: "",
    estado_hidratacao: "",
    nivel_consciencia: "",
    nivel_dor: "",
    // Etapa 2 — Exame clínico
    exame_fisico: "",
    historico_clinico: "",
    // Etapa 3 — Diagnóstico
    diagnostico: "",
    prognostico: "",
    tratamento: "",
    observacoes: "",
    retorno_em_dias: "",
    // Prescrição
    prescricao_itens: [], // [{nome, principio, dose_mg, frequencia, duracao}]
    procedimentos_realizados: [],
  });
  // Carrega dados ao editar
  useEffect(() => {
    if (!isEdicao) return;
    vetApi
      .obterConsulta(consultaId)
      .then((res) => {
        const c = res.data;
        setForm((prev) => ({
          ...prev,
          pet_id: c.pet_id ?? "",
          veterinario_id: c.veterinario_id ?? "",
          motivo_consulta: c.motivo_consulta ?? "",
          peso_kg: c.peso_kg ?? "",
          temperatura: c.temperatura ?? "",
          freq_cardiaca: c.freq_cardiaca ?? "",
          freq_respiratoria: c.freq_respiratoria ?? "",
          tpc: c.tpc ?? "",
          mucosa: c.mucosa ?? "",
          estado_hidratacao: c.estado_hidratacao ?? "",
          nivel_consciencia: c.nivel_consciencia ?? "",
          nivel_dor: c.nivel_dor ?? "",
          exame_fisico: c.exame_fisico ?? "",
          historico_clinico: c.historico_clinico ?? "",
          diagnostico: c.diagnostico ?? "",
          prognostico: c.prognostico ?? "",
          tratamento: c.tratamento ?? "",
          observacoes: c.observacoes ?? "",
          retorno_em_dias: c.retorno_em_dias ?? "",
        }));
        if (c.status === "finalizada") setFinalizado(true);
      })
      .catch(() => setErro("Não foi possível carregar a consulta."))
      .finally(() => setCarregando(false));
  }, [consultaId, isEdicao]);

  useEffect(() => {
    if (!modoSomenteLeitura || !consultaIdAtual) return;
    vetApi
      .validarAssinaturaConsulta(consultaIdAtual)
      .then((res) => setAssinatura(res.data))
      .catch(() => setAssinatura(null));
  }, [modoSomenteLeitura, consultaIdAtual]);

  // Carrega pets e veterinários
  useEffect(() => {
    api
      .get("/vet/pets", { params: { limit: 500 } })
      .then((r) => setPets(r.data?.items ?? r.data ?? []))
      .catch(() => {});
    api
      .get("/vet/veterinarios")
      .then((r) => setVeterinarios(r.data ?? []))
      .catch(() => {});

    vetApi
      .listarMedicamentos()
      .then((r) => setMedicamentosCatalogo(Array.isArray(r.data) ? r.data : (r.data?.items ?? [])))
      .catch(() => {});
    vetApi
      .listarCatalogoProcedimentos()
      .then((r) => setProcedimentosCatalogo(Array.isArray(r.data) ? r.data : (r.data?.items ?? [])))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (isEdicao) return;
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((p) => String(p.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    set("pet_id", String(petEncontrado.id));
    setTutorSelecionado({
      id: petEncontrado.cliente_id,
      nome: petEncontrado.cliente_nome ?? `Tutor #${petEncontrado.cliente_id}`,
      telefone: petEncontrado.cliente_telefone ?? "",
      celular: petEncontrado.cliente_celular ?? "",
    });
    setBuscaTutor(petEncontrado.cliente_nome ?? "");
    setListaPetsExpandida(false);
  }, [isEdicao, petIdQuery, novoPetIdQuery, pets]);

  useEffect(() => {
    if (isEdicao || !tutorIdQuery) return;
    setTutorSelecionado((prev) => {
      if (prev?.id && String(prev.id) === String(tutorIdQuery)) return prev;
      return {
        id: String(tutorIdQuery),
        nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
        telefone: "",
        celular: "",
      };
    });
    setBuscaTutor((prev) => prev || tutorNomeQuery || "");
  }, [isEdicao, tutorIdQuery, tutorNomeQuery]);

  function set(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  const tutoresIndex = useMemo(() => {
    const mapa = new Map();
    for (const p of pets) {
      const tutorId = p.cliente_id;
      if (!tutorId) continue;
      if (!mapa.has(tutorId)) {
        mapa.set(tutorId, {
          id: tutorId,
          nome: p.cliente_nome ?? `Tutor #${tutorId}`,
          telefone: p.cliente_telefone ?? "",
          celular: p.cliente_celular ?? "",
        });
      }
    }
    return Array.from(mapa.values()).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [pets]);

  const petsDoTutor = useMemo(() => {
    if (!tutorSelecionado) return [];

    const petsTutor = pets.filter(
      (p) => String(p.cliente_id) === String(tutorSelecionado.id) && p.ativo !== false
    );

    // Evita duplicidade visual caso a API devolva itens repetidos
    const porId = new Map();
    for (const pet of petsTutor) {
      porId.set(String(pet.id), pet);
    }
    return Array.from(porId.values());
  }, [pets, tutorSelecionado]);

  const petSelecionado = useMemo(
    () => pets.find((p) => String(p.id) === String(form.pet_id)) ?? null,
    [pets, form.pet_id]
  );

  const petSelecionadoLabel = useMemo(() => {
    if (!petSelecionado) return "Selecione o pet";
    const especie = petSelecionado.especie;
    const especieValida = especie && !/\?/.test(especie);
    return especieValida ? `${petSelecionado.nome} (${especie})` : petSelecionado.nome;
  }, [petSelecionado]);
  const sugestoesEspecies = useMemo(
    () =>
      Array.from(new Set(pets.map((pet) => pet?.especie).filter((especie) => especie && !/\?/.test(especie)))),
    [pets]
  );
  const medicamentoCalculadoraSelecionado = useMemo(
    () =>
      medicamentosCatalogo.find(
        (item) => String(item.id) === String(calculadoraForm.medicamento_id)
      ) ?? null,
    [medicamentosCatalogo, calculadoraForm.medicamento_id]
  );
  const calculadoraResultado = useMemo(() => {
    const peso = parseNumero(calculadoraForm.peso_kg);
    const dose = parseNumero(calculadoraForm.dose_mg_kg);
    const frequencia = parseNumero(calculadoraForm.frequencia_horas);
    const dias = parseNumero(calculadoraForm.dias);
    if (!Number.isFinite(peso) || peso <= 0 || !Number.isFinite(dose) || dose <= 0) {
      return null;
    }

    const mgPorDose = peso * dose;
    const dosesPorDia = Number.isFinite(frequencia) && frequencia > 0 ? 24 / frequencia : null;
    const mgDia = dosesPorDia ? mgPorDose * dosesPorDia : null;
    const mgTratamento = mgDia && Number.isFinite(dias) && dias > 0 ? mgDia * dias : null;

    return {
      mgPorDose,
      dosesPorDia,
      mgDia,
      mgTratamento,
    };
  }, [calculadoraForm]);
  const contextoConsultaParams = useMemo(() => {
    if (!form.pet_id) return "";
    const params = new URLSearchParams();
    params.set("pet_id", String(form.pet_id));
    if (consultaIdAtual) params.set("consulta_id", String(consultaIdAtual));
    if (agendamentoIdQuery) params.set("agendamento_id", String(agendamentoIdQuery));
    if (tutorSelecionado?.id) params.set("tutor_id", String(tutorSelecionado.id));
    if (tutorSelecionado?.nome) params.set("tutor_nome", tutorSelecionado.nome);
    return params.toString();
  }, [form.pet_id, consultaIdAtual, agendamentoIdQuery, tutorSelecionado]);

  useEffect(() => {
    const termo = buscaTutor.trim();
    if (!termo) {
      setTutoresSugeridos([]);
      return;
    }

    const termoLower = termo.toLowerCase();
    const termoDigitos = termo.replaceAll(/\D/g, "");

    const sugestoes = tutoresIndex
      .filter((t) => {
        const nome = (t.nome ?? "").toLowerCase();
        const telefone = (t.telefone ?? "").toLowerCase();
        const celular = (t.celular ?? "").toLowerCase();
        const telefoneDigitos = telefone.replaceAll(/\D/g, "");
        const celularDigitos = celular.replaceAll(/\D/g, "");

        return (
          nome.includes(termoLower) ||
          telefone.includes(termoLower) ||
          celular.includes(termoLower) ||
          (termoDigitos && (telefoneDigitos.includes(termoDigitos) || celularDigitos.includes(termoDigitos)))
        );
      })
      .slice(0, 20);

    setTutoresSugeridos(sugestoes);
  }, [buscaTutor, tutoresIndex]);

  useEffect(() => {
    if (!form.pet_id || !pets.length) return;
    const petAtual = pets.find((p) => String(p.id) === String(form.pet_id));
    if (!petAtual) return;

    setTutorSelecionado((prev) => {
      if (prev && String(prev.id) === String(petAtual.cliente_id)) return prev;
      return {
        id: petAtual.cliente_id,
        nome: petAtual.cliente_nome ?? `Tutor #${petAtual.cliente_id}`,
        telefone: petAtual.cliente_telefone ?? "",
        celular: petAtual.cliente_celular ?? "",
      };
    });
    setBuscaTutor((prev) => prev || petAtual.cliente_nome || "");
  }, [form.pet_id, pets]);

  useEffect(() => {
    setCalculadoraForm((prev) => ({
      ...prev,
      peso_kg: prev.peso_kg || form.peso_kg || String(petSelecionado?.peso || ""),
    }));
  }, [form.peso_kg, petSelecionado]);

  useEffect(() => {
    if (!medicamentoCalculadoraSelecionado) return;
    const doseMin = parseNumero(medicamentoCalculadoraSelecionado.dose_minima_mg_kg);
    const doseMax = parseNumero(medicamentoCalculadoraSelecionado.dose_maxima_mg_kg);
    const doseMedia = Number.isFinite(doseMin) && Number.isFinite(doseMax)
      ? ((doseMin + doseMax) / 2).toFixed(2)
      : doseMin || doseMax || "";
    setCalculadoraForm((prev) => ({
      ...prev,
      dose_mg_kg: prev.dose_mg_kg || String(doseMedia || ""),
    }));
  }, [medicamentoCalculadoraSelecionado]);

  useEffect(() => {
    if (!consultaIdAtual) {
      setTimelineConsulta([]);
      return;
    }
    carregarTimelineConsulta(consultaIdAtual);
  }, [consultaIdAtual]);

  async function carregarTimelineConsulta(id = consultaIdAtual) {
    if (!id) return;
    setCarregandoTimeline(true);
    try {
      const res = await vetApi.obterTimelineConsulta(id);
      setTimelineConsulta(Array.isArray(res.data?.eventos) ? res.data.eventos : []);
    } catch {
      setTimelineConsulta([]);
    } finally {
      setCarregandoTimeline(false);
    }
  }

  function abrirModalInsumoRapido() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lançar insumos rápidos.");
      return;
    }
    setInsumoRapidoSelecionado(null);
    setInsumoRapidoForm({
      quantidade_utilizada: "1",
      quantidade_desperdicio: "",
      observacoes: "",
    });
    setModalInsumoAberto(true);
  }

  function selecionarTutor(tutor) {
    setTutorSelecionado(tutor);
    setBuscaTutor(tutor.nome);
    setTutoresSugeridos([]);
    setListaPetsExpandida(true);
    set("pet_id", "");
  }

  function limparTutor() {
    setTutorSelecionado(null);
    setBuscaTutor("");
    setTutoresSugeridos([]);
    setListaPetsExpandida(false);
    set("pet_id", "");
  }

  function abrirModalNovoPet() {
    if (!tutorSelecionado) return;
    setModalNovoPetAberto(true);
  }

  function handleNovoPetCriado(petCriado) {
    if (!petCriado?.id) {
      setModalNovoPetAberto(false);
      return;
    }

    setPets((prev) => {
      const semDuplicado = prev.filter((pet) => String(pet.id) !== String(petCriado.id));
      return [petCriado, ...semDuplicado];
    });

    setTutorSelecionado((prev) => ({
      id: petCriado.cliente_id,
      nome: petCriado.cliente_nome ?? prev?.nome ?? tutorSelecionado?.nome ?? `Tutor #${petCriado.cliente_id}`,
      telefone: petCriado.cliente_telefone ?? prev?.telefone ?? "",
      celular: petCriado.cliente_celular ?? prev?.celular ?? "",
    }));
    setBuscaTutor(petCriado.cliente_nome ?? tutorSelecionado?.nome ?? buscaTutor);
    set("pet_id", String(petCriado.id));
    setListaPetsExpandida(false);
    setModalNovoPetAberto(false);
    setErro(null);
    setSucesso(`Pet ${petCriado.nome} cadastrado e selecionado na consulta.`);
  }

  // ---------- Salvar rascunho ----------
  async function salvarRascunho() {
    setSalvando(true);
    setErro(null);
    setSucesso(null);
    try {
      const petSelecionadoAtual = pets.find((p) => String(p.id) === String(form.pet_id));

      if (!petSelecionadoAtual?.cliente_id) {
        setErro("Selecione um pet válido vinculado a um tutor.");
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }

      const payload = {
        pet_id: form.pet_id || undefined,
        cliente_id: petSelecionadoAtual.cliente_id,
        veterinario_id: form.veterinario_id || undefined,
        tipo: tipoQuery || "consulta",
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        queixa_principal: form.motivo_consulta || undefined,
        // Campos extras são ignorados pelo backend no create e usados no patch quando suportados.
        peso_kg: form.peso_kg ? Number.parseFloat(form.peso_kg) : undefined,
        temperatura: form.temperatura ? Number.parseFloat(form.temperatura) : undefined,
        freq_cardiaca: form.freq_cardiaca ? parseInt(form.freq_cardiaca) : undefined,
        freq_respiratoria: form.freq_respiratoria ? parseInt(form.freq_respiratoria) : undefined,
        tpc: form.tpc || undefined,
        mucosa: form.mucosa || undefined,
        estado_hidratacao: form.estado_hidratacao || undefined,
        nivel_consciencia: form.nivel_consciencia || undefined,
        nivel_dor: form.nivel_dor ? parseInt(form.nivel_dor) : undefined,
        exame_fisico: form.exame_fisico || undefined,
        historico_clinico: form.historico_clinico || undefined,
        diagnostico: form.diagnostico || undefined,
        prognostico: form.prognostico || undefined,
        tratamento: form.tratamento || undefined,
        observacoes: form.observacoes || undefined,
        retorno_em_dias: form.retorno_em_dias ? parseInt(form.retorno_em_dias) : undefined,
      };

      if (!consultaIdAtual) {
        const res = await vetApi.criarConsulta(payload);
        setConsultaIdAtual(res.data.id);
        navigate(`/veterinario/consultas/${res.data.id}`, { replace: true });
      } else {
        await vetApi.atualizarConsulta(consultaIdAtual, payload);
      }

      setSucesso(
        etapa < ETAPAS.length - 1
          ? "Rascunho salvo com sucesso."
          : "Rascunho salvo com sucesso. Você pode finalizar quando quiser."
      );

      if (etapa < ETAPAS.length - 1) setEtapa((e) => e + 1);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao salvar. Tente novamente.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSalvando(false);
    }
  }

  // ---------- Finalizar ----------
  async function finalizar() {
    setSucesso(null);
    if (!consultaIdAtual) { setErro("Salve a consulta antes de finalizar."); return; }
    setSalvando(true);
    setErro(null);
    try {
      // primeiro salva o que está no form
      await vetApi.atualizarConsulta(consultaIdAtual, {
        diagnostico: form.diagnostico || undefined,
        prognostico: form.prognostico || undefined,
        tratamento: form.tratamento || undefined,
        observacoes: form.observacoes || undefined,
        retorno_em_dias: form.retorno_em_dias ? parseInt(form.retorno_em_dias) : undefined,
      });
      // cria prescrição se houver itens
      if (form.prescricao_itens.length > 0) {
        const itensPrescricao = form.prescricao_itens
          .map((it) => {
            const nome = (it.nome || "").trim();
            const frequencia = (it.frequencia || "").trim();
            const instrucoes = (it.instrucoes || "").trim();
            const dose = (it.dose_mg || "").toString().trim();
            const unidade = (it.unidade || "mg").trim();
            const posologia = [dose ? `${dose} ${unidade}` : "", frequencia, instrucoes]
              .filter(Boolean)
              .join(" - ");

            if (!nome || !posologia) return null;

            return {
              nome_medicamento: nome,
              concentracao: it.principio_ativo || undefined,
              quantidade: dose || undefined,
              posologia,
              via_administracao: it.via || undefined,
              duracao_dias: it.duracao_dias ? Number.parseInt(it.duracao_dias) : undefined,
            };
          })
          .filter(Boolean);

        if (itensPrescricao.length === 0) {
          setErro("Adicione ao menos 1 item de prescrição com nome e posologia.");
          return;
        }

        await vetApi.criarPrescricao({
          consulta_id: consultaIdAtual,
          pet_id: form.pet_id ? Number.parseInt(form.pet_id) : undefined,
          veterinario_id: form.veterinario_id ? Number.parseInt(form.veterinario_id) : undefined,
          tipo_receituario: "simples",
          itens: itensPrescricao,
        });
      }

      if (form.procedimentos_realizados.length > 0) {
        const procedimentosValidos = form.procedimentos_realizados.filter((item) => item.nome?.trim());
        for (const procedimento of procedimentosValidos) {
          await vetApi.adicionarProcedimento({
            consulta_id: consultaIdAtual,
            catalogo_id: procedimento.catalogo_id ? Number.parseInt(procedimento.catalogo_id) : undefined,
            nome: procedimento.nome,
            descricao: procedimento.descricao || undefined,
            valor: procedimento.valor ? Number(String(procedimento.valor).replace(",", ".")) : undefined,
            observacoes: procedimento.observacoes || undefined,
            realizado: true,
            baixar_estoque: procedimento.baixar_estoque !== false,
          });
        }
      }
      // finaliza (gera hash)
      await vetApi.finalizarConsulta(consultaIdAtual);
      setFinalizado(true);
      await carregarTimelineConsulta();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao finalizar.");
    } finally {
      setSalvando(false);
    }
  }

  // ---------- Prescrição helpers ----------
  function adicionarItem() {
    setForm((prev) => ({
      ...prev,
      prescricao_itens: [
        ...prev.prescricao_itens,
        {
          medicamento_id: "",
          nome: "",
          principio_ativo: "",
          dose_mg: "",
          unidade: "mg",
          dose_minima_mg_kg: "",
          dose_maxima_mg_kg: "",
          frequencia: "",
          duracao_dias: "",
          via: "oral",
          instrucoes: "",
        },
      ],
    }));
  }

  function adicionarProcedimento() {
    setForm((prev) => ({
      ...prev,
      procedimentos_realizados: [
        ...prev.procedimentos_realizados,
        {
          catalogo_id: "",
          nome: "",
          descricao: "",
          valor: "",
          observacoes: "",
          baixar_estoque: true,
        },
      ],
    }));
  }

  function removerProcedimento(idx) {
    setForm((prev) => ({
      ...prev,
      procedimentos_realizados: prev.procedimentos_realizados.filter((_, i) => i !== idx),
    }));
  }

  function setProcedimentoItem(idx, campo, valor) {
    setForm((prev) => {
      const itens = [...prev.procedimentos_realizados];
      itens[idx] = { ...itens[idx], [campo]: valor };
      return { ...prev, procedimentos_realizados: itens };
    });
  }

  function selecionarProcedimentoCatalogo(idx, catalogoId) {
    const procedimento = procedimentosCatalogo.find((item) => String(item.id) === String(catalogoId));
    setForm((prev) => {
      const itens = [...prev.procedimentos_realizados];
      itens[idx] = {
        ...itens[idx],
        catalogo_id: catalogoId,
        nome: procedimento?.nome || itens[idx].nome,
        descricao: procedimento?.descricao || "",
        valor: procedimento?.valor_padrao != null ? String(procedimento.valor_padrao) : itens[idx].valor,
      };
      return { ...prev, procedimentos_realizados: itens };
    });
  }

  function removerItem(idx) {
    setForm((prev) => ({
      ...prev,
      prescricao_itens: prev.prescricao_itens.filter((_, i) => i !== idx),
    }));
  }

  function setItem(idx, chave, valor) {
    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      itens[idx] = { ...itens[idx], [chave]: valor };
      return { ...prev, prescricao_itens: itens };
    });
  }

  function calcularDosePorPeso(item) {
    const peso = parseNumero(form.peso_kg);
    if (!Number.isFinite(peso) || peso <= 0) {
      setErro("Informe o peso do pet para calcular a dose automaticamente.");
      return null;
    }

    const doseMin = parseNumero(item.dose_minima_mg_kg);
    const doseMax = parseNumero(item.dose_maxima_mg_kg);
    let doseMgKg = Number.isFinite(doseMin) ? doseMin : NaN;

    if (Number.isFinite(doseMin) && Number.isFinite(doseMax)) {
      doseMgKg = (doseMin + doseMax) / 2;
    } else if (!Number.isFinite(doseMgKg) && Number.isFinite(doseMax)) {
      doseMgKg = doseMax;
    }

    if (!Number.isFinite(doseMgKg) || doseMgKg <= 0) {
      setErro("Esse medicamento não tem dose mg/kg cadastrada no catálogo.");
      return null;
    }

    return {
      dose_mg: (doseMgKg * peso).toFixed(2),
      unidade: "mg",
    };
  }

  function selecionarMedicamentoNoItem(idx, medicamentoId) {
    const medicamento = medicamentosCatalogo.find((m) => String(m.id) === String(medicamentoId));
    if (!medicamento) return;

    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      const itemAtual = itens[idx] ?? {};
      const itemAtualizado = {
        ...itemAtual,
        medicamento_id: medicamento.id,
        nome: medicamento.nome ?? itemAtual.nome ?? "",
        principio_ativo: medicamento.principio_ativo ?? itemAtual.principio_ativo ?? "",
        via: medicamento.via_administracao ?? itemAtual.via ?? "oral",
        dose_minima_mg_kg: medicamento.dose_minima_mg_kg,
        dose_maxima_mg_kg: medicamento.dose_maxima_mg_kg,
      };

      const doseCalculada = calcularDosePorPeso(itemAtualizado);
      if (doseCalculada) {
        itemAtualizado.dose_mg = doseCalculada.dose_mg;
        itemAtualizado.unidade = doseCalculada.unidade;
      }

      itens[idx] = itemAtualizado;
      return { ...prev, prescricao_itens: itens };
    });
  }

  function recalcularDoseItem(idx) {
    const item = form.prescricao_itens[idx];
    if (!item) return;

    const doseCalculada = calcularDosePorPeso(item);
    if (!doseCalculada) return;

    setForm((prev) => {
      const itens = [...prev.prescricao_itens];
      itens[idx] = {
        ...itens[idx],
        dose_mg: doseCalculada.dose_mg,
        unidade: doseCalculada.unidade,
      };
      return { ...prev, prescricao_itens: itens };
    });
  }

  function baixarArquivo(blob, nomeArquivo) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = nomeArquivo;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  async function baixarProntuarioPdf() {
    if (!consultaIdAtual) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const res = await vetApi.baixarProntuarioPdf(consultaIdAtual);
      baixarArquivo(res.data, `prontuario_consulta_${consultaIdAtual}.pdf`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível baixar o prontuário em PDF.");
    } finally {
      setBaixandoPdf(false);
    }
  }

  async function baixarUltimaReceitaPdf() {
    if (!consultaIdAtual) return;
    setBaixandoPdf(true);
    setErro(null);
    try {
      const lista = await vetApi.listarPrescricoes(consultaIdAtual);
      const prescricoes = Array.isArray(lista.data) ? lista.data : (lista.data?.items ?? []);
      if (!prescricoes.length) {
        setErro("Essa consulta não tem prescrição emitida.");
        return;
      }

      const ultima = prescricoes[prescricoes.length - 1];
      const res = await vetApi.baixarPrescricaoPdf(ultima.id);
      baixarArquivo(res.data, `${ultima.numero || `prescricao_${ultima.id}`}.pdf`);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível baixar a receita em PDF.");
    } finally {
      setBaixandoPdf(false);
    }
  }

  function abrirFluxoConsulta(pathname, extras = {}) {
    if (!contextoConsultaParams) {
      setErro("Salve a consulta com um pet válido antes de abrir outro fluxo clínico.");
      return;
    }
    const params = new URLSearchParams(contextoConsultaParams);
    Object.entries(extras).forEach(([chave, valor]) => {
      if (valor == null || valor === "") return;
      params.set(chave, String(valor));
    });
    navigate(`${pathname}?${params.toString()}`);
  }

  async function salvarNovoExameRapido() {
    if (!form.pet_id || !novoExameForm.nome.trim()) {
      setErro("Selecione o pet e informe o nome do exame.");
      return;
    }

    setSalvandoNovoExame(true);
    setErro(null);
    try {
      const res = await vetApi.criarExame({
        pet_id: Number(form.pet_id),
        consulta_id: consultaIdAtual ? Number(consultaIdAtual) : undefined,
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        tipo: novoExameForm.tipo,
        nome: novoExameForm.nome.trim(),
        data_solicitacao: novoExameForm.data_solicitacao || undefined,
        laboratorio: novoExameForm.laboratorio?.trim() || undefined,
        observacoes: novoExameForm.observacoes?.trim() || undefined,
      });

      if (novoExameArquivo) {
        await vetApi.uploadArquivoExame(res.data.id, novoExameArquivo);
        try {
          await vetApi.processarArquivoExameIA(res.data.id);
        } catch (erroProcessamento) {
          console.warn("Nao foi possivel processar o arquivo do exame com IA automaticamente.", erroProcessamento);
        }
      }

      setModalNovoExameAberto(false);
      setNovoExameForm({
        tipo: "laboratorial",
        nome: "",
        data_solicitacao: hojeIso(),
        laboratorio: "",
        observacoes: "",
      });
      setNovoExameArquivo(null);
      setRefreshExamesToken((prev) => prev + 1);
      setSucesso("Exame vinculado à consulta com sucesso.");
      await carregarTimelineConsulta();
      setEtapa(1);
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível registrar o exame.");
    } finally {
      setSalvandoNovoExame(false);
    }
  }

  async function salvarInsumoRapidoConsulta() {
    if (!consultaIdAtual) {
      setErro("Salve a consulta primeiro para lançar insumos.");
      return;
    }
    if (!insumoRapidoSelecionado?.id) {
      setErro("Selecione o insumo do estoque.");
      return;
    }

    const quantidadeUtilizada = parseNumero(insumoRapidoForm.quantidade_utilizada);
    const quantidadeDesperdicio = parseNumero(insumoRapidoForm.quantidade_desperdicio) || 0;
    const quantidadeConsumida = quantidadeUtilizada + quantidadeDesperdicio;

    if (!Number.isFinite(quantidadeUtilizada) || quantidadeUtilizada <= 0) {
      setErro("Informe a quantidade efetivamente utilizada do insumo.");
      return;
    }
    if (!Number.isFinite(quantidadeConsumida) || quantidadeConsumida <= 0) {
      setErro("A baixa total do insumo precisa ser maior que zero.");
      return;
    }

    setSalvandoInsumoRapido(true);
    setErro(null);
    try {
      const unidade = insumoRapidoSelecionado.unidade || "un";
      await vetApi.adicionarProcedimento({
        consulta_id: Number(consultaIdAtual),
        nome: `Insumo: ${insumoRapidoSelecionado.nome}`,
        descricao: "Lançamento rápido de insumo durante a consulta",
        valor: 0,
        observacoes: insumoRapidoForm.observacoes?.trim()
          ? `${insumoRapidoForm.observacoes.trim()} | Utilizado: ${quantidadeUtilizada} ${unidade}${quantidadeDesperdicio ? ` | Desperdício: ${quantidadeDesperdicio} ${unidade}` : ""}`
          : `Utilizado: ${quantidadeUtilizada} ${unidade}${quantidadeDesperdicio ? ` | Desperdício: ${quantidadeDesperdicio} ${unidade}` : ""}`,
        realizado: true,
        baixar_estoque: true,
        insumos: [
          {
            produto_id: insumoRapidoSelecionado.id,
            nome: insumoRapidoSelecionado.nome,
            unidade,
            quantidade: quantidadeConsumida,
            baixar_estoque: true,
          },
        ],
      });

      setModalInsumoAberto(false);
      setInsumoRapidoSelecionado(null);
      setInsumoRapidoForm({
        quantidade_utilizada: "1",
        quantidade_desperdicio: "",
        observacoes: "",
      });
      setSucesso("Insumo lançado com sucesso na consulta.");
      await carregarTimelineConsulta();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Não foi possível lançar o insumo.");
    } finally {
      setSalvandoInsumoRapido(false);
    }
  }

  // ---------- Render ----------
  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (finalizado && !isEdicao) {
    return (
      <div className="p-6 max-w-lg mx-auto text-center space-y-4">
        <div className="p-4 bg-green-50 rounded-xl border border-green-200">
          <CheckCircle size={40} className="mx-auto text-green-500 mb-2" />
          <h2 className="text-lg font-bold text-green-700">Consulta finalizada!</h2>
          <p className="text-sm text-gray-500 mt-1">O prontuário foi assinado digitalmente e não pode mais ser alterado.</p>
        </div>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => navigate("/veterinario/consultas")}
            className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Ver todas as consultas
          </button>
          <button
            onClick={() => navigate("/veterinario/consultas/nova")}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Nova consulta
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-xl">
            <Stethoscope size={22} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">
              {tituloConsulta}
            </h1>
            <p className="text-xs text-gray-400">
              {consultaIdAtual ? `Código da consulta: #${consultaIdAtual}` : "Ainda não salva"}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {consultaIdAtual && (
            <button
              type="button"
              onClick={() => abrirFluxoConsulta("/veterinario/assistente-ia")}
              className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
            >
              <MessageSquare size={16} />
              IA da consulta
            </button>
          )}
          <button
            type="button"
            onClick={() => setModalCalculadoraAberto(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm font-medium text-cyan-700 hover:bg-cyan-100"
          >
            <Calculator size={16} />
            Calculadora
          </button>
        </div>
      </div>

      {modoSomenteLeitura && (
        <div className="space-y-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
          <div className="flex items-center gap-2">
            <Lock size={15} />
            <span>Consulta assinada digitalmente. Você pode visualizar todos os dados, mas não pode editar.</span>
          </div>
          {assinatura && (
            <div className="text-xs text-green-800 bg-white/70 border border-green-200 rounded px-3 py-2">
              <div>
                Integridade do prontuário: <strong>{assinatura.hash_valido ? "válida" : "divergente"}</strong>
              </div>
              <div>
                Hash: <span className="font-mono">{assinatura.hash_prontuario || "—"}</span>
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              onClick={baixarProntuarioPdf}
              disabled={baixandoPdf}
              className="px-3 py-1.5 text-xs border border-green-300 rounded-md hover:bg-green-100 disabled:opacity-60"
            >
              {baixandoPdf ? "Baixando..." : "Baixar prontuário PDF"}
            </button>
            <button
              type="button"
              onClick={baixarUltimaReceitaPdf}
              disabled={baixandoPdf}
              className="px-3 py-1.5 text-xs border border-green-300 rounded-md hover:bg-green-100 disabled:opacity-60"
            >
              {baixandoPdf ? "Baixando..." : "Baixar receita PDF"}
            </button>
          </div>
        </div>
      )}

      {/* Passos */}
      <div className="flex items-center gap-1">
        {ETAPAS.map((nome, i) => (
          <div key={i} className="flex items-center gap-1">
            <button
              onClick={() => {
                if (modoSomenteLeitura) {
                  setEtapa(i);
                  return;
                }
                if (i < etapa) setEtapa(i);
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                i === etapa
                  ? "bg-blue-600 text-white"
                  : i < etapa
                  ? "bg-blue-100 text-blue-700 cursor-pointer hover:bg-blue-200"
                  : "bg-gray-100 text-gray-400 cursor-default"
              }`}
            >
              {i < etapa ? <CheckCircle size={12} /> : null}
              {i + 1}. {nome}
            </button>
            {i < ETAPAS.length - 1 && <ChevronRight size={14} className="text-gray-300" />}
          </div>
        ))}
      </div>

      {/* Erro */}
      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
          <button className="ml-auto" onClick={() => setErro(null)}><X size={14} /></button>
        </div>
      )}

      {sucesso && (
        <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm">
          <CheckCircle size={16} />
          <span>{sucesso}</span>
          <button className="ml-auto" onClick={() => setSucesso(null)}><X size={14} /></button>
        </div>
      )}

      {/* =========== ETAPA 1: TRIAGEM =========== */}
      {etapa === 0 && (
        <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
          <h2 className="font-semibold text-gray-700">Triagem inicial</h2>

          <div className="grid grid-cols-2 gap-4">
            {campo("Tutor (nome/telefone)", true)(
              <div className="relative">
                <input
                  type="text"
                  value={buscaTutor}
                  onChange={(e) => {
                    setBuscaTutor(e.target.value);
                    if (tutorSelecionado) {
                      setTutorSelecionado(null);
                      set("pet_id", "");
                    }
                  }}
                  placeholder="Digite nome ou telefone do tutor..."
                  className={css.input}
                  disabled={isEdicao}
                />
                {!isEdicao && tutorSelecionado && (
                  <button
                    type="button"
                    onClick={limparTutor}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700"
                  >
                    limpar
                  </button>
                )}

                {!isEdicao && buscaTutor.trim().length >= 1 && !tutorSelecionado && tutoresSugeridos.length > 0 && (
                  <div className="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
                    {tutoresSugeridos.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => selecionarTutor(t)}
                        className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b last:border-b-0"
                      >
                        <div className="text-sm font-medium text-gray-800">{t.nome}</div>
                        <div className="text-xs text-gray-500">
                          {[t.telefone, t.celular].filter(Boolean).join(" • ") || "Sem telefone"}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {campo("Veterinário")(
              <select value={form.veterinario_id} onChange={(e) => set("veterinario_id", e.target.value)} className={css.select}>
                <option value="">Selecione…</option>
                {veterinarios.map((v) => (
                  <option key={v.id} value={v.id}>{v.nome}</option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              {campo("Pet", true)(
              <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
                <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-3 py-2">
                  <button
                    type="button"
                    onClick={() => tutorSelecionado && setListaPetsExpandida((prev) => !prev)}
                    disabled={!tutorSelecionado || isEdicao}
                    className="flex-1 text-left text-sm disabled:opacity-60"
                  >
                    <span>{petSelecionadoLabel}</span>
                  </button>
                  <NovoPetButton
                    tutorId={tutorSelecionado?.id}
                    tutorNome={tutorSelecionado?.nome}
                    onClick={abrirModalNovoPet}
                  />
                  <span className="text-gray-500 text-xs">
                    {tutorSelecionado ? `${petsDoTutor.length} pet(s)` : "Sem tutor"}
                  </span>
                </div>

                {listaPetsExpandida && tutorSelecionado && !isEdicao && (
                  <div className="border-t border-gray-200 max-h-52 overflow-y-auto p-2 space-y-1">
                    {petsDoTutor.map((p) => {
                      const ativo = String(form.pet_id) === String(p.id);
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => {
                            set("pet_id", p.id);
                            setListaPetsExpandida(false);
                          }}
                          className={`w-full text-left px-2.5 py-2 rounded text-sm transition-colors ${
                            ativo ? "bg-blue-50 border border-blue-200 text-blue-700" : "hover:bg-gray-50"
                          }`}
                        >
                          <div className="font-medium">{p.nome}</div>
                          <div className="text-xs text-gray-500">
                            {p.especie && !/\?/.test(p.especie) ? p.especie : "Pet"}
                            {p.codigo ? ` • ${p.codigo}` : ""}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
              )}
            </div>
          </div>

          {!isEdicao && tutorSelecionado && petsDoTutor.length === 0 && (
            <p className="text-xs text-amber-600">
              Nenhum pet ativo vinculado a esse tutor.
            </p>
          )}

          {campo("Motivo da consulta", true)(
            <textarea
              value={form.motivo_consulta}
              onChange={(e) => set("motivo_consulta", e.target.value)}
              className={css.textarea}
              placeholder="Descreva o motivo da consulta…"
            />
          )}

          <h3 className="text-sm font-medium text-gray-500 pt-2">Sinais vitais</h3>
          <div className="grid grid-cols-3 gap-3">
            {campo("Peso (kg)")(
              <input type="number" step="0.1" value={form.peso_kg} onChange={(e) => set("peso_kg", e.target.value)} className={css.input} placeholder="ex: 12,5" />
            )}
            {campo("Temperatura (°C)")(
              <input type="number" step="0.1" value={form.temperatura} onChange={(e) => set("temperatura", e.target.value)} className={css.input} placeholder="ex: 38,5" />
            )}
            {campo("FC (bpm)")(
              <input type="number" value={form.freq_cardiaca} onChange={(e) => set("freq_cardiaca", e.target.value)} className={css.input} placeholder="ex: 80" />
            )}
            {campo("FR (rpm)")(
              <input type="number" value={form.freq_respiratoria} onChange={(e) => set("freq_respiratoria", e.target.value)} className={css.input} placeholder="ex: 20" />
            )}
            {campo("TPC")(
              <input type="text" value={form.tpc} onChange={(e) => set("tpc", e.target.value)} className={css.input} placeholder="ex: < 2 seg" />
            )}
            {campo("Mucosa")(
              <select value={form.mucosa} onChange={(e) => set("mucosa", e.target.value)} className={css.select}>
                <option value="">—</option>
                <option>Rósea</option><option>Pálida</option><option>Ictérica</option>
                <option>Cianótica</option><option>Hiperêmica</option>
              </select>
            )}
            {campo("Hidratação")(
              <select value={form.estado_hidratacao} onChange={(e) => set("estado_hidratacao", e.target.value)} className={css.select}>
                <option value="">—</option>
                <option>Normal</option><option>Leve desidratação</option>
                <option>Moderada desidratação</option><option>Grave desidratação</option>
              </select>
            )}
            {campo("Consciência")(
              <select value={form.nivel_consciencia} onChange={(e) => set("nivel_consciencia", e.target.value)} className={css.select}>
                <option value="">—</option>
                <option>Alerta</option><option>Deprimido</option><option>Estupor</option><option>Coma</option>
              </select>
            )}
            {campo("Dor (0–10)")(
              <input type="number" min={0} max={10} value={form.nivel_dor} onChange={(e) => set("nivel_dor", e.target.value)} className={css.input} placeholder="0 = sem dor" />
            )}
          </div>
        </fieldset>
      )}

      {/* =========== ETAPA 2: EXAME CLÍNICO =========== */}
      {etapa === 1 && (
        <>
          <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
            <h2 className="font-semibold text-gray-700">Exame clínico</h2>
            {campo("Histórico clínico")(
              <textarea
                value={form.historico_clinico}
                onChange={(e) => set("historico_clinico", e.target.value)}
                className={css.textarea}
                placeholder="Histórico médico, cirurgias anteriores, medicações em uso…"
              />
            )}
            {campo("Exame físico detalhado")(
              <textarea
                value={form.exame_fisico}
                onChange={(e) => set("exame_fisico", e.target.value)}
                className={css.textarea}
                style={{ minHeight: 200 }}
                placeholder="Descrição sistemática: cabeça, tórax, abdômen, membros, pele…"
              />
            )}
          </fieldset>

          <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-blue-900">Exames ligados a esta consulta</h3>
                <p className="text-xs text-blue-700">
                  Cadastre o exame já com anexo e mantenha a IA olhando o mesmo caso clínico.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setModalNovoExameAberto(true)}
                  disabled={modoSomenteLeitura || !form.pet_id || !consultaIdAtual}
                  className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-60"
                >
                  <FlaskConical size={15} />
                  Novo exame / anexo
                </button>
                {consultaIdAtual && (
                  <button
                    type="button"
                    onClick={() => abrirFluxoConsulta("/veterinario/exames", { acao: "novo" })}
                    className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100"
                  >
                    Ver tela de exames
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Painel chat IA de exames */}
          <ExameChatIAAvancada
            petId={form.pet_id}
            refreshToken={refreshExamesToken}
            onNovoExame={() => setModalNovoExameAberto(true)}
          />
        </>
      )}

      {/* =========== ETAPA 3: DIAGNÓSTICO =========== */}
      {etapa === 2 && (
        <div className="space-y-4">
          <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
            <h2 className="font-semibold text-gray-700">Diagnóstico e tratamento</h2>
            {campo("Diagnóstico")(
              <textarea value={form.diagnostico} onChange={(e) => set("diagnostico", e.target.value)} className={css.textarea} placeholder="Diagnóstico principal e diferenciais…" />
            )}
            {campo("Prognóstico")(
              <select value={form.prognostico} onChange={(e) => set("prognostico", e.target.value)} className={css.select}>
                <option value="">—</option>
                <option>Favorável</option><option>Reservado</option><option>Grave</option><option>Desfavorável</option>
              </select>
            )}
            {campo("Tratamento prescrito")(
              <textarea value={form.tratamento} onChange={(e) => set("tratamento", e.target.value)} className={css.textarea} placeholder="Protocolo terapêutico, cuidados em casa…" />
            )}
            <div className="grid grid-cols-2 gap-3">
              {campo("Retorno em (dias)")(
                <input type="number" value={form.retorno_em_dias} onChange={(e) => set("retorno_em_dias", e.target.value)} className={css.input} placeholder="ex: 15" />
              )}
            </div>
            {campo("Observações adicionais")(
              <textarea value={form.observacoes} onChange={(e) => set("observacoes", e.target.value)} className={css.textarea} placeholder="Observações para o tutor, cuidados especiais…" />
            )}
          </fieldset>

          {/* Prescrição */}
          <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 disabled:opacity-100">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-700">Prescrição (opcional)</h2>
              <button
                onClick={adicionarItem}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                + Adicionar medicamento
              </button>
            </div>
            {form.prescricao_itens.length === 0 && (
              <p className="text-xs text-gray-400">Nenhum medicamento adicionado ainda.</p>
            )}
            {form.prescricao_itens.map((item, idx) => (
              <div key={idx} className="border border-gray-100 rounded-lg p-3 space-y-2 relative">
                <button
                  onClick={() => removerItem(idx)}
                  className="absolute top-2 right-2 text-gray-300 hover:text-red-400"
                >
                  <X size={14} />
                </button>
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={item.medicamento_id || ""}
                    onChange={(e) => selecionarMedicamentoNoItem(idx, e.target.value)}
                    className={css.select}
                  >
                    <option value="">Selecionar do catálogo…</option>
                    {medicamentosCatalogo.map((m) => (
                      <option key={m.id} value={m.id}>{m.nome}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => recalcularDoseItem(idx)}
                    className="inline-flex items-center justify-center gap-2 px-3 py-2 text-xs border border-blue-200 text-blue-700 rounded-lg hover:bg-blue-50"
                  >
                    <Calculator size={14} />
                    Calcular dose pelo peso
                  </button>
                </div>
                {(item.dose_minima_mg_kg || item.dose_maxima_mg_kg) && (
                  <p className="text-[11px] text-gray-500">
                    Referência do catálogo: {item.dose_minima_mg_kg || "—"}
                    {item.dose_maxima_mg_kg ? ` a ${item.dose_maxima_mg_kg}` : ""} mg/kg
                  </p>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <input type="text" placeholder="Nome do medicamento" value={item.nome} onChange={(e) => setItem(idx, "nome", e.target.value)} className={css.input} />
                  <input type="text" placeholder="Princípio ativo" value={item.principio_ativo} onChange={(e) => setItem(idx, "principio_ativo", e.target.value)} className={css.input} />
                  <input type="text" placeholder="Dose (ex: 10 mg/kg)" value={item.dose_mg} onChange={(e) => setItem(idx, "dose_mg", e.target.value)} className={css.input} />
                  <select value={item.via} onChange={(e) => setItem(idx, "via", e.target.value)} className={css.select}>
                    <option value="oral">Oral</option>
                    <option value="iv">IV</option><option value="im">IM</option>
                    <option value="sc">SC</option><option value="topico">Tópico</option>
                    <option value="oftalmico">Oftálmico</option>
                  </select>
                  <input type="text" placeholder="Frequência (ex: a cada 12h)" value={item.frequencia} onChange={(e) => setItem(idx, "frequencia", e.target.value)} className={css.input} />
                  <input type="number" placeholder="Duração (dias)" value={item.duracao_dias} onChange={(e) => setItem(idx, "duracao_dias", e.target.value)} className={css.input} />
                </div>
                <input type="text" placeholder="Instruções ao tutor" value={item.instrucoes} onChange={(e) => setItem(idx, "instrucoes", e.target.value)} className={css.input} />
              </div>
            ))}
          </fieldset>

          <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 disabled:opacity-100">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-700">Procedimentos realizados</h2>
              <div className="flex flex-wrap items-center gap-3">
                <button onClick={adicionarProcedimento} className="text-xs text-blue-600 hover:text-blue-800 underline">
                  + Adicionar procedimento
                </button>
                <button
                  type="button"
                  onClick={abrirModalInsumoRapido}
                  disabled={!consultaIdAtual}
                  className="text-xs text-emerald-600 hover:text-emerald-800 underline disabled:opacity-50"
                >
                  + Lançar insumo rápido
                </button>
              </div>
            </div>
            {form.procedimentos_realizados.length === 0 && (
              <p className="text-xs text-gray-400">Nenhum procedimento lançado ainda.</p>
            )}
            {form.procedimentos_realizados.map((item, idx) => (
              <div key={`procedimento_${idx}`} className="border border-gray-100 rounded-lg p-3 space-y-2 relative">
                <button onClick={() => removerProcedimento(idx)} className="absolute top-2 right-2 text-gray-300 hover:text-red-400">
                  <X size={14} />
                </button>
                {(() => {
                  const resumo = obterResumoProcedimentoSelecionado(item, procedimentosCatalogo);
                  return (
                    <>
                <div className="grid grid-cols-2 gap-2">
                  <select value={item.catalogo_id || ""} onChange={(e) => selecionarProcedimentoCatalogo(idx, e.target.value)} className={css.select}>
                    <option value="">Selecionar do catálogo…</option>
                    {procedimentosCatalogo.map((proc) => (
                      <option key={proc.id} value={proc.id}>{proc.nome}</option>
                    ))}
                  </select>
                  <input type="text" placeholder="Nome do procedimento" value={item.nome} onChange={(e) => setProcedimentoItem(idx, "nome", e.target.value)} className={css.input} />
                  <input type="text" placeholder="Descrição" value={item.descricao} onChange={(e) => setProcedimentoItem(idx, "descricao", e.target.value)} className={css.input} />
                  <input type="text" placeholder="Valor" value={item.valor} onChange={(e) => setProcedimentoItem(idx, "valor", e.target.value)} className={css.input} />
                </div>
                <input type="text" placeholder="Observações" value={item.observacoes} onChange={(e) => setProcedimentoItem(idx, "observacoes", e.target.value)} className={css.input} />
                {resumo.possuiCatalogo && (
                  <div className="grid grid-cols-3 gap-2 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-gray-400">Cobrado</p>
                      <p className="text-sm font-semibold text-gray-800">{formatMoneyBRL(resumo.valorCobrado)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo est.</p>
                      <p className="text-sm font-semibold text-amber-700">{formatMoneyBRL(resumo.custoTotal)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem est.</p>
                      <p className={`text-sm font-semibold ${resumo.margemValor < 0 ? "text-red-600" : "text-emerald-700"}`}>
                        {formatMoneyBRL(resumo.margemValor)}
                      </p>
                      <p className="text-[11px] text-gray-400">{formatPercent(resumo.margemPercentual)}</p>
                    </div>
                  </div>
                )}
                <label className="flex items-center gap-2 text-xs text-gray-600">
                  <input type="checkbox" checked={item.baixar_estoque !== false} onChange={(e) => setProcedimentoItem(idx, "baixar_estoque", e.target.checked)} />
                  Baixar estoque automático dos insumos vinculados
                </label>
                    </>
                  );
                })()}
              </div>
            ))}
          </fieldset>

          <div className="rounded-xl border border-purple-100 bg-purple-50 px-4 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-purple-900">Fluxos vinculados à consulta</h3>
                <p className="text-xs text-purple-700">
                  Use a consulta #{consultaIdAtual || "—"} como referência para exames, vacinas, IA e internação.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => abrirFluxoConsulta("/veterinario/assistente-ia")}
                  disabled={!consultaIdAtual}
                  className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
                >
                  <MessageSquare size={15} />
                  IA da consulta
                </button>
                <button
                  type="button"
                  onClick={() => abrirFluxoConsulta("/veterinario/vacinas", { acao: "novo" })}
                  disabled={!consultaIdAtual}
                  className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
                >
                  <Syringe size={15} />
                  Registrar vacina
                </button>
                <button
                  type="button"
                  onClick={() => abrirFluxoConsulta("/veterinario/internacoes", { abrir_nova: "1" })}
                  disabled={!consultaIdAtual}
                  className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
                >
                  <BedDouble size={15} />
                  Encaminhar para internação
                </button>
              </div>
            </div>
            {!consultaIdAtual && (
              <p className="mt-3 text-xs text-purple-700">
                Salve o rascunho primeiro para liberar os outros fluxos já amarrados a esta consulta.
              </p>
            )}
          </div>

          <TimelineConsultaPanel
            consultaIdAtual={consultaIdAtual}
            carregandoTimeline={carregandoTimeline}
            timelineConsulta={timelineConsulta}
            onRefresh={() => carregarTimelineConsulta()}
            onOpenLink={(link) => navigate(link)}
          />
        </div>
      )}

      {/* Rodapé de ações */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => navigate(-1)}
          className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancelar
        </button>

        <div className="flex gap-3">
          {modoSomenteLeitura ? (
            <button
              onClick={() => navigate("/veterinario/consultas")}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              Voltar para consultas
            </button>
          ) : (
            <>
          {etapa > 0 && (
            <button
              onClick={() => setEtapa((e) => e - 1)}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              ← Voltar
            </button>
          )}

          {etapa < ETAPAS.length - 1 ? (
            <button
              onClick={salvarRascunho}
              disabled={salvando}
              className="flex items-center gap-2 px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
            >
              <Save size={14} />
              {salvando ? "Salvando…" : "Salvar e continuar"}
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={salvarRascunho}
                disabled={salvando}
                className="flex items-center gap-2 px-4 py-2 text-sm border border-blue-300 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-60"
              >
                <Save size={14} />
                {salvando ? "Salvando…" : "Salvar rascunho"}
              </button>
              <button
                onClick={finalizar}
                disabled={salvando || !form.diagnostico}
                className="flex items-center gap-2 px-5 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60"
                title={!form.diagnostico ? "Preencha o diagnóstico para finalizar" : ""}
              >
                <Lock size={14} />
                {salvando ? "Finalizando…" : "Dar alta / finalizar"}
              </button>
            </div>
          )}
            </>
          )}
        </div>
      </div>

      <InsumoRapidoModal
        isOpen={modalInsumoAberto}
        onClose={() => setModalInsumoAberto(false)}
        css={css}
        consultaIdAtual={consultaIdAtual}
        petSelecionadoLabel={petSelecionadoLabel}
        insumoSelecionado={insumoRapidoSelecionado}
        setInsumoSelecionado={setInsumoRapidoSelecionado}
        insumoForm={insumoRapidoForm}
        setInsumoForm={setInsumoRapidoForm}
        salvarInsumo={salvarInsumoRapidoConsulta}
        salvandoInsumo={salvandoInsumoRapido}
      />

      <NovoPetModal
        isOpen={modalNovoPetAberto}
        tutor={tutorSelecionado}
        sugestoesEspecies={sugestoesEspecies}
        onClose={() => setModalNovoPetAberto(false)}
        onCreated={handleNovoPetCriado}
      />

      <CalculadoraDoseModal
        isOpen={modalCalculadoraAberto}
        onClose={() => setModalCalculadoraAberto(false)}
        css={css}
        petSelecionadoLabel={petSelecionadoLabel}
        calculadoraForm={calculadoraForm}
        setCalculadoraForm={setCalculadoraForm}
        medicamentosCatalogo={medicamentosCatalogo}
        medicamentoSelecionado={medicamentoCalculadoraSelecionado}
        resultado={calculadoraResultado}
      />

      <NovoExameConsultaModal
        isOpen={modalNovoExameAberto}
        onClose={() => setModalNovoExameAberto(false)}
        css={css}
        consultaIdAtual={consultaIdAtual}
        petSelecionadoLabel={petSelecionadoLabel}
        petId={form.pet_id}
        novoExameForm={novoExameForm}
        setNovoExameForm={setNovoExameForm}
        setNovoExameArquivo={setNovoExameArquivo}
        salvarNovoExameRapido={salvarNovoExameRapido}
        salvandoNovoExame={salvandoNovoExame}
      />
    </div>
  );
}
