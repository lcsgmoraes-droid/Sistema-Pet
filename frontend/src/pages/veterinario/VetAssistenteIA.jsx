import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import { buildReturnTo } from "../../utils/petReturnFlow";
import AssistenteIAComposer from "./assistenteIA/AssistenteIAComposer";
import AssistenteIAContextoPanel from "./assistenteIA/AssistenteIAContextoPanel";
import AssistenteIAConversaSelector from "./assistenteIA/AssistenteIAConversaSelector";
import AssistenteIAHeader from "./assistenteIA/AssistenteIAHeader";
import AssistenteIAHistorico from "./assistenteIA/AssistenteIAHistorico";
import { criarIdMensagemLocal } from "./assistenteIA/assistenteIAUtils";

export default function VetAssistenteIA() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const exameIdQuery = searchParams.get("exame_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";
  const [modo, setModo] = useState("atendimento"); // atendimento | livre
  const [conversaId, setConversaId] = useState("");
  const [filtrarConversasContexto, setFiltrarConversasContexto] = useState(false);
  const [memoriaAtiva, setMemoriaAtiva] = useState(null);
  const [conversas, setConversas] = useState([]);
  const [pets, setPets] = useState([]);
  const [consultas, setConsultas] = useState([]);
  const [exames, setExames] = useState([]);
  const [tutorSelecionado, setTutorSelecionado] = useState(null);

  const [petId, setPetId] = useState("");
  const [consultaId, setConsultaId] = useState("");
  const [exameId, setExameId] = useState("");

  const [med1, setMed1] = useState("");
  const [med2, setMed2] = useState("");
  const [pesoKg, setPesoKg] = useState("");
  const [mensagem, setMensagem] = useState("");

  const [historico, setHistorico] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [salvandoFeedbackId, setSalvandoFeedbackId] = useState("");
  const [erro, setErro] = useState("");

  const petSelecionado = useMemo(
    () => pets.find((p) => String(p.id) === String(petId)) || null,
    [pets, petId]
  );

  const petsDoTutor = useMemo(() => {
    if (!tutorSelecionado?.id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(tutorSelecionado.id) && pet.ativo !== false
    );
  }, [pets, tutorSelecionado]);

  useEffect(() => {
    carregarConversas();
    vetApi
      .memoriaStatusAssistenteIA()
      .then((res) => setMemoriaAtiva(Boolean(res.data?.ok)))
      .catch(() => setMemoriaAtiva(false));
    api
      .get("/vet/pets", { params: { limit: 500 } })
      .then((res) => {
        const lista = res.data?.items || res.data || [];
        setPets(Array.isArray(lista) ? lista : []);
      })
      .catch(() => setPets([]));
  }, []);

  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;
    const pet = pets.find((item) => String(item.id) === String(petIdAlvo));
    if (!pet) return;
    setPetId(String(pet.id));
    setTutorSelecionado(
      pet?.cliente_id
        ? {
            id: String(pet.cliente_id),
            nome: pet.cliente_nome ?? `Pessoa #${pet.cliente_id}`,
          }
        : null
    );
  }, [pets, petIdQuery, novoPetIdQuery]);

  useEffect(() => {
    if (!tutorIdQuery || tutorSelecionado?.id) return;
    setTutorSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
    });
  }, [tutorIdQuery, tutorNomeQuery, tutorSelecionado]);

  useEffect(() => {
    if (!filtrarConversasContexto) return;
    carregarConversas();
  }, [filtrarConversasContexto, petId, consultaId, exameId]);

  useEffect(() => {
    if (!conversaId) {
      setHistorico([]);
      return;
    }
    carregarMensagensConversa(conversaId);
  }, [conversaId]);

  useEffect(() => {
    if (!petId) {
      setConsultas([]);
      setExames([]);
      setConsultaId("");
      setExameId("");
      return;
    }

    vetApi
      .listarConsultas({ pet_id: petId, limit: 100 })
      .then((res) => {
        const lista = res.data?.items || res.data || [];
        setConsultas(Array.isArray(lista) ? lista : []);
      })
      .catch(() => setConsultas([]));

    vetApi
      .listarExamesPet(petId)
      .then((res) => {
        const lista = res.data?.items || res.data || [];
        setExames(Array.isArray(lista) ? lista : []);
      })
      .catch(() => setExames([]));
  }, [petId]);

  useEffect(() => {
    if (!consultaIdQuery || consultaId) return;
    const consulta = consultas.find((item) => String(item.id) === String(consultaIdQuery));
    if (consulta) {
      setConsultaId(String(consulta.id));
    }
  }, [consultaIdQuery, consultaId, consultas]);

  useEffect(() => {
    if (!exameIdQuery || exameId) return;
    const exame = exames.find((item) => String(item.id) === String(exameIdQuery));
    if (exame) {
      setExameId(String(exame.id));
    }
  }, [exameIdQuery, exameId, exames]);

  useEffect(() => {
    if (petSelecionado?.peso && !pesoKg) {
      setPesoKg(String(petSelecionado.peso));
    }
  }, [petSelecionado, pesoKg]);

  async function enviar() {
    if (!mensagem.trim() || carregando) return;

    const msg = mensagem.trim();
    const mensagemUsuarioLocalId = criarIdMensagemLocal();
    const mensagemIaLocalId = criarIdMensagemLocal();
    setErro("");
    setHistorico((h) => [...h, { localId: mensagemUsuarioLocalId, role: "user", text: msg }]);
    setMensagem("");
    setCarregando(true);

    try {
      const payload = {
        modo,
        mensagem: msg,
        conversa_id: conversaId ? Number(conversaId) : undefined,
        salvar_historico: true,
        pet_id: petId ? Number(petId) : undefined,
        consulta_id: consultaId ? Number(consultaId) : undefined,
        exame_id: exameId ? Number(exameId) : undefined,
        medicamento_1: med1 || undefined,
        medicamento_2: med2 || undefined,
        peso_kg: pesoKg ? Number(String(pesoKg).replace(",", ".")) : undefined,
      };

      const res = await vetApi.assistenteIA(payload);
      const novaConversaId = res.data?.conversa_id;
      setHistorico((h) => [...h, { localId: mensagemIaLocalId, role: "ia", text: res.data?.resposta || "Sem resposta." }]);

      if (novaConversaId) {
        setConversaId(String(novaConversaId));
        await carregarConversas();
        await carregarMensagensConversa(String(novaConversaId));
      }
    } catch (e) {
      const detail = e?.response?.data?.detail || "Não foi possível falar com a IA agora.";
      setErro(detail);
      setHistorico((h) => [...h, { localId: mensagemIaLocalId, role: "ia", text: `Erro: ${detail}` }]);
    } finally {
      setCarregando(false);
    }
  }

  async function carregarConversas() {
    try {
      const params = { limit: 30 };
      if (filtrarConversasContexto) {
        if (petId) params.pet_id = Number(petId);
        if (consultaId) params.consulta_id = Number(consultaId);
        if (exameId) params.exame_id = Number(exameId);
      }
      const res = await vetApi.listarConversasAssistenteIA(params);
      const lista = res.data?.items || [];
      setConversas(Array.isArray(lista) ? lista : []);
    } catch {
      setConversas([]);
    }
  }

  async function carregarMensagensConversa(id) {
    if (!id) return;
    setCarregandoHistorico(true);
    try {
      const res = await vetApi.listarMensagensConversaAssistenteIA(Number(id));
      const itens = res.data?.items || [];
      setHistorico(
        itens.map((item) => ({
          id: item.id,
          role: item.tipo === "usuario" ? "user" : "ia",
          text: item.conteudo || "",
          feedback: item.feedback || null,
        }))
      );
    } catch {
      setHistorico([]);
    } finally {
      setCarregandoHistorico(false);
    }
  }

  function novaConversa() {
    setConversaId("");
    setHistorico([]);
    setErro("");
  }

  async function enviarFeedback(mensagemId, util) {
    if (!mensagemId || salvandoFeedbackId) return;
    setSalvandoFeedbackId(String(mensagemId));
    try {
      const comentarioBruto = globalThis.prompt("Comentário opcional para melhorar a IA:", "") || "";
      const comentario = comentarioBruto.trim();
      const payload = {
        util,
        nota: util ? 5 : 2,
        comentario: comentario || undefined,
      };
      await vetApi.feedbackMensagemAssistenteIA(mensagemId, payload);
      setHistorico((atual) =>
        atual.map((msg) =>
          msg.id === mensagemId
            ? { ...msg, feedback: { util, nota: util ? 5 : 2, comentario: comentario || null } }
            : msg
        )
      );
    } catch {
      // mantém a conversa sem interromper o fluxo principal
    } finally {
      setSalvandoFeedbackId("");
    }
  }

  function perguntaRapida(texto) {
    setMensagem(texto);
  }

  function selecionarTutor(cliente) {
    setTutorSelecionado(cliente);
    setPetId("");
    setConsultaId("");
    setExameId("");
  }

  function selecionarPet(proximoPetId) {
    setPetId(proximoPetId);
    setConsultaId("");
    setExameId("");
  }

  function abrirConsulta(consultaIdAlvo) {
    navigate(`/veterinario/consultas/${consultaIdAlvo}`);
  }

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search),
    [location.pathname, location.search]
  );
  const consultaSelecionada = useMemo(
    () => consultas.find((item) => String(item.id) === String(consultaId)) ?? null,
    [consultas, consultaId]
  );
  const exameSelecionado = useMemo(
    () => exames.find((item) => String(item.id) === String(exameId)) ?? null,
    [exames, exameId]
  );

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <AssistenteIAHeader memoriaAtiva={memoriaAtiva} />

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <AssistenteIAConversaSelector
          conversaId={conversaId}
          conversas={conversas}
          filtrarConversasContexto={filtrarConversasContexto}
          onAtualizarConversas={carregarConversas}
          onNovaConversa={novaConversa}
          setConversaId={setConversaId}
          setFiltrarConversasContexto={setFiltrarConversasContexto}
        />

        <AssistenteIAContextoPanel
          consultaId={consultaId}
          consultaSelecionada={consultaSelecionada}
          consultas={consultas}
          exameId={exameId}
          exameSelecionado={exameSelecionado}
          exames={exames}
          med1={med1}
          med2={med2}
          modo={modo}
          onAbrirConsulta={abrirConsulta}
          onSelecionarPet={selecionarPet}
          onSelecionarTutor={selecionarTutor}
          pesoKg={pesoKg}
          petId={petId}
          petsDoTutor={petsDoTutor}
          retornoNovoPet={retornoNovoPet}
          setConsultaId={setConsultaId}
          setExameId={setExameId}
          setMed1={setMed1}
          setMed2={setMed2}
          setModo={setModo}
          setPesoKg={setPesoKg}
          tutorSelecionado={tutorSelecionado}
        />

        <AssistenteIAComposer
          carregando={carregando}
          erro={erro}
          mensagem={mensagem}
          onEnviar={enviar}
          onPerguntaRapida={perguntaRapida}
          setMensagem={setMensagem}
        />
      </div>

      <AssistenteIAHistorico
        carregandoHistorico={carregandoHistorico}
        historico={historico}
        onEnviarFeedback={enviarFeedback}
        salvandoFeedbackId={salvandoFeedbackId}
      />
    </div>
  );
}
