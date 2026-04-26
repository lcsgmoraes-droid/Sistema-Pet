import { useCallback, useEffect, useRef, useState } from "react";

import { vetApi } from "../vetApi";
import { FORM_CONSULTORIO_INICIAL, FORM_PARCEIRO_INICIAL } from "./configuracoesConstants";

export function useVetConfiguracoes() {
  const sucessoTimerRef = useRef(null);
  const [parceiros, setParceiros] = useState([]);
  const [tenantsVet, setTenantsVet] = useState([]);
  const [consultorios, setConsultorios] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [parceiroForm, setParceiroForm] = useState(FORM_PARCEIRO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [mostrarFormConsultorio, setMostrarFormConsultorio] = useState(false);
  const [consultorioForm, setConsultorioForm] = useState(FORM_CONSULTORIO_INICIAL);

  const mostrarSucesso = useCallback((mensagem) => {
    window.clearTimeout(sucessoTimerRef.current);
    setSucesso(mensagem);
    sucessoTimerRef.current = window.setTimeout(() => setSucesso(null), 3000);
  }, []);

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const [parcRes, tenRes, consultRes] = await Promise.all([
        vetApi.listarParceiros(),
        vetApi.listarTenantsVeterinarios(),
        vetApi.listarConsultorios({ ativos_only: false }),
      ]);
      setParceiros(Array.isArray(parcRes.data) ? parcRes.data : []);
      setTenantsVet(Array.isArray(tenRes.data) ? tenRes.data : []);
      setConsultorios(Array.isArray(consultRes.data) ? consultRes.data : []);
    } catch {
      setErro("Não foi possível carregar as configurações de parceria.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();

    return () => {
      window.clearTimeout(sucessoTimerRef.current);
    };
  }, [carregar]);

  const atualizarParceiroForm = useCallback((patch) => {
    setParceiroForm((prev) => ({ ...prev, ...patch }));
  }, []);

  const atualizarConsultorioForm = useCallback((patch) => {
    setConsultorioForm((prev) => ({ ...prev, ...patch }));
  }, []);

  const salvarNovoParceiro = useCallback(async () => {
    if (!parceiroForm.vetTenantId) {
      setErro("Selecione o tenant veterinário parceiro.");
      return;
    }

    try {
      setSalvando(true);
      setErro(null);
      await vetApi.criarParceiro({
        vet_tenant_id: parceiroForm.vetTenantId,
        tipo_relacao: parceiroForm.tipoRelacao,
        comissao_empresa_pct: parceiroForm.comissao ? Number.parseFloat(parceiroForm.comissao) : null,
      });
      mostrarSucesso("Parceiro cadastrado com sucesso!");
      setMostrarForm(false);
      setParceiroForm(FORM_PARCEIRO_INICIAL);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao cadastrar parceiro.");
    } finally {
      setSalvando(false);
    }
  }, [carregar, mostrarSucesso, parceiroForm]);

  const toggleAtivoParceiro = useCallback(async (parceiro) => {
    try {
      await vetApi.atualizarParceiro(parceiro.id, { ativo: !parceiro.ativo });
      setParceiros((prev) =>
        prev.map((item) => (item.id === parceiro.id ? { ...item, ativo: !parceiro.ativo } : item))
      );
    } catch {
      setErro("Não foi possível atualizar o parceiro.");
    }
  }, []);

  const removerParceiro = useCallback(
    async (id) => {
      if (!window.confirm("Tem certeza que deseja remover este vínculo de parceria?")) return;

      try {
        await vetApi.removerParceiro(id);
        setParceiros((prev) => prev.filter((item) => item.id !== id));
        mostrarSucesso("Parceiro removido.");
      } catch {
        setErro("Erro ao remover parceiro.");
      }
    },
    [mostrarSucesso]
  );

  const salvarNovoConsultorio = useCallback(async () => {
    if (!consultorioForm.nome.trim()) {
      setErro("Informe o nome do consultório.");
      return;
    }

    try {
      setSalvando(true);
      setErro(null);
      await vetApi.criarConsultorio({
        nome: consultorioForm.nome.trim(),
        descricao: consultorioForm.descricao.trim() || undefined,
        ordem: consultorioForm.ordem ? Number.parseInt(consultorioForm.ordem, 10) : undefined,
      });
      mostrarSucesso("Consultório cadastrado com sucesso!");
      setMostrarFormConsultorio(false);
      setConsultorioForm(FORM_CONSULTORIO_INICIAL);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao cadastrar consultório.");
    } finally {
      setSalvando(false);
    }
  }, [carregar, consultorioForm, mostrarSucesso]);

  const toggleAtivoConsultorio = useCallback(async (consultorio) => {
    try {
      await vetApi.atualizarConsultorio(consultorio.id, { ativo: !consultorio.ativo });
      setConsultorios((prev) =>
        prev.map((item) =>
          item.id === consultorio.id ? { ...item, ativo: !consultorio.ativo } : item
        )
      );
    } catch (e) {
      setErro(e?.response?.data?.detail || "Não foi possível atualizar o consultório.");
    }
  }, []);

  const removerConsultorio = useCallback(
    async (consultorio) => {
      if (!window.confirm(`Deseja remover o consultório "${consultorio.nome}"?`)) return;

      try {
        await vetApi.removerConsultorio(consultorio.id);
        setConsultorios((prev) => prev.filter((item) => item.id !== consultorio.id));
        mostrarSucesso("Consultório removido.");
      } catch (e) {
        setErro(e?.response?.data?.detail || "Erro ao remover consultório.");
      }
    },
    [mostrarSucesso]
  );

  const cancelarParceiro = useCallback(() => {
    setMostrarForm(false);
    setErro(null);
  }, []);

  const cancelarConsultorio = useCallback(() => {
    setMostrarFormConsultorio(false);
    setConsultorioForm(FORM_CONSULTORIO_INICIAL);
  }, []);

  return {
    atualizarConsultorioForm,
    atualizarParceiroForm,
    cancelarConsultorio,
    cancelarParceiro,
    carregar,
    carregando,
    consultorioForm,
    consultorios,
    erro,
    mostrarForm,
    mostrarFormConsultorio,
    parceiroForm,
    parceiros,
    removerConsultorio,
    removerParceiro,
    salvando,
    salvarNovoConsultorio,
    salvarNovoParceiro,
    setErro,
    setMostrarForm,
    setMostrarFormConsultorio,
    sucesso,
    tenantsVet,
    toggleAtivoConsultorio,
    toggleAtivoParceiro,
  };
}
