import { useEffect, useRef, useState } from "react";
import api from "../api";
import { formatMoneyBRL } from "../utils/formatters";

export function usePDVAssistente(vendaAtual) {
  const [painelAssistenteAberto, setPainelAssistenteAberto] = useState(false);
  const [mensagensAssistente, setMensagensAssistente] = useState([]);
  const [inputAssistente, setInputAssistente] = useState("");
  const [enviandoAssistente, setEnviandoAssistente] = useState(false);
  const [alertasCarrinho, setAlertasCarrinho] = useState([]);
  const [infosCarrinho, setInfosCarrinho] = useState([]);
  const chatAssistenteEndRef = useRef(null);

  useEffect(() => {
    setMensagensAssistente([]);
    setInputAssistente("");
    setAlertasCarrinho([]);
    setInfosCarrinho([]);
  }, [vendaAtual.cliente?.id]);

  useEffect(() => {
    chatAssistenteEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagensAssistente]);

  useEffect(() => {
    if (vendaAtual.cliente?.id && vendaAtual.itens?.length > 0) {
      const timer = setTimeout(() => {
        void verificarAlertasCarrinho(vendaAtual.cliente.id, vendaAtual.itens);
      }, 800);
      return () => clearTimeout(timer);
    }

    setAlertasCarrinho([]);
    setInfosCarrinho([]);
    return undefined;
  }, [vendaAtual.itens, vendaAtual.cliente?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const carregarInfoCliente = async (clienteId) => {
    if (!clienteId) return;

    try {
      const res = await api.get(`/clientes/${clienteId}/info-pdv`);
      const info = res.data;
      const pets = info.pets?.map((p) => p.nome).join(", ") || "Nenhum";
      const ultimaCompra = info.resumo_financeiro?.ultima_compra;
      const topProdutos =
        info.sugestoes?.slice(0, 3).map((s) => s.nome).join(", ") || "Nenhum";
      const oportunidades = info.oportunidades || [];

      let autoMsg = `Resumo de **${info.cliente?.nome}**:\n`;
      autoMsg += `🛒 ${info.resumo_financeiro?.numero_compras || 0} compras — ticket médio: ${formatMoneyBRL(info.resumo_financeiro?.ticket_medio || 0)}\n`;
      if (ultimaCompra?.data) {
        autoMsg += `📅 Última compra: ${ultimaCompra.data} (${formatMoneyBRL(ultimaCompra.valor || 0)})\n`;
      }
      if (pets !== "Nenhum") autoMsg += `🐾 Pets: ${pets}\n`;
      autoMsg += `⭐ Favoritos: ${topProdutos}\n`;
      if (oportunidades.length > 0) {
        autoMsg += `\n⚠️ ${oportunidades.length} produto(s) para reabastecer:\n`;
        oportunidades.slice(0, 3).forEach((op) => {
          autoMsg += `• ${op.produto_nome} (${op.dias_atraso}d atrasado)\n`;
        });
      }
      autoMsg += "\nPergunta sobre este cliente?";

      setMensagensAssistente([{ role: "assistant", texto: autoMsg }]);
    } catch {
      setMensagensAssistente([
        {
          role: "assistant",
          texto:
            "Não foi possível carregar o histórico. Pode me perguntar qualquer coisa!",
        },
      ]);
    }
  };

  const verificarAlertasCarrinho = async (clienteId, itens) => {
    if (!clienteId || !itens || itens.length === 0) {
      setAlertasCarrinho([]);
      setInfosCarrinho([]);
      return;
    }

    try {
      const payload = {
        itens: itens.map((i) => ({
          produto_id: i.produto_id || null,
          produto_nome: i.produto_nome || i.nome || "",
          quantidade: i.quantidade || 1,
          preco_unitario: i.preco_unitario || 0,
        })),
      };
      const res = await api.post(`/clientes/${clienteId}/alertas-carrinho`, payload);
      setAlertasCarrinho(res.data.alertas || []);
      setInfosCarrinho(res.data.infos || []);
    } catch {
      // silencioso
    }
  };

  const enviarMensagemAssistente = async () => {
    const msg = inputAssistente.trim();
    if (!msg || !vendaAtual.cliente?.id || enviandoAssistente) return;

    setMensagensAssistente((prev) => [...prev, { role: "user", texto: msg }]);
    setInputAssistente("");
    setEnviandoAssistente(true);

    try {
      const carrinhoPayload =
        vendaAtual.itens?.map((i) => ({
          produto_id: i.produto_id || null,
          produto_nome: i.produto_nome || i.nome || "",
          quantidade: i.quantidade || 1,
          preco_unitario: i.preco_unitario || 0,
        })) || [];

      const res = await api.post(`/clientes/${vendaAtual.cliente.id}/chat-pdv`, {
        mensagem: msg,
        carrinho: carrinhoPayload,
      });
      setMensagensAssistente((prev) => [
        ...prev,
        { role: "assistant", texto: res.data.resposta },
      ]);
    } catch {
      setMensagensAssistente((prev) => [
        ...prev,
        { role: "assistant", texto: "Erro ao responder. Tente novamente." },
      ]);
    } finally {
      setEnviandoAssistente(false);
    }
  };

  const alternarPainelAssistente = async () => {
    const abrindo = !painelAssistenteAberto;
    setPainelAssistenteAberto(abrindo);

    if (abrindo && mensagensAssistente.length === 0 && vendaAtual.cliente?.id) {
      await carregarInfoCliente(vendaAtual.cliente.id);
    }
  };

  return {
    painelAssistenteAberto,
    setPainelAssistenteAberto,
    mensagensAssistente,
    inputAssistente,
    setInputAssistente,
    enviandoAssistente,
    chatAssistenteEndRef,
    alertasCarrinho,
    infosCarrinho,
    enviarMensagemAssistente,
    alternarPainelAssistente,
  };
}
