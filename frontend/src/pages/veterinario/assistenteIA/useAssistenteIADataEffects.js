import { useEffect } from "react";
import { api } from "../../../services/api";
import { vetApi } from "../vetApi";

export default function useAssistenteIADataEffects({
  carregarConversas,
  carregarMensagensConversa,
  consultaId,
  consultaIdQuery,
  consultas,
  conversaId,
  exameId,
  exameIdQuery,
  exames,
  filtrarConversasContexto,
  novoPetIdQuery,
  petId,
  petIdQuery,
  pets,
  petSelecionado,
  pesoKg,
  setConsultaId,
  setConsultas,
  setExameId,
  setExames,
  setHistorico,
  setMemoriaAtiva,
  setPets,
  setPesoKg,
  setPetId,
  setTutorSelecionado,
  tutorIdQuery,
  tutorNomeQuery,
  tutorSelecionado,
}) {
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
    if (consulta) setConsultaId(String(consulta.id));
  }, [consultaIdQuery, consultaId, consultas]);

  useEffect(() => {
    if (!exameIdQuery || exameId) return;
    const exame = exames.find((item) => String(item.id) === String(exameIdQuery));
    if (exame) setExameId(String(exame.id));
  }, [exameIdQuery, exameId, exames]);

  useEffect(() => {
    if (petSelecionado?.peso && !pesoKg) {
      setPesoKg(String(petSelecionado.peso));
    }
  }, [petSelecionado, pesoKg]);
}
