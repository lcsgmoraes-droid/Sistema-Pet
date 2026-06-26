import api from "../../api";
import { extrairListaProdutos } from "../calculadoraRacaoUtils";

export async function buscarRacoesNoCadastro(termo, pageSize = 80) {
  const response = await api.get("/produtos/calculadora-racao/opcoes", {
    params: {
      busca: String(termo || "").trim() || undefined,
      page: 1,
      page_size: pageSize,
      _ts: Date.now(),
    },
  });

  return extrairListaProdutos(response.data);
}

export async function carregarProdutosCalculadora() {
  const response = await api.get("/produtos/calculadora-racao/opcoes", {
    params: {
      page: 1,
      page_size: 1200,
      _ts: Date.now(),
    },
  });

  return response.data;
}

export async function carregarPetsCalculadora() {
  const response = await api.get("/clientes/pets/todos");
  return Array.isArray(response.data) ? response.data : [];
}

export async function calcularRacao(payload) {
  const response = await api.post("/produtos/calculadora-racao", payload);
  return response.data;
}

export async function compararRacoesPorFiltros(params) {
  const response = await api.post("/produtos/comparar-racoes", null, { params });
  return response.data?.racoes || [];
}
