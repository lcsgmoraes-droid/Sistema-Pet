import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { banhoTosaApi } from "../banhoTosaApi";
import { getApiErrorMessage, toApiDecimal } from "../banhoTosaUtils";
import BanhoTosaTaxiDogForm from "./BanhoTosaTaxiDogForm";
import BanhoTosaTaxiDogList from "./BanhoTosaTaxiDogList";

const todayIso = () => new Date().toISOString().slice(0, 10);

const initialForm = {
  agendamento_id: "",
  tipo: "ida_volta",
  motorista_id: "",
  janela_inicio: "",
  janela_fim: "",
  km_estimado: "0",
  km_real: "0",
  valor_cobrado: "0",
  custo_estimado: "0",
  custo_real: "0",
  endereco_origem: "",
  endereco_destino: "",
};

export default function BanhoTosaTaxiDogView({ funcionarios = [], onChanged }) {
  const [dataRef, setDataRef] = useState(todayIso());
  const [taxiDog, setTaxiDog] = useState([]);
  const [agendamentos, setAgendamentos] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  async function carregarDados() {
    setLoading(true);
    try {
      const [taxiRes, agendaRes] = await Promise.all([
        banhoTosaApi.listarTaxiDog({ data_inicio: dataRef, data_fim: dataRef }),
        banhoTosaApi.listarAgendamentos({ data_inicio: dataRef, data_fim: dataRef }),
      ]);
      setTaxiDog(Array.isArray(taxiRes.data) ? taxiRes.data : []);
      setAgendamentos(Array.isArray(agendaRes.data) ? agendaRes.data : []);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel carregar taxi dog."));
      setTaxiDog([]);
      setAgendamentos([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregarDados();
  }, [dataRef]);

  function updateField(field, value) {
    if (field === "agendamento_id") {
      const agendamento = agendamentos.find((item) => String(item.id) === String(value));
      setForm((prev) => ({
        ...prev,
        agendamento_id: value,
        janela_inicio: agendamento ? toDateTimeInput(addMinutes(agendamento.data_hora_inicio, -60)) : prev.janela_inicio,
        janela_fim: agendamento ? toDateTimeInput(agendamento.data_hora_inicio) : prev.janela_fim,
      }));
      return;
    }
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function criarTaxiDog(event) {
    event.preventDefault();
    if (!form.agendamento_id) {
      toast.error("Selecione um agendamento para vincular o taxi dog.");
      return;
    }

    setSaving(true);
    try {
      await banhoTosaApi.criarTaxiDog(montarPayload());
      toast.success("Taxi dog criado.");
      setForm(initialForm);
      await carregarDados();
      await onChanged?.(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel criar taxi dog."));
    } finally {
      setSaving(false);
    }
  }

  async function atualizarStatus(item, status) {
    setSaving(true);
    try {
      await banhoTosaApi.atualizarStatusTaxiDog(item.id, { status });
      toast.success("Status atualizado.");
      await carregarDados();
      await onChanged?.(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel atualizar status."));
    } finally {
      setSaving(false);
    }
  }

  async function salvarMedicao(item) {
    setSaving(true);
    try {
      await banhoTosaApi.atualizarTaxiDog(item.id, {
        km_real: item.km_real,
        custo_real: item.custo_real,
      });
      toast.success("Medicao salva.");
      await carregarDados();
      await onChanged?.(true);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Nao foi possivel salvar medicao."));
    } finally {
      setSaving(false);
    }
  }

  function montarPayload() {
    return {
      agendamento_id: Number(form.agendamento_id),
      tipo: form.tipo,
      motorista_id: form.motorista_id ? Number(form.motorista_id) : null,
      janela_inicio: normalizarDateTime(form.janela_inicio),
      janela_fim: normalizarDateTime(form.janela_fim),
      km_estimado: toApiDecimal(form.km_estimado),
      km_real: toApiDecimal(form.km_real),
      valor_cobrado: toApiDecimal(form.valor_cobrado),
      custo_estimado: toApiDecimal(form.custo_estimado),
      custo_real: toApiDecimal(form.custo_real),
      endereco_origem: form.endereco_origem || null,
      endereco_destino: form.endereco_destino || null,
    };
  }

  const agendamentosDisponiveis = agendamentos.filter((item) => !item.taxi_dog_id);

  return (
    <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
      <BanhoTosaTaxiDogForm
        agendamentos={agendamentosDisponiveis}
        dataRef={dataRef}
        form={form}
        funcionarios={funcionarios}
        saving={saving}
        onChangeData={setDataRef}
        onChangeField={updateField}
        onSubmit={criarTaxiDog}
      />
      <BanhoTosaTaxiDogList
        items={taxiDog}
        loading={loading}
        saving={saving}
        onAtualizarMedicao={setTaxiDog}
        onSalvarMedicao={salvarMedicao}
        onStatus={atualizarStatus}
      />
    </div>
  );
}

function normalizarDateTime(value) {
  if (!value) return null;
  return value.length === 16 ? `${value}:00` : value;
}

function addMinutes(value, minutes) {
  const date = new Date(value);
  date.setMinutes(date.getMinutes() + minutes);
  return date;
}

function toDateTimeInput(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
