import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../../api";
import { useModulos } from "../../contexts/ModulosContext";
import { vetApi } from "../veterinario/vetApi";
import { DEFAULT_LIST_LIMIT, INITIAL_ABA } from "./petDetalhesConstants";
import {
  createNovoExame,
  filtrarConsultas,
  filtrarVacinas,
  normalizeItemsPayload,
  ordenarConsultasPorData,
  ordenarVacinasPorData,
  selecionarUltimaAlta,
} from "./petDetalhesUtils";

export function usePetDetalhesController() {
  const { petId } = useParams();
  const navigate = useNavigate();
  const { moduloAtivo } = useModulos();
  const moduloVeterinarioAtivo = moduloAtivo("veterinario");

  const [pet, setPet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [abaAtiva, setAbaAtiva] = useState(INITIAL_ABA);
  const [historicoInternacoes, setHistoricoInternacoes] = useState([]);
  const [loadingInternacoes, setLoadingInternacoes] = useState(false);
  const [historicoVacinas, setHistoricoVacinas] = useState([]);
  const [loadingVacinas, setLoadingVacinas] = useState(false);
  const [historicoConsultas, setHistoricoConsultas] = useState([]);
  const [loadingConsultas, setLoadingConsultas] = useState(false);
  const [filtroVacinas, setFiltroVacinas] = useState("");
  const [filtroConsultas, setFiltroConsultas] = useState("");
  const [limiteVacinas, setLimiteVacinas] = useState(DEFAULT_LIST_LIMIT);
  const [limiteConsultas, setLimiteConsultas] = useState(DEFAULT_LIST_LIMIT);
  const [ultimaVacina, setUltimaVacina] = useState(null);
  const [ultimaAlta, setUltimaAlta] = useState(null);
  const [carteirinha, setCarteirinha] = useState(null);
  const [exames, setExames] = useState([]);
  const [loadingExames, setLoadingExames] = useState(false);
  const [salvandoExame, setSalvandoExame] = useState(false);
  const [novoExame, setNovoExame] = useState(createNovoExame);

  useEffect(() => {
    loadPet();
  }, [petId]);

  useEffect(() => {
    if (!moduloVeterinarioAtivo) {
      setCarteirinha(null);
      setUltimaVacina(null);
      setUltimaAlta(null);
      return;
    }
    carregarResumoClinico();
  }, [petId, moduloVeterinarioAtivo]);

  useEffect(() => {
    if (abaAtiva === "internacoes") carregarHistoricoInternacoes();
    if (abaAtiva === "vacinas") carregarHistoricoVacinas();
    if (abaAtiva === "consultas") carregarHistoricoConsultas();
    if (abaAtiva === "saude") carregarExames();
  }, [abaAtiva, petId]);

  useEffect(() => {
    if (abaAtiva === "vacinas") setLimiteVacinas(DEFAULT_LIST_LIMIT);
  }, [abaAtiva, filtroVacinas]);

  useEffect(() => {
    if (abaAtiva === "consultas") setLimiteConsultas(DEFAULT_LIST_LIMIT);
  }, [abaAtiva, filtroConsultas]);

  async function loadPet() {
    try {
      setLoading(true);
      const response = await api.get(`/pets/${petId}`);
      setPet(response.data);
      setError("");
    } catch (err) {
      console.error("Erro ao carregar pet:", err);
      setError("Erro ao carregar informaÃ§Ãµes do pet");
    } finally {
      setLoading(false);
    }
  }

  async function carregarHistoricoInternacoes() {
    if (!moduloVeterinarioAtivo) return;
    try {
      setLoadingInternacoes(true);
      const response = await vetApi.historicoInternacoesPet(petId);
      const lista = Array.isArray(response.data?.historico) ? response.data.historico : [];
      setHistoricoInternacoes(lista);
    } catch {
      setHistoricoInternacoes([]);
    } finally {
      setLoadingInternacoes(false);
    }
  }

  async function carregarHistoricoVacinas() {
    if (!moduloVeterinarioAtivo) return;
    try {
      setLoadingVacinas(true);
      const response = await vetApi.listarVacinasPet(petId);
      setHistoricoVacinas(ordenarVacinasPorData(normalizeItemsPayload(response.data)));
    } catch {
      setHistoricoVacinas([]);
    } finally {
      setLoadingVacinas(false);
    }
  }

  async function carregarHistoricoConsultas() {
    if (!moduloVeterinarioAtivo) return;
    try {
      setLoadingConsultas(true);
      const response = await vetApi.listarConsultas({ pet_id: petId, limit: 200 });
      setHistoricoConsultas(ordenarConsultasPorData(normalizeItemsPayload(response.data)));
    } catch {
      setHistoricoConsultas([]);
    } finally {
      setLoadingConsultas(false);
    }
  }

  async function carregarExames() {
    if (!moduloVeterinarioAtivo) return;
    try {
      setLoadingExames(true);
      const response = await vetApi.listarExamesPet(petId);
      setExames(normalizeItemsPayload(response.data));
    } catch {
      setExames([]);
    } finally {
      setLoadingExames(false);
    }
  }

  async function carregarResumoClinico() {
    if (!moduloVeterinarioAtivo) return;
    try {
      const [resCarteirinha, resHistoricoInternacoes] = await Promise.all([
        vetApi.obterCarteirinhaPet(petId).catch(() => ({ data: null })),
        vetApi.historicoInternacoesPet(petId).catch(() => ({ data: { historico: [] } })),
      ]);

      const resumoCarteirinha = resCarteirinha.data || null;
      setCarteirinha(resumoCarteirinha);

      const listaVacinas = Array.isArray(resumoCarteirinha?.status_vacinal?.carteira)
        ? resumoCarteirinha.status_vacinal.carteira
        : [];
      setUltimaVacina(ordenarVacinasPorData(listaVacinas)[0] ?? null);

      const historico = Array.isArray(resHistoricoInternacoes.data?.historico)
        ? resHistoricoInternacoes.data.historico
        : [];
      setUltimaAlta(selecionarUltimaAlta(historico) ?? null);
    } catch {
      setCarteirinha(null);
      setUltimaVacina(null);
      setUltimaAlta(null);
    }
  }

  async function interpretarExameIA(exameId) {
    try {
      await vetApi.interpretarExameIA(exameId);
      await Promise.all([carregarExames(), carregarResumoClinico()]);
    } catch (err) {
      alert(err.response?.data?.detail || "NÃ£o foi possÃ­vel interpretar o exame com IA");
    }
  }

  async function toggleAtivacao() {
    try {
      if (pet.ativo) {
        await api.delete(`/pets/${pet.id}?soft_delete=true`);
      } else {
        await api.post(`/pets/${pet.id}/ativar`);
      }
      loadPet();
    } catch (err) {
      console.error("Erro ao alterar status do pet:", err);
      alert("Erro ao alterar status do pet");
    }
  }

  async function salvarNovoExame() {
    if (!moduloVeterinarioAtivo || !novoExame.nome.trim()) return;

    try {
      setSalvandoExame(true);
      const response = await vetApi.criarExame({
        pet_id: Number(petId),
        nome: novoExame.nome,
        tipo: novoExame.tipo,
        data_solicitacao: novoExame.data_solicitacao || undefined,
        laboratorio: novoExame.laboratorio || undefined,
        observacoes: novoExame.observacoes || undefined,
      });

      if (novoExame.arquivo) {
        await vetApi.uploadArquivoExame(response.data.id, novoExame.arquivo);
      }

      setNovoExame(createNovoExame());
      await carregarExames();
    } catch (err) {
      console.error("Erro ao salvar exame:", err);
      alert(err.response?.data?.detail || "Erro ao salvar exame");
    } finally {
      setSalvandoExame(false);
    }
  }

  return {
    abaAtiva,
    abrirConsulta: (consultaId) => navigate(`/veterinario/consultas/${consultaId}`),
    abrirModuloInternacoes: () => navigate("/veterinario/internacoes"),
    carregarExames,
    carteirinha,
    consultasFiltradas: filtrarConsultas(historicoConsultas, filtroConsultas),
    editarPet: () => navigate(`/pets/${pet.id}/editar`),
    error,
    exames,
    filtroConsultas,
    filtroVacinas,
    historicoInternacoes,
    interpretarExameIA,
    limiteConsultas,
    limiteVacinas,
    loading,
    loadingConsultas,
    loadingExames,
    loadingInternacoes,
    loadingVacinas,
    novaConsulta: () => navigate(`/veterinario/consultas/nova?pet_id=${pet.id}`),
    novoExame,
    pet,
    registrarVacina: () => navigate(`/veterinario/vacinas?pet_id=${pet.id}&acao=novo`),
    salvandoExame,
    salvarNovoExame,
    setAbaAtiva,
    setFiltroConsultas,
    setFiltroVacinas,
    setLimiteConsultas,
    setLimiteVacinas,
    setNovoExame,
    toggleAtivacao,
    ultimaAlta,
    ultimaVacina,
    vacinasFiltradas: filtrarVacinas(historicoVacinas, filtroVacinas),
    voltarParaPets: () => navigate("/pets"),
  };
}
