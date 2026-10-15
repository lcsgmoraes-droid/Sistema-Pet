import { useState } from "react";
import { confirmarCorePet } from "../services/corepetDialog";
import { resolveCepMunicipio } from "../utils/cepMunicipio";

const createEnderecoVazio = () => ({
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

export function useClientesNovoEnderecos() {
  const [enderecosAdicionais, setEnderecosAdicionais] = useState([]);
  const [enderecoAtual, setEnderecoAtual] = useState(null);
  const [mostrarFormEndereco, setMostrarFormEndereco] = useState(false);
  const [loadingCepEndereco, setLoadingCepEndereco] = useState(false);

  const abrirModalEndereco = (index = null) => {
    if (index !== null) {
      setEnderecoAtual({ ...enderecosAdicionais[index], index });
    } else {
      setEnderecoAtual(createEnderecoVazio());
    }
    setMostrarFormEndereco(true);
  };

  const fecharModalEndereco = () => {
    setMostrarFormEndereco(false);
    setEnderecoAtual(null);
  };

  const buscarCepModal = async (cep) => {
    const cepConsultado = String(cep || "").replace(/\D/g, "");
    if (cepConsultado.length !== 8) return;

    setLoadingCepEndereco(true);
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
      setLoadingCepEndereco(false);
    }
  };

  const salvarEndereco = () => {
    if (!enderecoAtual?.cep || !enderecoAtual?.endereco || !enderecoAtual?.cidade) {
      alert("Preencha pelo menos CEP, Endereco e Cidade");
      return;
    }

    const novosEnderecos = [...enderecosAdicionais];

    if (enderecoAtual.index !== undefined) {
      novosEnderecos[enderecoAtual.index] = { ...enderecoAtual };
      delete novosEnderecos[enderecoAtual.index].index;
    } else {
      novosEnderecos.push({ ...enderecoAtual });
    }

    setEnderecosAdicionais(novosEnderecos);
    fecharModalEndereco();
  };

  const removerEndereco = async (index) => {
    if (await confirmarCorePet("Deseja realmente remover este endereco?")) {
      setEnderecosAdicionais((prev) => prev.filter((_, i) => i !== index));
    }
  };

  return {
    enderecosAdicionais,
    setEnderecosAdicionais,
    enderecoAtual,
    setEnderecoAtual,
    mostrarFormEndereco,
    loadingCepEndereco,
    abrirModalEndereco,
    fecharModalEndereco,
    buscarCepModal,
    salvarEndereco,
    removerEndereco,
  };
}
