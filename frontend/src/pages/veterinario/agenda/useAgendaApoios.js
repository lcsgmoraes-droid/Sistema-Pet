import { useEffect } from "react";

import { api } from "../../../services/api";
import { vetApi } from "../vetApi";

export function useAgendaApoios({
  abrirNovoQuery,
  formNovoData,
  novoAberto,
  novoPetIdQuery,
  petsDoTutor,
  setAgendaDiaModal,
  setCalendarioMeta,
  setCarregandoAgendaDiaModal,
  setCarregandoCalendario,
  setCarregandoPetsTutor,
  setConsultorios,
  setFormNovo,
  setNovoAberto,
  setPetsDoTutor,
  setTutorSelecionado,
  setVeterinarios,
  tutorIdQuery,
  tutorNomeQuery,
  tutorSelecionado,
}) {
  useEffect(() => {
    if (!abrirNovoQuery) return;
    setNovoAberto(true);
  }, [abrirNovoQuery, setNovoAberto]);

  useEffect(() => {
    let ativo = true;

    async function carregarApoiosAgenda() {
      try {
        const [veterinariosRes, consultoriosRes] = await Promise.all([
          vetApi.listarVeterinarios(),
          vetApi.listarConsultorios({ ativos_only: true }),
        ]);
        if (!ativo) return;
        setVeterinarios(Array.isArray(veterinariosRes.data) ? veterinariosRes.data : []);
        setConsultorios(Array.isArray(consultoriosRes.data) ? consultoriosRes.data : []);
      } catch {
        if (!ativo) return;
        setVeterinarios([]);
        setConsultorios([]);
      }
    }

    carregarApoiosAgenda();

    return () => {
      ativo = false;
    };
  }, [setConsultorios, setVeterinarios]);

  useEffect(() => {
    let ativo = true;

    async function carregarCalendarioAgenda() {
      try {
        setCarregandoCalendario(true);
        const res = await vetApi.obterCalendarioAgendaMeta();
        if (!ativo) return;
        setCalendarioMeta(res.data || null);
      } catch {
        if (!ativo) return;
        setCalendarioMeta(null);
      } finally {
        if (ativo) {
          setCarregandoCalendario(false);
        }
      }
    }

    carregarCalendarioAgenda();

    return () => {
      ativo = false;
    };
  }, [setCalendarioMeta, setCarregandoCalendario]);

  useEffect(() => {
    if (!novoAberto || !tutorIdQuery) return;
    setTutorSelecionado((prev) => {
      if (prev?.id && String(prev.id) === String(tutorIdQuery)) {
        return prev;
      }
      return {
        id: String(tutorIdQuery),
        nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
      };
    });
  }, [novoAberto, setTutorSelecionado, tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    if (!novoAberto || !tutorSelecionado?.id) {
      setPetsDoTutor([]);
      setCarregandoPetsTutor(false);
      return;
    }

    let ativo = true;

    async function carregarPetsTutor() {
      try {
        setCarregandoPetsTutor(true);
        const resposta = await api.get("/vet/pets", {
          params: {
            cliente_id: tutorSelecionado.id,
            limit: 100,
          },
        });
        if (!ativo) return;
        const lista = resposta.data?.items ?? resposta.data ?? [];
        setPetsDoTutor(Array.isArray(lista) ? lista : []);
      } catch {
        if (!ativo) return;
        setPetsDoTutor([]);
      } finally {
        if (ativo) {
          setCarregandoPetsTutor(false);
        }
      }
    }

    carregarPetsTutor();

    return () => {
      ativo = false;
    };
  }, [novoAberto, setCarregandoPetsTutor, setPetsDoTutor, tutorSelecionado?.id]);

  useEffect(() => {
    if (!novoAberto || !novoPetIdQuery || !petsDoTutor.length) return;
    const petNovo = petsDoTutor.find((pet) => String(pet.id) === String(novoPetIdQuery));
    if (!petNovo) return;
    setFormNovo((prev) => ({ ...prev, pet_id: String(petNovo.id) }));
  }, [novoAberto, novoPetIdQuery, petsDoTutor, setFormNovo]);

  useEffect(() => {
    if (!novoAberto || !formNovoData) {
      setAgendaDiaModal([]);
      setCarregandoAgendaDiaModal(false);
      return;
    }

    let ativo = true;

    async function carregarAgendaDiaModal() {
      try {
        setCarregandoAgendaDiaModal(true);
        const resposta = await vetApi.listarAgendamentos({
          data_inicio: formNovoData,
          data_fim: formNovoData,
        });
        if (!ativo) return;
        const lista = resposta.data?.items ?? resposta.data ?? [];
        const ordenados = (Array.isArray(lista) ? lista : []).sort((a, b) =>
          String(a.data_hora || "").localeCompare(String(b.data_hora || ""))
        );
        setAgendaDiaModal(ordenados);
      } catch {
        if (!ativo) return;
        setAgendaDiaModal([]);
      } finally {
        if (ativo) {
          setCarregandoAgendaDiaModal(false);
        }
      }
    }

    carregarAgendaDiaModal();

    return () => {
      ativo = false;
    };
  }, [formNovoData, novoAberto, setAgendaDiaModal, setCarregandoAgendaDiaModal]);
}
