import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../../../services/api";
import { buildReturnTo } from "../../../utils/petReturnFlow";
import { vetApi } from "../vetApi";
import {
  FORM_EXAME_ANEXADO_INICIAL,
  hojeIso,
} from "./examesAnexadosUtils";

export function useVetExamesAnexados() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [periodo, setPeriodo] = useState("hoje");
  const [dataInicio, setDataInicio] = useState(hojeIso());
  const [dataFim, setDataFim] = useState(hojeIso());
  const [tutorBusca, setTutorBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState({ items: [], total: 0 });
  const [exameExpandidoId, setExameExpandidoId] = useState("");
  const [pets, setPets] = useState([]);
  const [novaAberta, setNovaAberta] = useState(false);
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [erroNovo, setErroNovo] = useState("");
  const [tutorFormSelecionado, setTutorFormSelecionado] = useState(null);
  const [form, setForm] = useState(FORM_EXAME_ANEXADO_INICIAL);
  const [arquivoNovo, setArquivoNovo] = useState(null);

  const itens = useMemo(() => (Array.isArray(dados.items) ? dados.items : []), [dados]);

  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const acaoQuery = searchParams.get("acao") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

  const petsDoTutor = useMemo(() => {
    if (!tutorFormSelecionado?.id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(tutorFormSelecionado.id) && pet.ativo !== false
    );
  }, [pets, tutorFormSelecionado]);

  async function carregar() {
    try {
      setCarregando(true);
      setErro("");

      const params = {
        periodo,
        tutor: tutorBusca.trim() || undefined,
      };

      if (periodo === "periodo") {
        params.data_inicio = dataInicio;
        params.data_fim = dataFim;
      }

      const res = await vetApi.listarExamesAnexados(params);
      setDados(res.data || { items: [], total: 0 });
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao carregar exames anexados.");
      setDados({ items: [], total: 0 });
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    api
      .get("/vet/pets", { params: { limit: 500 } })
      .then((res) => setPets(res.data?.items ?? res.data ?? []))
      .catch(() => setPets([]));
  }, []);

  useEffect(() => {
    const petIdAlvo = novoPetIdQuery || petIdQuery;
    if (!petIdAlvo || !pets.length) return;

    const petEncontrado = pets.find((pet) => String(pet.id) === String(petIdAlvo));
    if (!petEncontrado) return;

    const tutor = petEncontrado?.cliente_id
      ? {
          id: String(petEncontrado.cliente_id),
          nome: petEncontrado.cliente_nome ?? `Tutor #${petEncontrado.cliente_id}`,
          telefone: petEncontrado.cliente_telefone ?? "",
          celular: petEncontrado.cliente_celular ?? "",
        }
      : null;

    setTutorFormSelecionado(tutor);
    setForm((prev) => ({
      ...prev,
      pet_id: String(petEncontrado.id),
    }));

    if (acaoQuery === "novo" || novoPetIdQuery) {
      setNovaAberta(true);
    }
  }, [petIdQuery, novoPetIdQuery, acaoQuery, pets]);

  useEffect(() => {
    if (!tutorIdQuery || tutorFormSelecionado?.id) return;
    setTutorFormSelecionado({
      id: String(tutorIdQuery),
      nome: tutorNomeQuery || `Tutor #${tutorIdQuery}`,
    });
  }, [tutorIdQuery, tutorNomeQuery, tutorFormSelecionado]);

  const retornoNovoPet = useMemo(
    () => buildReturnTo(location.pathname, location.search, { acao: "novo" }),
    [location.pathname, location.search]
  );

  function abrirNovoExame() {
    setErroNovo("");
    setArquivoNovo(null);
    setNovaAberta(true);
  }

  function fecharNovoExame() {
    setNovaAberta(false);
    setErroNovo("");
    setTutorFormSelecionado(null);
    setForm(FORM_EXAME_ANEXADO_INICIAL);
    setArquivoNovo(null);

    if (acaoQuery === "novo" || petIdQuery || novoPetIdQuery || agendamentoIdQuery || consultaIdQuery) {
      navigate("/veterinario/exames", { replace: true });
    }
  }

  async function salvarExame() {
    if (!form.pet_id || !form.nome) return;
    setSalvandoNovo(true);
    setErroNovo("");

    try {
      const res = await vetApi.criarExame({
        pet_id: Number(form.pet_id),
        consulta_id: consultaIdQuery ? Number(consultaIdQuery) : undefined,
        agendamento_id: agendamentoIdQuery ? Number(agendamentoIdQuery) : undefined,
        tipo: form.tipo,
        nome: form.nome,
        data_solicitacao: form.data_solicitacao || undefined,
        laboratorio: form.laboratorio || undefined,
        observacoes: form.observacoes || undefined,
      });

      if (arquivoNovo) {
        await vetApi.uploadArquivoExame(res.data.id, arquivoNovo);
        try {
          await vetApi.processarArquivoExameIA(res.data.id);
        } catch {}
      }

      fecharNovoExame();
      await carregar();
    } catch (e) {
      setErroNovo(e?.response?.data?.detail || "Erro ao registrar exame.");
    } finally {
      setSalvandoNovo(false);
    }
  }

  function atualizarResumoExame(exameAtualizado) {
    if (!exameAtualizado?.id) return;
    setDados((atual) => ({
      ...atual,
      items: (Array.isArray(atual.items) ? atual.items : []).map((item) =>
        String(item.exame_id) === String(exameAtualizado.id)
          ? {
              ...item,
              status: exameAtualizado.status || item.status,
              arquivo_nome: exameAtualizado.arquivo_nome || item.arquivo_nome,
              arquivo_url: exameAtualizado.arquivo_url || item.arquivo_url,
              tem_interpretacao_ia: Boolean(
                exameAtualizado.interpretacao_ia ||
                  exameAtualizado.interpretacao_ia_resumo ||
                  exameAtualizado.interpretacao_ia_payload
              ),
            }
          : item
      ),
    }));
  }

  function limparFiltros() {
    setPeriodo("hoje");
    setDataInicio(hojeIso());
    setDataFim(hojeIso());
    setTutorBusca("");
  }

  function toggleExameExpandido(exameId) {
    setExameExpandidoId((atual) => (
      String(atual) === String(exameId) ? "" : String(exameId)
    ));
  }

  function abrirConsultaExame(item) {
    if (item.consulta_id) {
      navigate(`/veterinario/consultas/${item.consulta_id}`);
      return;
    }

    navigate(`/veterinario/consultas/nova?pet_id=${item.pet_id}`);
  }

  return {
    abrirConsultaExame,
    abrirNovoExame,
    atualizarResumoExame,
    carregar,
    carregando,
    consultaIdQuery,
    dados,
    dataFim,
    dataInicio,
    erro,
    erroNovo,
    exameExpandidoId,
    fecharNovoExame,
    form,
    itens,
    limparFiltros,
    novaAberta,
    periodo,
    petsDoTutor,
    retornoNovoPet,
    salvarExame,
    salvandoNovo,
    setArquivoNovo,
    setDataFim,
    setDataInicio,
    setForm,
    setPeriodo,
    setTutorBusca,
    setTutorFormSelecionado,
    toggleExameExpandido,
    tutorBusca,
    tutorFormSelecionado,
    verPet: (petId) => navigate(`/pets/${petId}`),
    verPets: () => navigate("/pets"),
  };
}
