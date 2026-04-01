import { useState } from "react";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";

const criarEnderecoVazio = () => ({
  tipo: "entrega",
  apelido: "",
  cep: "",
  endereco: "",
  numero: "",
  complemento: "",
  bairro: "",
  cidade: "",
  estado: "",
});

export function usePDVEndereco({ vendaAtual, setVendaAtual }) {
  const [mostrarModalEndereco, setMostrarModalEndereco] = useState(false);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [loadingCep, setLoadingCep] = useState(false);

  const abrirModalEndereco = () => {
    setEnderecoAtual(criarEnderecoVazio());
    setMostrarModalEndereco(true);
  };

  const fecharModalEndereco = () => {
    setMostrarModalEndereco(false);
    setEnderecoAtual(null);
  };

  const buscarCepModal = async (cep) => {
    if (!cep || cep.length !== 9) return;

    setLoadingCep(true);
    try {
      const response = await fetch(
        `https://viacep.com.br/ws/${cep.replace("-", "")}/json/`,
      );
      const data = await response.json();

      if (data.erro) {
        alert("CEP não encontrado");
        return;
      }

      setEnderecoAtual((prev) => ({
        ...prev,
        endereco: data.logradouro || "",
        bairro: data.bairro || "",
        cidade: data.localidade || "",
        estado: data.uf || "",
      }));
    } catch (error) {
      console.error("Erro ao buscar CEP:", error);
      alert("Erro ao buscar CEP");
    } finally {
      setLoadingCep(false);
    }
  };

  const salvarEnderecoNoCliente = async () => {
    if (
      !enderecoAtual?.cep ||
      !enderecoAtual.endereco ||
      !enderecoAtual.cidade
    ) {
      alert("Preencha pelo menos CEP, Endereço e Cidade");
      return;
    }

    if (!vendaAtual.cliente?.id) {
      alert("Selecione um cliente primeiro");
      return;
    }

    try {
      const clienteAtual = await buscarClientePorId(vendaAtual.cliente.id);
      const enderecosAdicionais = clienteAtual.enderecos_adicionais || [];
      enderecosAdicionais.push({ ...enderecoAtual });

      await api.put(`/clientes/${vendaAtual.cliente.id}`, {
        ...clienteAtual,
        enderecos_adicionais: enderecosAdicionais,
      });

      const clienteAtualizado = await buscarClientePorId(vendaAtual.cliente.id);
      setVendaAtual((prev) => ({
        ...prev,
        cliente: clienteAtualizado,
      }));

      alert("Endereço adicionado com sucesso!");
      fecharModalEndereco();
    } catch (error) {
      console.error("Erro ao salvar endereço:", error);
      alert("Erro ao salvar endereço. Tente novamente.");
    }
  };

  return {
    mostrarModalEndereco,
    enderecoAtual,
    setEnderecoAtual,
    loadingCep,
    abrirModalEndereco,
    fecharModalEndereco,
    buscarCepModal,
    salvarEnderecoNoCliente,
  };
}
