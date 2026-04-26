import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { buildReturnTo } from "../../utils/petReturnFlow";
import CalendarioPreventivoTab from "./vacinas/CalendarioPreventivoTab";
import CarteiraVacinasTab from "./vacinas/CarteiraVacinasTab";
import RegistrarVacinaModal from "./vacinas/RegistrarVacinaModal";
import VacinasHeader from "./vacinas/VacinasHeader";
import VacinasTabs from "./vacinas/VacinasTabs";
import VacinasVencendoTab from "./vacinas/VacinasVencendoTab";
import {
  criarFormVacinaInicial,
  normalizarVacinas,
  sugerirProximaDose,
} from "./vacinas/vacinaUtils";

export default function VetVacinas() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [aba, setAba] = useState("registros");
  const [pessoaFiltro, setPessoaFiltro] = useState("");
  const [tutorFiltroSelecionado, setTutorFiltroSelecionado] = useState(null);
  const [petSelecionado, setPetSelecionado] = useState("");
  const [pets, setPets] = useState([]);
  const [veterinarios, setVeterinarios] = useState([]);
  const [vacinas, setVacinas] = useState([]);
  const [vacinasVencendo, setVacinasVencendo] = useState([]);
  const [protocolos, setProtocolos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [novaAberta, setNovaAberta] = useState(false);
  const [calendario, setCalendario] = useState([]);
  const [especieCalendario, setEspecieCalendario] = useState("");
  const [carregandoCalendario, setCarregandoCalendario] = useState(false);
  const [tutorFormSelecionado, setTutorFormSelecionado] = useState(null);
  const [form, setForm] = useState(() => criarFormVacinaInicial());
  const [salvando, setSalvando] = useState(false);

  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const acaoQuery = searchParams.get("acao") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

  const carregarVencendo = useCallback(async () => {
    try {
      const res = await vetApi.vacinasVencendo(30);
      setVacinasVencendo(normalizarVacinas(res.data));
    } catch {}
  }, []);

  useEffect(() => {
    api.get("/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => {});

    vetApi.listarVeterinarios()
      .then((res) => setVeterinarios(Array.isArray(res.data) ? res.data : []))
      .catch(() => setVeterinarios([]));

    vetApi.listarProtocolosVacinas()
      .then((res) => setProtocolos(Array.isArray(res.data) ? res.data : []))
      .catch(() => setProtocolos([]));

    carregarVencendo();
  }, [carregarVencendo]);

  const carregarVacinasPet = useCallback(async () => {
    if (!petSelecionado) {
      setVacinas([]);
      return;
    }

    try {
      setCarregando(true);
      const res = await vetApi.listarVacinasPet(petSelecionado);
      setVacinas(normalizarVacinas(res.data));
    } catch {
      setErro("Erro ao carregar vacinas.");
    } finally {
      setCarregando(false);
    }
  }, [petSelecionado]);

  useEffect(() => {
    carregarVacinasPet();
  }, [carregarVacinasPet]);

  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    const pessoaId = petEncontrado?.cliente_id ? String(petEncontrado.cliente_id) : "";
    if (pessoaId) {
      const tutorSelecionado = {
        id: pessoaId,
        nome: petEncontrado.cliente_nome ?? `Pessoa #${pessoaId}`,
      };

      setPessoaFiltro(pessoaId);
      setTutorFiltroSelecionado(tutorSelecionado);
      setTutorFormSelecionado(tutorSelecionado);
      setForm((prev) => ({ ...prev, pessoa_id: pessoaId }));
    }

    setPetSelecionado(String(petEncontrado.id));
    setForm((prev) => ({ ...prev, pet_id: String(petEncontrado.id) }));

    if (acaoQuery === "novo" || novoPetIdQuery) {
      setNovaAberta(true);
    }
  }, [petIdQuery, novoPetIdQuery, acaoQuery, pets]);

  useEffect(() => {
    if (!tutorIdQuery || tutorFormSelecionado?.id) return;

    setTutorFormSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
    });
    setForm((prev) => ({ ...prev, pessoa_id: String(tutorIdQuery) }));
  }, [tutorIdQuery, tutorNomeQuery, tutorFormSelecionado]);

  const petsDaPessoa = useMemo(() => {
    if (!form.pessoa_id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(form.pessoa_id) && pet.ativo !== false
    );
  }, [pets, form.pessoa_id]);

  const pessoaIdPorPet = useCallback(
    (petId) => {
      if (!petId) return "";
      const pet = pets.find((item) => String(item.id) === String(petId));
      return pet?.cliente_id ? String(pet.cliente_id) : "";
    },
    [pets]
  );

  const petsFiltradosCarteira = useMemo(() => {
    if (!pessoaFiltro) return pets;
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(pessoaFiltro) && pet.ativo !== false
    );
  }, [pets, pessoaFiltro]);

  const sugestaoDose = useMemo(
    () => sugerirProximaDose(protocolos, pets, form),
    [protocolos, pets, form]
  );

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { acao: "novo" }),
    [location.pathname, location.search]
  );

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function selecionarTutorFiltro(cliente) {
    setTutorFiltroSelecionado(cliente);
    setPessoaFiltro(cliente?.id ? String(cliente.id) : "");
    setPetSelecionado("");
  }

  function selecionarTutorForm(cliente) {
    setTutorFormSelecionado(cliente);
    setCampo("pessoa_id", cliente?.id ? String(cliente.id) : "");
    setCampo("pet_id", "");
  }

  function fecharModalVacina() {
    setNovaAberta(false);
    setTutorFormSelecionado(null);
    setForm(criarFormVacinaInicial());

    if (acaoQuery === "novo" || petIdQuery || novoPetIdQuery || agendamentoIdQuery || consultaIdQuery) {
      navigate("/veterinario/vacinas", { replace: true });
    }
  }

  function abrirRegistroPrimeiraVacina() {
    const pessoaIdAtual = pessoaIdPorPet(petSelecionado);
    const petAtual = pets.find((pet) => String(pet.id) === String(petSelecionado));

    setTutorFormSelecionado(
      pessoaIdAtual
        ? { id: pessoaIdAtual, nome: petAtual?.cliente_nome ?? `Pessoa #${pessoaIdAtual}` }
        : null
    );

    setForm((prev) => ({
      ...prev,
      pessoa_id: pessoaIdAtual,
      pet_id: petSelecionado,
    }));
    setNovaAberta(true);
  }

  async function carregarCalendarioPreventivo() {
    setCarregandoCalendario(true);

    try {
      const res = await vetApi.calendarioPreventivo(especieCalendario || undefined);
      setCalendario(res.data?.items ?? []);
    } catch {
      setCalendario([]);
    } finally {
      setCarregandoCalendario(false);
    }
  }

  async function salvarVacina() {
    if (!form.pet_id || !form.nome_vacina || !form.data_aplicacao) return;

    setSalvando(true);
    setErro(null);

    try {
      await vetApi.registrarVacina({
        pet_id: form.pet_id,
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        nome_vacina: form.nome_vacina,
        fabricante: form.fabricante || undefined,
        lote: form.lote || undefined,
        data_aplicacao: form.data_aplicacao,
        data_proxima_dose: form.proxima_dose || sugestaoDose?.proximaDose || undefined,
        veterinario_responsavel: form.veterinario_responsavel || undefined,
        observacoes: form.observacoes || undefined,
      });

      fecharModalVacina();
      if (form.pet_id === petSelecionado) await carregarVacinasPet();
      await carregarVencendo();
    } catch (e) {
      setErro(e?.response?.data?.detail ?? "Erro ao registrar vacina.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      <VacinasHeader onRegistrarVacina={() => setNovaAberta(true)} />

      <VacinasTabs
        aba={aba}
        vacinasVencendoTotal={vacinasVencendo.length}
        onChangeAba={setAba}
      />

      {erro && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">
          <AlertCircle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {aba === "registros" && (
        <CarteiraVacinasTab
          tutorFiltroSelecionado={tutorFiltroSelecionado}
          pessoaFiltro={pessoaFiltro}
          petSelecionado={petSelecionado}
          petsFiltradosCarteira={petsFiltradosCarteira}
          vacinas={vacinas}
          carregando={carregando}
          onSelecionarTutor={selecionarTutorFiltro}
          onSelecionarPet={setPetSelecionado}
          onRegistrarPrimeiraVacina={abrirRegistroPrimeiraVacina}
        />
      )}

      {aba === "vencendo" && (
        <VacinasVencendoTab vacinasVencendo={vacinasVencendo} />
      )}

      {aba === "calendario" && (
        <CalendarioPreventivoTab
          calendario={calendario}
          especieCalendario={especieCalendario}
          carregandoCalendario={carregandoCalendario}
          onChangeEspecie={setEspecieCalendario}
          onCarregarCalendario={carregarCalendarioPreventivo}
        />
      )}

      <RegistrarVacinaModal
        isOpen={novaAberta}
        consultaId={consultaIdQuery}
        tutorFormSelecionado={tutorFormSelecionado}
        form={form}
        petsDaPessoa={petsDaPessoa}
        sugestaoDose={sugestaoDose}
        veterinarios={veterinarios}
        erro={erro}
        salvando={salvando}
        retornoNovoPet={retornoNovoPet}
        onSelecionarTutor={selecionarTutorForm}
        onSetCampo={setCampo}
        onFechar={fecharModalVacina}
        onSalvar={salvarVacina}
        onBeforeNovoPet={() => setNovaAberta(false)}
      />
    </div>
  );
}
