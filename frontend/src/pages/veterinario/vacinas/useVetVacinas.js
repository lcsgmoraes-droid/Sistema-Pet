import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { buildReturnTo } from "../../../utils/petReturnFlow";
import { vetApi } from "../vetApi";
import {
  criarFormVacinaInicial,
  normalizarVacinas,
  sugerirProximaDose,
} from "./vacinaUtils";
import { useVacinasBaseData } from "./useVacinasBaseData";
import { useVacinasCalendario } from "./useVacinasCalendario";
import { useVacinasDeepLinks } from "./useVacinasDeepLinks";
import { useVacinasRegistroActions } from "./useVacinasRegistroActions";

export function useVetVacinas() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [aba, setAba] = useState("registros");
  const [pessoaFiltro, setPessoaFiltro] = useState("");
  const [tutorFiltroSelecionado, setTutorFiltroSelecionado] = useState(null);
  const [petSelecionado, setPetSelecionado] = useState("");
  const [vacinas, setVacinas] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [novaAberta, setNovaAberta] = useState(false);
  const [tutorFormSelecionado, setTutorFormSelecionado] = useState(null);
  const [form, setForm] = useState(() => criarFormVacinaInicial());
  const [salvando, setSalvando] = useState(false);
  const { carregarVencendo, pets, protocolos, vacinasVencendo, veterinarios } = useVacinasBaseData();
  const {
    calendario,
    carregarCalendarioPreventivo,
    carregandoCalendario,
    especieCalendario,
    setEspecieCalendario,
  } = useVacinasCalendario();

  const petIdQuery = searchParams.get("pet_id") || "";
  const novoPetIdQuery = searchParams.get("novo_pet_id") || "";
  const acaoQuery = searchParams.get("acao") || "";
  const agendamentoIdQuery = searchParams.get("agendamento_id") || "";
  const consultaIdQuery = searchParams.get("consulta_id") || "";
  const tutorIdQuery = searchParams.get("tutor_id") || "";
  const tutorNomeQuery = searchParams.get("tutor_nome") || "";

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

  useVacinasDeepLinks({
    acaoQuery,
    novoPetIdQuery,
    petIdQuery,
    pets,
    setForm,
    setNovaAberta,
    setPessoaFiltro,
    setPetSelecionado,
    setTutorFiltroSelecionado,
    setTutorFormSelecionado,
    tutorFormSelecionado,
    tutorIdQuery,
    tutorNomeQuery,
  });

  const petsDaPessoa = useMemo(() => {
    if (!form.pessoa_id) return [];
    return pets.filter(
      (pet) => String(pet.cliente_id) === String(form.pessoa_id) && pet.ativo !== false
    );
  }, [pets, form.pessoa_id]);

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

  const {
    abrirRegistroPrimeiraVacina,
    fecharModalVacina,
    salvarVacina,
    selecionarTutorFiltro,
    selecionarTutorForm,
    setCampo,
  } = useVacinasRegistroActions({
    acaoQuery,
    agendamentoIdQuery,
    carregarVacinasPet,
    carregarVencendo,
    consultaIdQuery,
    form,
    navigate,
    novoPetIdQuery,
    petIdQuery,
    petSelecionado,
    pets,
    setErro,
    setForm,
    setNovaAberta,
    setPessoaFiltro,
    setPetSelecionado,
    setSalvando,
    setTutorFiltroSelecionado,
    setTutorFormSelecionado,
    sugestaoDose,
  });

  return {
    aba,
    abrirRegistroPrimeiraVacina,
    calendario,
    carregarCalendarioPreventivo,
    carregando,
    carregandoCalendario,
    consultaIdQuery,
    erro,
    especieCalendario,
    fecharModalVacina,
    form,
    novaAberta,
    pessoaFiltro,
    petSelecionado,
    petsDaPessoa,
    petsFiltradosCarteira,
    retornoNovoPet,
    salvando,
    salvarVacina,
    selecionarTutorFiltro,
    selecionarTutorForm,
    setAba,
    setCampo,
    setEspecieCalendario,
    setNovaAberta,
    setPetSelecionado,
    sugestaoDose,
    tutorFiltroSelecionado,
    tutorFormSelecionado,
    vacinas,
    vacinasVencendo,
    veterinarios,
  };
}
