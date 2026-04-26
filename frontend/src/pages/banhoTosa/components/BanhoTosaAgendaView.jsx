import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../../../services/api";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaAgendaCriacaoPanel from "./BanhoTosaAgendaCriacaoPanel";
import BanhoTosaAgendaGrade from "./BanhoTosaAgendaGrade";
import BanhoTosaAgendaList from "./BanhoTosaAgendaList";
import BanhoTosaCapacidadePanel from "./BanhoTosaCapacidadePanel";
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
  const [dataRef, setDataRef] = useState(todayIso());
  const [agendamentos, setAgendamentos] = useState([]);
  const [capacidade, setCapacidade] = useState(null);
  const [sugestoes, setSugestoes] = useState([]);
  const [loadingAgenda, setLoadingAgenda] = useState(false);
  const [loadingSugestoes, setLoadingSugestoes] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tutorSelecionado, setTutorSelecionado] = useState(null);
  const [petsDoTutor, setPetsDoTutor] = useState([]);
  const [loadingPets, setLoadingPets] = useState(false);
  const [form, setForm] = useState(criarFormularioInicial);
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

  function onServicoChange(servicoId) {
    setForm((prev) => ({ ...prev, servico_id: servicoId }));
  }

  function resetarFormularioAgendamento() {
    setTutorSelecionado(null);
    setPetsDoTutor([]);
    setForm(criarFormularioInicial());
  }

  async function carregarSugestoes() {
    setLoadingSugestoes(true);
    try {
      const response = await banhoTosaApi.listarSugestoesSlots({
        data_referencia: dataRef,
        duracao_minutos: duracaoSelecionada(),
        recurso_id: form.recurso_id || undefined,
        limit: 18,
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
      valor_unitario: toApiDecimal(form.valor_unitario),
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
    <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
      <BanhoTosaAgendaCriacaoPanel
        dataRef={dataRef}
        form={form}
        loadingPets={loadingPets}
        loadingSugestoes={loadingSugestoes}
        petsDoTutor={petsDoTutor}
        recursos={recursos}
        saving={saving}
        servicos={servicos}
        sugestoes={sugestoes}
        tutorSelecionado={tutorSelecionado}
        onChangeData={setDataRef}
        onChangeField={updateField}
        onChangeServico={onServicoChange}
        onSelectTutor={setTutorSelecionado}
        onSubmit={criarAgendamento}
        onUseSlot={usarSlot}
      />

      <BanhoTosaAgendaList
        agendamentos={agendamentos}
        dataRef={dataRef}
        loading={loadingAgenda}
        onAtualizar={carregarAgenda}
        onCancelar={cancelar}
        onCheckIn={checkIn}
      />

      <div className="xl:col-span-2">
        <BanhoTosaAgendaGrade
          agendamentos={agendamentos}
          capacidade={capacidade}
          recursos={recursos}
          sugestoes={sugestoes}
          onUseSlot={usarSlot}
        />
      </div>

      <div className="xl:col-span-2">
        <BanhoTosaCapacidadePanel capacidade={capacidade} />
      </div>
    </div>
  );
}
