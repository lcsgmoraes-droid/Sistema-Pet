import { useState } from "react";
import api from "../api";

export function usePDVFuncionariosBusca() {
  const [funcionariosSugeridos, setFuncionariosSugeridos] = useState([]);
  const [buscaFuncionario, setBuscaFuncionario] = useState("");

  const carregarFuncionariosComissao = async (busca = "") => {
    try {
      const response = await api.get("/comissoes/configuracoes/funcionarios");
      const funcionarios = response.data.data || [];
      const termo = String(busca || "").trim().toLowerCase();
      const filtrados = termo
        ? funcionarios.filter((funcionario) =>
            funcionario.nome.toLowerCase().includes(termo),
          )
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
