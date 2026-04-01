import { useState } from "react";

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
    if (!cep || cep.length !== 9) return;

    setLoadingCepEndereco(true);
    try {
      const response = await fetch(
        `https://viacep.com.br/ws/${cep.replace("-", "")}/json/`,
      );
      const data = await response.json();

      if (data.erro) {
        alert("CEP nao encontrado");
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
      setLoadingCepEndereco(false);
    }
  };

  const salvarEndereco = () => {
    if (
      !enderecoAtual?.cep ||
      !enderecoAtual?.endereco ||
      !enderecoAtual?.cidade
    ) {
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

  const removerEndereco = (index) => {
    if (confirm("Deseja realmente remover este endereco?")) {
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
