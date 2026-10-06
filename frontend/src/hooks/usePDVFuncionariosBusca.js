import { useState } from "react";
import api from "../api";

export function usePDVFuncionariosBusca() {
  const [funcionariosSugeridos, setFuncionariosSugeridos] = useState([]);
  const [buscaFuncionario, setBuscaFuncionario] = useState("");

  const carregarFuncionariosComissao = async (busca = "") => {
    try {
      const [parceirosResult, funcionariosResult] = await Promise.allSettled([
        api.get("/comissoes/configuracoes/funcionarios"),
        api.get("/funcionarios", { params: { ativo: true } }),
      ]);
      if (parceirosResult.status === "rejected" && funcionariosResult.status === "rejected") {
        throw parceirosResult.reason;
      }
      const parceiros = parceirosResult.status === "fulfilled" ? parceirosResult.value.data.data || [] : [];
      const funcionariosAtivos = funcionariosResult.status === "fulfilled" ? funcionariosResult.value.data || [] : [];
      const funcionarios = [...new Map(
        [...parceiros, ...funcionariosAtivos].map((funcionario) => [funcionario.id, funcionario]),
      ).values()];
      const termo = String(busca || "")
        .trim()
        .toLowerCase();
      const filtrados = termo
        ? funcionarios.filter((funcionario) => funcionario.nome.toLowerCase().includes(termo))
        : funcionarios;

      setFuncionariosSugeridos(filtrados);
      return filtrados;
    } catch (error) {
      console.error("Erro ao buscar funcionarios:", error);
      setFuncionariosSugeridos([]);
      return [];
    }
  };

  return {
    funcionariosSugeridos,
    setFuncionariosSugeridos,
    buscaFuncionario,
    setBuscaFuncionario,
    carregarFuncionariosComissao,
  };
}
