import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import TutorAutocomplete from "../../../components/TutorAutocomplete";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../../components/v2/InputData/InputData";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import Panel from "../../../components/ui/Panel";
import { api } from "../../../services/api";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatCurrency, getApiErrorMessage } from "../banhoTosaUtils";
import { formatarDataLocal } from "../../../utils/drePeriodos";

const initialForm = () => ({
  pacote_id: "",
  pet_id: "",
  data_inicio: formatarDataLocal(),
  data_validade: "",
  observacoes: "",
  gerar_cobranca: true,
});

export default function BanhoTosaCreditoForm({ pacotes = [], onCancel, onChanged }) {
  const [form, setForm] = useState(initialForm);
  const [tutor, setTutor] = useState(null);
  const [pets, setPets] = useState([]);
  const [loadingPets, setLoadingPets] = useState(false);
  const [erroPets, setErroPets] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!tutor?.id) {
      setPets([]);
      setLoadingPets(false);
      return;
    }
    let active = true;
    setLoadingPets(true);
    setErroPets("");
    api
      .get("/vet/pets", { params: { cliente_id: tutor.id, limit: 100 } })
      .then((response) => {
        if (!active) return;
        const lista = response.data?.items ?? response.data ?? [];
        setPets(Array.isArray(lista) ? lista : []);
      })
      .catch((error) => {
        if (!active) return;
        setPets([]);
        setErroPets(
          getApiErrorMessage(
            error,
            "Não foi possível carregar os pets. Selecione o tutor novamente.",
          ),
        );
      })
      .finally(() => active && setLoadingPets(false));
    return () => {
      active = false;
    };
  }, [tutor?.id]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }
  const pacote = pacotes.find((item) => String(item.id) === String(form.pacote_id));

  async function liberarCredito(event) {
    event.preventDefault();
    if (!form.pacote_id || !tutor?.id || !form.pet_id) {
      return toast.error("Selecione pacote, tutor e o pet que usará os serviços.");
    }
    if (!form.data_inicio || (form.data_validade && form.data_validade < form.data_inicio)) {
      return toast.error(
        "Informe as datas do pacote; a validade deve ser igual ou posterior ao início.",
      );
    }
    setSaving(true);
    try {
      const response = await banhoTosaApi.criarCreditoPacote({
        pacote_id: Number(form.pacote_id),
        cliente_id: Number(tutor.id),
        pet_id: Number(form.pet_id),
        data_inicio: form.data_inicio,
        data_validade: form.data_validade || null,
        observacoes: form.observacoes.trim() || null,
      });
      if (form.gerar_cobranca && Number(pacote?.preco || 0) > 0) {
        try {
          await banhoTosaApi.gerarVendaCreditoPacote(response.data.id);
          toast.success(
            "Pacote vinculado ao pet e cobrança aberta no PDV. Registre o recebimento para constar como pago.",
          );
        } catch (error) {
          toast.error(
            getApiErrorMessage(
              error,
              "Pacote vinculado, mas a cobrança não foi gerada. Use Gerar cobrança na lista de saldos.",
            ),
          );
        }
      } else
        toast.success(
          "Pacote vinculado ao pet. O pagamento continua separado do saldo de serviços.",
        );
      await onChanged?.();
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Não foi possível vincular o pacote."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Panel
      title="Vincular pacote ao pet"
      subtitle="O saldo será reservado automaticamente no agendamento e confirmado no check-in, mesmo com pagamento pendente."
    >
      <form onSubmit={liberarCredito} className="space-y-4">
        <InputCombobox
          id="bt-credito-pacote"
          label="Pacote"
          required
          value={form.pacote_id}
          onChange={(value) => updateField("pacote_id", value)}
          opcoes={pacotes
            .filter((item) => item.ativo)
            .map((item) => ({
              value: String(item.id),
              label: `${item.nome} — ${formatCurrency(item.preco)}`,
            }))}
        />
        {pacote && (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {(pacote.servicos || [])
              .map((item) => `${item.quantidade_creditos} × ${item.servico_nome || "serviço"}`)
              .join(" · ") || `${pacote.quantidade_creditos} créditos`}
            {` · validade padrão de ${pacote.validade_dias} dias`}
          </p>
        )}
        <TutorAutocomplete
          label="Tutor"
          inputId="bt-pacote-tutor"
          selectedTutor={tutor}
          onSelect={(value) => {
            setTutor(value);
            setPets([]);
            updateField("pet_id", "");
          }}
        />
        <InputCombobox
          id="bt-credito-pet"
          label="Pet vinculado"
          required
          value={form.pet_id}
          disabled={!tutor?.id || loadingPets}
          error={erroPets}
          placeholder={
            loadingPets
              ? "Carregando pets..."
              : !tutor?.id
                ? "Selecione o tutor primeiro"
                : "Selecione o pet"
          }
          opcoes={pets.map((pet) => ({
            value: String(pet.id),
            label: `${pet.nome}${pet.especie ? ` (${pet.especie})` : ""}`,
          }))}
          onChange={(value) => updateField("pet_id", value)}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <InputData
            id="bt-credito-inicio"
            label="Início"
            required
            value={form.data_inicio}
            onChange={(value) => updateField("data_inicio", value)}
          />
          <InputData
            id="bt-credito-validade"
            label="Validade combinada (opcional)"
            value={form.data_validade}
            help="Em branco, usa a validade do pacote. Depois é possível prorrogar com motivo."
            onChange={(value) => updateField("data_validade", value)}
          />
        </div>
        <InputTexto
          id="bt-credito-observacoes"
          label="Combinados com o cliente"
          value={form.observacoes}
          onChange={(value) => updateField("observacoes", value)}
        />
        {Number(pacote?.preco || 0) > 0 && (
          <InputCheck
            id="bt-credito-cobranca"
            label="Gerar cobrança no PDV"
            checked={form.gerar_cobranca}
            help="Cria uma venda em aberto. O pacote só aparece como pago após registrar o recebimento no PDV."
            onChange={(value) => updateField("gerar_cobranca", value)}
          />
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <BotaoCancelar onClick={onCancel} disabled={saving} />
          <BotaoSalva loading={saving}>Vincular pacote ao pet</BotaoSalva>
        </div>
      </form>
    </Panel>
  );
}
