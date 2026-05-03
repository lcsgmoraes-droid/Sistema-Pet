import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { AlertTriangle, CalendarDays, Clock3, Plus, RefreshCw, UsersRound } from "lucide-react";
import { useLocation, useSearchParams } from "react-router-dom";
import ActionButton from "../../../components/ui/ActionButton";
import { api } from "../../../services/api";
import MetricCard from "../../../components/ui/MetricCard";
import MetricGrid from "../../../components/ui/MetricGrid";
import Panel from "../../../components/ui/Panel";
import { buildReturnTo } from "../../../utils/petReturnFlow";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaAgendaCriacaoPanel from "./BanhoTosaAgendaCriacaoPanel";
import BanhoTosaAgendaList from "./BanhoTosaAgendaList";
const todayIso = () => new Date().toISOString().slice(0, 10);
const criarFormularioInicial = () => ({
  pet_id: "",
  hora: "09:00",
  recurso_id: "",
  servico_id: "",
  valor_unitario: "0",
  observacoes: "",
});
export default function BanhoTosaAgendaView({ recursos = [], servicos, onChanged }) {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [dataRef, setDataRef] = useState(todayIso());
  const [agendamentos, setAgendamentos] = useState([]);
  const [capacidade, setCapacidade] = useState(null);
  const [sugestoes, setSugestoes] = useState([]);
  const [loadingAgenda, setLoadingAgenda] = useState(false);
  const [loadingSugestoes, setLoadingSugestoes] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [petsDoTutor, setPetsDoTutor] = useState([]);
  const [loadingPets, setLoadingPets] = useState(false);
  const [form, setForm] = useState(criarFormularioInicial);
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const retornoNovoPet = useMemo(
    () =>
      buildReturnTo(location.pathname, location.search, {
        novo_pet_id: null,
        novo_pet_nome: null,
        tutor_id: tutorSelecionado?.id || null,
        tutor_nome: tutorSelecionado?.nome || null,
      }),
    [location.pathname, location.search, tutorSelecionado?.id, tutorSelecionado?.nome]
  );
  const agendaResumo = useMemo(
    () => resumirAgenda(agendamentos, capacidade, recursos),
    [agendamentos, capacidade, recursos],
  );

  async function carregarAgenda() {
    setLoadingAgenda(true);
    try {
      const [agendaRes, capacidadeRes] = await Promise.all([
        banhoTosaApi.listarAgendamentos({
          data_inicio: dataRef,
          data_fim: dataRef,
        }),
        banhoTosaApi.obterCapacidadeAgenda(dataRef),
      ]);
      setAgendamentos(Array.isArray(agendaRes.data) ? agendaRes.data : []);
      setCapacidade(capacidadeRes.data || null);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar a agenda."));
      setAgendamentos([]);
      setCapacidade(null);
    } finally {
      setLoadingAgenda(false);
    }
  }

  useEffect(() => {
    carregarAgenda();
  }, [dataRef]);

  useEffect(() => {
    carregarSugestoes();
  }, [dataRef, form.servico_id, form.recurso_id, servicos.length]);

  useEffect(() => {
    if (!tutorIdQuery) return;
    setTutorSelecionado((prev) => {
      if (prev?.id && String(prev.id) === String(tutorIdQuery)) return prev;
      return {
        id: tutorIdQuery,
        nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
      };
    });
    if (novoPetIdQuery) {
      setForm((prev) => (
        String(prev.pet_id) === String(novoPetIdQuery)
          ? prev
          : { ...prev, pet_id: "" }
      ));
    }
  }, [novoPetIdQuery, tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    if (!tutorSelecionado?.id) {
      setPetsDoTutor([]);
      setForm((prev) => ({ ...prev, pet_id: "" }));
      return;
    }

    let active = true;
    carregarPetsTutor(tutorSelecionado.id, () => active);
    return () => {
      active = false;
    };
  }, [tutorSelecionado?.id]);

  useEffect(() => {
    if (!novoPetIdQuery || !petsDoTutor.length) return;
    const petCriado = petsDoTutor.find((pet) => String(pet.id) === String(novoPetIdQuery));
    if (!petCriado) return;
    setForm((prev) => {
      if (String(prev.pet_id) === String(petCriado.id)) return prev;
      return { ...prev, pet_id: String(petCriado.id) };
    });
  }, [novoPetIdQuery, petsDoTutor]);

  async function carregarPetsTutor(tutorId, isActive) {
    setLoadingPets(true);
    try {
      const response = await api.get("/vet/pets", {
        params: { cliente_id: tutorId, limit: 100 },
      });
      if (!isActive()) return;
      const lista = response.data?.items ?? response.data ?? [];
      setPetsDoTutor(Array.isArray(lista) ? lista : []);
    } catch {
      if (isActive()) {
        setPetsDoTutor([]);
      }
    } finally {
      if (isActive()) {
        setLoadingPets(false);
      }
    }
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function selecionarTutorAgenda(tutor) {
    setTutorSelecionado(tutor);
    setForm((prev) => ({ ...prev, pet_id: "" }));
  }

  function onServicoChange(servicoId) {
    const servico = servicos.find((item) => String(item.id) === String(servicoId));
    setForm((prev) => ({
      ...prev,
      servico_id: servicoId,
      valor_unitario: servico ? String(servico.preco_base ?? "0") : prev.valor_unitario,
    }));
  }

  function resetarFormularioAgendamento() {
    setTutorSelecionado(null);
    setPetsDoTutor([]);
    setForm(criarFormularioInicial());
  }

  function abrirNovoAgendamento() {
    setFormOpen(true);
  }

  async function carregarSugestoes() {
    setLoadingSugestoes(true);
    try {
      const response = await banhoTosaApi.listarSugestoesSlots({
        data_referencia: dataRef,
        duracao_minutos: duracaoSelecionada(),
        recurso_id: form.recurso_id || undefined,
        limit: 50,
      });
      setSugestoes(Array.isArray(response.data) ? response.data : []);
    } catch {
      setSugestoes([]);
    } finally {
      setLoadingSugestoes(false);
    }
  }

  async function criarAgendamento(event) {
    event.preventDefault();

    if (!tutorSelecionado?.id || !form.pet_id || !form.hora) {
      toast.error("Selecione tutor, pet e horario.");
      return;
    }

    const servico = servicos.find((item) => String(item.id) === String(form.servico_id));
    setSaving(true);
    try {
      await banhoTosaApi.criarAgendamento({
        cliente_id: Number(tutorSelecionado.id),
        pet_id: Number(form.pet_id),
        data_hora_inicio: `${dataRef}T${form.hora}:00`,
        recurso_id: form.recurso_id ? Number(form.recurso_id) : null,
        origem: "balcao",
        observacoes: form.observacoes || null,
        servicos: [montarServicoPayload(servico)],
      });

      toast.success("Agendamento criado.");
      resetarFormularioAgendamento();
      setFormOpen(false);
      await carregarAgenda();
      await carregarSugestoes();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel criar o agendamento."));
    } finally {
      setSaving(false);
    }
  }

  function montarServicoPayload(servico) {
    return {
      servico_id: servico ? Number(servico.id) : null,
      nome_servico: servico ? null : "Banho & Tosa",
      quantidade: "1",
      valor_unitario: toApiDecimal(form.valor_unitario || servico?.preco_base || "0"),
      desconto: "0",
      tempo_previsto_minutos: servico?.duracao_padrao_minutos || 60,
    };
  }

  function duracaoSelecionada() {
    const servico = servicos.find((item) => String(item.id) === String(form.servico_id));
    return servico?.duracao_padrao_minutos || 60;
  }

  function usarSlot(slot) {
    setForm((prev) => ({
      ...prev,
      hora: String(slot.horario_inicio || "").slice(11, 16),
      recurso_id: String(slot.recurso_id || ""),
    }));
    toast.success("Horario sugerido aplicado.");
  }

  async function checkIn(agendamento) {
    try {
      await banhoTosaApi.checkInAgendamento(agendamento.id);
      toast.success("Check-in realizado.");
      await carregarAgenda();
      await carregarSugestoes();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel fazer check-in."));
    }
  }

  async function cancelar(agendamento) {
    try {
      await banhoTosaApi.atualizarStatusAgendamento(agendamento.id, {
        status: "cancelado",
      });
      toast.success("Agendamento cancelado.");
      await carregarAgenda();
      await carregarSugestoes();
      await onChanged(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel cancelar."));
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        actions={
          <>
            <ActionButton icon={RefreshCw} intent="neutral" onClick={carregarAgenda} tone="soft">
              Atualizar
            </ActionButton>
            <ActionButton icon={Plus} intent="create" onClick={abrirNovoAgendamento}>
              Agendar
            </ActionButton>
          </>
        }
        subtitle="Acompanhe o dia antes de abrir um novo cadastro."
        title="Agenda de Banho & Tosa"
      >
        <div className="mb-3 max-w-xs">
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Data da agenda
          </label>
          <input
            className="h-9 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            onChange={(event) => setDataRef(event.target.value)}
            type="date"
            value={dataRef}
          />
        </div>
        <MetricGrid>
          <MetricCard
            icon={<CalendarDays size={18} />}
            intent="blue"
            label="Agendamentos"
            subtitle="Dia selecionado"
            value={agendaResumo.total}
          />
          <MetricCard
            icon={<Clock3 size={18} />}
            intent="amber"
            label="Em andamento"
            subtitle="Check-in ou atendimento"
            value={agendaResumo.emAndamento}
          />
          <MetricCard
            icon={<UsersRound size={18} />}
            intent="emerald"
            label="Recursos ativos"
            subtitle="Boxes/equipe disponiveis"
            value={agendaResumo.recursosAtivos}
          />
          <MetricCard
            intent="slate"
            label="Capacidade"
            subtitle={`${capacidade?.janela_inicio || "08:00"} as ${capacidade?.janela_fim || "18:00"}`}
            value={`${agendaResumo.ocupacao}%`}
          />
        </MetricGrid>
      </Panel>

      <BanhoTosaAgendaCriacaoPanel
        agendamentos={agendamentos}
        capacidade={capacidade}
        dataRef={dataRef}
        form={form}
        isOpen={formOpen}
        loadingAgenda={loadingAgenda}
        loadingPets={loadingPets}
        loadingSugestoes={loadingSugestoes}
        petsDoTutor={petsDoTutor}
        recursos={recursos}
        retornoNovoPet={retornoNovoPet}
        saving={saving}
        servicos={servicos}
        sugestoes={sugestoes}
        tutorSelecionado={tutorSelecionado}
        onChangeData={setDataRef}
        onChangeField={updateField}
        onChangeServico={onServicoChange}
        onClose={() => setFormOpen(false)}
        onSelectTutor={selecionarTutorAgenda}
        onSubmit={criarAgendamento}
        onUseSlot={usarSlot}
      />

      <CapacidadeAlertas capacidade={capacidade} />

      <BanhoTosaAgendaList
        agendamentos={agendamentos}
        dataRef={dataRef}
        loading={loadingAgenda}
        onAtualizar={carregarAgenda}
        onCancelar={cancelar}
        onCheckIn={checkIn}
      />
    </div>
  );
}

function CapacidadeAlertas({ capacidade }) {
  const alertas = capacidade?.alertas || [];
  if (!alertas.length) return null;

  return (
    <Panel className="border-amber-200 bg-amber-50" padding="sm">
      <div className="flex items-start gap-2 text-sm font-medium text-amber-800">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" />
        <div className="space-y-1">
          {alertas.map((alerta) => (
            <p key={alerta}>{alerta}</p>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function resumirAgenda(agendamentos, capacidade, recursos) {
  const emAndamento = agendamentos.filter((agendamento) =>
    ["check_in", "em_atendimento", "em_execucao"].includes(String(agendamento.status || "").toLowerCase()),
  ).length;
  const recursosAtivos = recursos.filter((recurso) => recurso.ativo).length;
  const recursosCapacidade = capacidade?.recursos || [];
  const ocupacao = recursosCapacidade.length
    ? Math.round(
        recursosCapacidade.reduce(
          (acc, recurso) => acc + Number(recurso.ocupacao_percentual || 0),
          0,
        ) / recursosCapacidade.length,
      )
    : 0;

  return {
    emAndamento,
    ocupacao,
    recursosAtivos,
    total: agendamentos.length,
  };
}
