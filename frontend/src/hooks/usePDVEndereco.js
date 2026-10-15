import { useState } from "react";
import api from "../api";
import { buscarClientePorId } from "../api/clientes";
import { criarPayloadEnderecoAdicional } from "./pdvEndereco";
import { resolveCepMunicipio } from "../utils/cepMunicipio";

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
  codigo_municipio: "",
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
    const cepConsultado = String(cep || "").replace(/\D/g, "");
    if (cepConsultado.length !== 8) return;

    setLoadingCep(true);
    try {
      const data = await resolveCepMunicipio(cep);

      setEnderecoAtual((prev) => {
        if (!prev || String(prev.cep || "").replace(/\D/g, "") !== cepConsultado) return prev;
        return {
          ...prev,
          endereco: data.endereco,
          bairro: data.bairro || "",
          cidade: data.cidade,
          estado: data.estado,
          codigo_municipio: data.codigo_municipio,
        };
      });
    } catch (error) {
      console.error("Erro ao buscar CEP:", error);
      alert(error.message || "Erro ao buscar CEP");
    } finally {
      setLoadingCep(false);
    }
  };

  const salvarEnderecoNoCliente = async () => {
    if (!enderecoAtual?.endereco || !enderecoAtual.cidade) {
      alert("Preencha pelo menos Endereço e Cidade");
      return;
    }

    if (!vendaAtual.cliente?.id) {
      alert("Selecione um cliente primeiro");
      return;
    }

    try {
      const clienteAtual = await buscarClientePorId(vendaAtual.cliente.id);
      const payload = criarPayloadEnderecoAdicional(clienteAtual, enderecoAtual);

      await api.put(`/clientes/${vendaAtual.cliente.id}`, payload);

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
