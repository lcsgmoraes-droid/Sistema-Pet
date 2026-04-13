import { useState } from "react";
import toast from "react-hot-toast";
import api from "../api";

export default function useProdutosEdicao({
  carregarDados,
  selecionados,
  setSelecionados,
}) {
  const [editandoPreco, setEditandoPreco] = useState(null);
  const [novoPreco, setNovoPreco] = useState("");
  const [modalEdicaoLote, setModalEdicaoLote] = useState(false);
  const [dadosEdicaoLote, setDadosEdicaoLote] = useState({
    marca_id: "",
    categoria_id: "",
    departamento_id: "",
    anunciar_ecommerce: "",
    anunciar_app: "",
  });

  const handleEditarPreco = (produtoId, precoAtual) => {
    setEditandoPreco(produtoId);
    setNovoPreco(precoAtual.toString());
  };

  const handleSalvarPreco = async (produtoId) => {
    try {
      await api.patch(`/produtos/${produtoId}?preco_venda=${novoPreco}`, {});
      toast.success("PreÃ§o atualizado!");
      setEditandoPreco(null);
      carregarDados();
    } catch (error) {
      console.error("Erro ao atualizar preÃ§o:", error);
      toast.error("Erro ao atualizar preÃ§o");
    }
  };

  const handleCancelarEdicaoPreco = () => {
    setEditandoPreco(null);
  };

  const handleAbrirEdicaoLote = () => {
    if (selecionados.length === 0) {
      toast.error("Selecione pelo menos um produto");
      return;
    }

    setDadosEdicaoLote({
      marca_id: "",
      categoria_id: "",
      departamento_id: "",
      anunciar_ecommerce: "",
      anunciar_app: "",
    });
    setModalEdicaoLote(true);
  };

  const handleSalvarEdicaoLote = async () => {
    try {
      const camposPreenchidos = Object.values(dadosEdicaoLote).filter(
        (value) => value !== "",
      );
      if (camposPreenchidos.length === 0) {
        toast.error("Preencha pelo menos um campo para atualizar");
        return;
      }

      const dadosEnvio = {};
      if (dadosEdicaoLote.marca_id) {
        dadosEnvio.marca_id = parseInt(dadosEdicaoLote.marca_id, 10);
      }
      if (dadosEdicaoLote.categoria_id) {
        dadosEnvio.categoria_id = parseInt(dadosEdicaoLote.categoria_id, 10);
      }
      if (dadosEdicaoLote.departamento_id) {
        dadosEnvio.departamento_id = parseInt(dadosEdicaoLote.departamento_id, 10);
      }
      if (dadosEdicaoLote.anunciar_ecommerce !== "") {
        dadosEnvio.anunciar_ecommerce = dadosEdicaoLote.anunciar_ecommerce === "true";
      }
      if (dadosEdicaoLote.anunciar_app !== "") {
        dadosEnvio.anunciar_app = dadosEdicaoLote.anunciar_app === "true";
      }

      await api.patch("/produtos/atualizar-lote", {
        produto_ids: selecionados,
        ...dadosEnvio,
      });

      toast.success(
        `${selecionados.length} produto(s) atualizado(s) com sucesso!`,
      );
      setModalEdicaoLote(false);
      setSelecionados([]);
      carregarDados();
    } catch (error) {
      console.error("Erro ao atualizar produtos:", error);
      toast.error("Erro ao atualizar produtos");
    }
  };

  return {
    dadosEdicaoLote,
    editandoPreco,
    handleAbrirEdicaoLote,
    handleCancelarEdicaoPreco,
    handleEditarPreco,
    handleSalvarEdicaoLote,
    handleSalvarPreco,
    modalEdicaoLote,
    novoPreco,
    setDadosEdicaoLote,
    setModalEdicaoLote,
    setNovoPreco,
  };
}
