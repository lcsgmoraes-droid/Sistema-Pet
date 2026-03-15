import { useEffect, useMemo, useState } from "react";
import {
  Bot,
  Send,
  Stethoscope,
  FlaskConical,
  Calculator,
  Pill,
  MessageSquarePlus,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import { vetApi } from "./vetApi";
import { api } from "../../services/api";
import TutorAutocomplete from "../../components/TutorAutocomplete";

const css = {
  input:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-300",
  select:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-cyan-300",
  textarea:
    "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm min-h-[90px] focus:outline-none focus:ring-2 focus:ring-cyan-300",
};

function criarIdMensagemLocal() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.round(Math.random() * 100000)}`;
}

export default function VetAssistenteIA() {
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

  let memoriaBadge = <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-500">Memória: verificando...</span>;
  if (memoriaAtiva === true) {
    memoriaBadge = <span className="text-xs px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">Memória ativa</span>;
  }
  if (memoriaAtiva === false) {
    memoriaBadge = <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700">Memória indisponível</span>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-cyan-100 rounded-xl">
          <Bot size={20} className="text-cyan-700" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-800">Assistente IA Veterinário</h1>
          <p className="text-xs text-gray-500">Aba dedicada para cálculo de dose, interação medicamentosa e discussão clínica.</p>
        </div>
        <div className="ml-auto">{memoriaBadge}</div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <div className="md:col-span-2">
            <label htmlFor="vet-ia-conversa" className="block text-xs font-medium text-gray-600 mb-1">Conversa salva</label>
            <select id="vet-ia-conversa" value={conversaId} onChange={(e) => setConversaId(e.target.value)} className={css.select}>
              <option value="">Nova conversa</option>
              {conversas.map((c) => (
                <option key={c.id} value={c.id}>{c.titulo || `Conversa #${c.id}`}</option>
              ))}
            </select>
            <label className="mt-2 inline-flex items-center gap-2 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={filtrarConversasContexto}
                onChange={(e) => setFiltrarConversasContexto(e.target.checked)}
              />
              <span>Filtrar conversas pelo contexto atual (pet/consulta/exame)</span>
            </label>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={novaConversa}
              className="inline-flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-gray-200 hover:bg-gray-50"
            >
              <MessageSquarePlus size={14} /> Nova
            </button>
            <button
              type="button"
              onClick={carregarConversas}
              className="inline-flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-gray-200 hover:bg-gray-50"
            >
              <RefreshCw size={14} /> Atualizar
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setModo("atendimento")}
            className={`px-3 py-1.5 text-sm rounded-lg border ${
              modo === "atendimento"
                ? "bg-cyan-600 text-white border-cyan-600"
                : "bg-white text-gray-600 border-gray-200"
            }`}
          >
            <span className="inline-flex items-center gap-2"><Stethoscope size={14} /> Vincular atendimento</span>
          </button>
          <button
            type="button"
            onClick={() => setModo("livre")}
            className={`px-3 py-1.5 text-sm rounded-lg border ${
              modo === "livre"
                ? "bg-cyan-600 text-white border-cyan-600"
                : "bg-white text-gray-600 border-gray-200"
            }`}
          >
            <span className="inline-flex items-center gap-2"><FlaskConical size={14} /> Conversa livre</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
            <TutorAutocomplete
              label="Tutor"
              inputId="vet-ia-tutor"
              selectedTutor={tutorSelecionado}
              onSelect={(cliente) => {
                setTutorSelecionado(cliente);
                setPetId("");
                setConsultaId("");
                setExameId("");
              }}
            />
          </div>

          <div>
            <label htmlFor="vet-ia-pet" className="block text-xs font-medium text-gray-600 mb-1">Pet (opcional)</label>
            <select
              id="vet-ia-pet"
              value={petId}
              onChange={(e) => setPetId(e.target.value)}
              className={css.select}
              disabled={!tutorSelecionado?.id}
            >
              <option value="">{tutorSelecionado?.id ? "Selecione o pet..." : "Selecione o tutor primeiro..."}</option>
              {petsDoTutor.map((p) => (
                <option key={p.id} value={p.id}>{p.nome}{p.especie ? ` (${p.especie})` : ""}</option>
              ))}
            </select>
          </div>

          {modo === "atendimento" && (
            <>
              <div>
                <label htmlFor="vet-ia-consulta" className="block text-xs font-medium text-gray-600 mb-1">Consulta (opcional)</label>
                <select id="vet-ia-consulta" value={consultaId} onChange={(e) => setConsultaId(e.target.value)} className={css.select}>
                  <option value="">Sem consulta</option>
                  {consultas.map((c) => (
                    <option key={c.id} value={c.id}>Consulta #{c.id} {c.data_consulta ? `- ${c.data_consulta}` : ""}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="vet-ia-exame" className="block text-xs font-medium text-gray-600 mb-1">Exame (opcional)</label>
                <select id="vet-ia-exame" value={exameId} onChange={(e) => setExameId(e.target.value)} className={css.select}>
                  <option value="">Sem exame</option>
                  {exames.map((ex) => (
                    <option key={ex.id} value={ex.id}>{ex.nome || ex.tipo || `Exame #${ex.id}`}</option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label htmlFor="vet-ia-peso" className="block text-xs font-medium text-gray-600 mb-1">Peso (kg) para cálculo de dose</label>
            <div className="relative">
              <Calculator size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input id="vet-ia-peso" value={pesoKg} onChange={(e) => setPesoKg(e.target.value)} className={`${css.input} pl-9`} placeholder="Ex: 12,5" />
            </div>
          </div>
          <div>
            <label htmlFor="vet-ia-med1" className="block text-xs font-medium text-gray-600 mb-1">Medicamento 1 (opcional)</label>
            <div className="relative">
              <Pill size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input id="vet-ia-med1" value={med1} onChange={(e) => setMed1(e.target.value)} className={`${css.input} pl-9`} placeholder="Ex: amoxicilina" />
            </div>
          </div>
          <div>
            <label htmlFor="vet-ia-med2" className="block text-xs font-medium text-gray-600 mb-1">Medicamento 2 (opcional)</label>
            <div className="relative">
              <Pill size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input id="vet-ia-med2" value={med2} onChange={(e) => setMed2(e.target.value)} className={`${css.input} pl-9`} placeholder="Ex: prednisolona" />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => perguntaRapida("pode associar amoxicilina com prednisolona?")} className="text-xs px-2.5 py-1.5 rounded-md border border-cyan-200 text-cyan-700 hover:bg-cyan-50">Interação de medicamentos</button>
          <button type="button" onClick={() => perguntaRapida("calcule a dose de amoxicilina por mg/kg") } className="text-xs px-2.5 py-1.5 rounded-md border border-cyan-200 text-cyan-700 hover:bg-cyan-50">Calcular dose</button>
          <button type="button" onClick={() => perguntaRapida("pelos sintomas de vômito, apatia e febre, quais as principais possibilidades?") } className="text-xs px-2.5 py-1.5 rounded-md border border-cyan-200 text-cyan-700 hover:bg-cyan-50">Hipóteses por sintomas</button>
          <button type="button" onClick={() => perguntaRapida("o que mais devo olhar para fechar diagnóstico?") } className="text-xs px-2.5 py-1.5 rounded-md border border-cyan-200 text-cyan-700 hover:bg-cyan-50">Checklist diagnóstico</button>
        </div>

        <textarea
          value={mensagem}
          onChange={(e) => setMensagem(e.target.value)}
          className={css.textarea}
          placeholder="Descreva o caso: sintomas, exames, medicações e sua pergunta..."
        />

        <div className="flex justify-end">
          <button
            type="button"
            onClick={enviar}
            disabled={!mensagem.trim() || carregando}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-60"
          >
            <Send size={14} /> {carregando ? "Enviando..." : "Perguntar à IA"}
          </button>
        </div>

        {erro && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{erro}</div>}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Conversa</h2>
        {carregandoHistorico && (
          <p className="text-xs text-gray-400">Carregando histórico...</p>
        )}
        {historico.length === 0 ? (
          <p className="text-sm text-gray-400">Ainda sem mensagens. Envie a primeira pergunta.</p>
        ) : (
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {historico.map((msg) => (
              <div key={msg.id || msg.localId || criarIdMensagemLocal()} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[88%] px-3 py-2 rounded-xl text-sm whitespace-pre-wrap ${msg.role === "user" ? "bg-cyan-600 text-white rounded-br-none" : "bg-gray-100 text-gray-800 rounded-bl-none"}`}>
                  {msg.role === "ia" && <div className="text-[11px] font-semibold text-cyan-700 mb-1">IA Vet</div>}
                  {msg.text}
                  {msg.role === "ia" && msg.id ? (
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => enviarFeedback(msg.id, true)}
                        disabled={salvandoFeedbackId === String(msg.id)}
                        className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md border ${msg.feedback?.util === true ? "border-green-400 text-green-700 bg-green-50" : "border-gray-200 text-gray-600"}`}
                      >
                        <ThumbsUp size={11} /> Útil
                      </button>
                      <button
                        type="button"
                        onClick={() => enviarFeedback(msg.id, false)}
                        disabled={salvandoFeedbackId === String(msg.id)}
                        className={`inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md border ${msg.feedback?.util === false ? "border-amber-400 text-amber-700 bg-amber-50" : "border-gray-200 text-gray-600"}`}
                      >
                        <ThumbsDown size={11} /> Não útil
                      </button>
                    </div>
                  ) : null}
                  {msg.role === "ia" && msg.feedback?.comentario ? (
                    <div className="mt-2 text-[11px] text-gray-500 border-t border-gray-200 pt-2">
                      Comentário: {msg.feedback.comentario}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
