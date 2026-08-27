import { useEffect, useState } from "react";
import { api } from "../../../services/api";
import {
  buildEntregasPayload,
  createInitialEntregasForm,
  nextTierLimit,
  normalizeEntregadores,
  normalizeEntregasConfig,
  validateEntregasForm,
} from "./entregasConfigUtils";

export function useEntregasConfigController() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [entregadores, setEntregadores] = useState([]);
  const [form, setForm] = useState(createInitialEntregasForm);

  useEffect(() => {
    async function load() {
      try {
        const [cfg, pessoas] = await Promise.all([
          api.get("/configuracoes/entregas"),
          api.get("/clientes/", {
            params: {
              is_entregador: true,
              entregador_ativo: true,
            },
          }),
        ]);
        setForm(normalizeEntregasConfig(cfg.data));
        const entregadoresList = normalizeEntregadores(pessoas.data);
        console.log("🚚 Entregadores carregados:", entregadoresList);
        setEntregadores(entregadoresList);
      } catch (error) {
        console.error("❌ Erro ao carregar configurações:", error);
        alert("Erro ao carregar configurações de entrega");
        setEntregadores([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function buscarCep() {
    const cep = form.cep.replace(/\D/g, "");
    if (cep.length !== 8) {
      alert("CEP inválido. Digite 8 dígitos.");
      return;
    }

    setBuscandoCep(true);
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = await response.json();
      if (data.erro) {
        alert("CEP não encontrado");
        return;
      }
      setForm({
        ...form,
        logradouro: data.logradouro || "",
        bairro: data.bairro || "",
        cidade: data.localidade || "",
        estado: data.uf || "",
      });
    } catch (error) {
      console.error(error);
      alert("Erro ao buscar CEP");
    } finally {
      setBuscandoCep(false);
    }
  }

  function changeBillingMode(modalidade) {
    setForm((current) => ({
      ...current,
      modalidade_cobranca: modalidade,
      faixas_distancia:
        modalidade === "por_faixa" && current.faixas_distancia.length === 0
          ? [{ ate_km: "1", valor: 0 }]
          : current.faixas_distancia,
    }));
  }

  function updateDistanceTier(index, field, value) {
    setForm((current) => ({
      ...current,
      faixas_distancia: current.faixas_distancia.map((tier, tierIndex) =>
        tierIndex === index ? { ...tier, [field]: value } : tier,
      ),
    }));
  }

  function addDistanceTier() {
    setForm((current) => ({
      ...current,
      faixas_distancia: [
        ...current.faixas_distancia,
        { ate_km: nextTierLimit(current.faixas_distancia), valor: 0 },
      ],
    }));
  }

  function removeDistanceTier(index) {
    setForm((current) => ({
      ...current,
      faixas_distancia: current.faixas_distancia.filter((_tier, tierIndex) => tierIndex !== index),
    }));
  }

  async function handleSave(event) {
    event.preventDefault();
    const validationError = validateEntregasForm(form);
    if (validationError) {
      alert(validationError);
      return;
    }

    setSaving(true);
    try {
      await api.put("/configuracoes/entregas", buildEntregasPayload(form));
      alert("Configurações salvas com sucesso");
    } catch (error) {
      console.error(error);
      alert("Erro ao salvar configurações");
    } finally {
      setSaving(false);
    }
  }

  return {
    addDistanceTier,
    buscandoCep,
    buscarCep,
    changeBillingMode,
    entregadores,
    form,
    handleSave,
    loading,
    removeDistanceTier,
    saving,
    setForm,
    updateDistanceTier,
  };
}
