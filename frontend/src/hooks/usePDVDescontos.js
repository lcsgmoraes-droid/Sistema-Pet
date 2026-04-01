import { useState } from "react";
import api from "../api";

export function usePDVDescontos({ vendaAtual, setVendaAtual }) {
  const [mostrarModalDescontoItem, setMostrarModalDescontoItem] =
    useState(false);
  const [itemEditando, setItemEditando] = useState(null);
  const [mostrarModalDescontoTotal, setMostrarModalDescontoTotal] =
    useState(false);
  const [tipoDescontoTotal, setTipoDescontoTotal] = useState("valor");
  const [valorDescontoTotal, setValorDescontoTotal] = useState(0);
  const [codigoCupom, setCodigoCupom] = useState("");
  const [cupomAplicado, setCupomAplicado] = useState(null);
  const [loadingCupom, setLoadingCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState("");

  const recalcularTotais = (itens) => {
    const subtotal = itens.reduce((sum, item) => sum + item.subtotal, 0);
    const descontoItens = itens.reduce(
      (sum, item) => sum + (item.desconto_valor || 0),
      0,
    );
    const totalBruto = subtotal + descontoItens;
    const descontoPercentual =
      totalBruto > 0 ? (descontoItens / totalBruto) * 100 : 0;
    const taxaEntrega = vendaAtual.tem_entrega
      ? vendaAtual.entrega?.taxa_entrega_total || 0
      : 0;
    const total = subtotal + taxaEntrega;

    setVendaAtual((prev) => ({
      ...prev,
      itens,
      subtotal,
      desconto_valor: descontoItens,
      desconto_percentual: descontoPercentual,
      total,
    }));
  };

  const abrirModalDescontoItem = (item) => {
    setItemEditando({
      ...item,
      preco: item.preco_unitario,
      descontoValor: item.desconto_valor || 0,
      descontoPercentual: item.desconto_percentual || 0,
      tipoDesconto: "valor",
    });
    setMostrarModalDescontoItem(true);
  };

  const salvarDescontoItem = () => {
    const itensAtualizados = vendaAtual.itens.map((item) => {
      if (item.produto_id === itemEditando.produto_id) {
        const precoUnitario = itemEditando.preco;
        const quantidade = item.quantidade;
        const subtotalSemDesconto = precoUnitario * quantidade;
        let descontoValor = 0;
        let descontoPercentual = 0;

        if (itemEditando.tipoDesconto === "valor") {
          descontoValor = parseFloat(itemEditando.descontoValor) || 0;
          descontoPercentual =
            subtotalSemDesconto > 0
              ? (descontoValor / subtotalSemDesconto) * 100
              : 0;
        } else {
          descontoPercentual = parseFloat(itemEditando.descontoPercentual) || 0;
          descontoValor = (subtotalSemDesconto * descontoPercentual) / 100;
        }

        const precoComDesconto = precoUnitario - descontoValor / quantidade;
        const subtotal = subtotalSemDesconto - descontoValor;

        return {
          ...item,
          desconto_valor: descontoValor,
          desconto_percentual: descontoPercentual,
          tipo_desconto_aplicado: itemEditando.tipoDesconto,
          preco_com_desconto: precoComDesconto,
          subtotal,
        };
      }
      return item;
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoItem(false);
    setItemEditando(null);
  };

  const removerItemEditando = () => {
    if (!itemEditando) return;
    const novosItens = vendaAtual.itens.filter(
      (item) => item.produto_id !== itemEditando.produto_id,
    );
    recalcularTotais(novosItens);
    setMostrarModalDescontoItem(false);
    setItemEditando(null);
  };

  const abrirModalDescontoTotal = () => {
    if (vendaAtual.desconto_valor > 0) {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(vendaAtual.desconto_valor);
    } else {
      setTipoDescontoTotal("valor");
      setValorDescontoTotal(0);
    }
    setMostrarModalDescontoTotal(true);
  };

  const aplicarDescontoTotal = (tipoDesconto, valor) => {
    const itens = vendaAtual.itens;
    if (itens.length === 0) return;

    const subtotaisBrutos = itens.map(
      (item) => (item.preco_unitario || item.preco_venda) * item.quantidade,
    );
    const totalBruto = subtotaisBrutos.reduce((sum, v) => sum + v, 0);

    let descontoTotal = 0;
    if (tipoDesconto === "valor") {
      descontoTotal = Math.min(parseFloat(valor) || 0, totalBruto);
    } else {
      const pct = Math.min(parseFloat(valor) || 0, 100);
      descontoTotal = (totalBruto * pct) / 100;
    }

    let descontoAlocado = 0;
    const itensAtualizados = itens.map((item, idx) => {
      const subtotalBrutoItem = subtotaisBrutos[idx];
      let descontoItem;

      if (idx === itens.length - 1) {
        descontoItem = parseFloat((descontoTotal - descontoAlocado).toFixed(2));
      } else {
        const proporcao = totalBruto > 0 ? subtotalBrutoItem / totalBruto : 0;
        descontoItem = parseFloat((descontoTotal * proporcao).toFixed(2));
        descontoAlocado += descontoItem;
      }

      const descontoPercentual =
        subtotalBrutoItem > 0 ? (descontoItem / subtotalBrutoItem) * 100 : 0;
      const subtotal = subtotalBrutoItem - descontoItem;
      const precoComDesconto =
        item.quantidade > 0 ? subtotal / item.quantidade : 0;

      return {
        ...item,
        desconto_valor: descontoItem,
        desconto_percentual: descontoPercentual,
        tipo_desconto_aplicado: tipoDesconto,
        preco_com_desconto: precoComDesconto,
        subtotal,
      };
    });

    recalcularTotais(itensAtualizados);
    setMostrarModalDescontoTotal(false);
  };

  const removerDescontoTotal = () => {
    const itensAtualizados = vendaAtual.itens.map((item) => {
      const subtotalBruto =
        (item.preco_unitario || item.preco_venda) * item.quantidade;
      return {
        ...item,
        desconto_valor: 0,
        desconto_percentual: 0,
        tipo_desconto_aplicado: null,
        preco_com_desconto: item.preco_unitario || item.preco_venda,
        subtotal: subtotalBruto,
      };
    });
    recalcularTotais(itensAtualizados);
  };

  const aplicarCupom = async () => {
    const code = codigoCupom.trim().toUpperCase();
    if (!code) return;
    if (vendaAtual.itens.length === 0) {
      setErroCupom("Adicione itens à venda antes de aplicar um cupom.");
      return;
    }
    setLoadingCupom(true);
    setErroCupom("");
    try {
      const res = await api.post(`/campanhas/cupons/${code}/resgatar`, {
        venda_total: vendaAtual.total,
        customer_id: vendaAtual.cliente?.id || null,
      });
      const dados = res.data;
      setCupomAplicado(dados);
      setCodigoCupom("");
      aplicarDescontoTotal("valor", dados.discount_applied);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erro ao validar cupom";
      setErroCupom(msg);
    } finally {
      setLoadingCupom(false);
    }
  };

  const removerCupom = () => {
    setCupomAplicado(null);
    setCodigoCupom("");
    setErroCupom("");
    removerDescontoTotal();
  };

  const handleCodigoCupomChange = (valor) => {
    setCodigoCupom(String(valor || "").toUpperCase());
    setErroCupom("");
  };

  const handleCodigoCupomKeyDown = (e) => {
    if (e.key === "Enter") {
      void aplicarCupom();
    }
  };

  return {
    mostrarModalDescontoItem,
    setMostrarModalDescontoItem,
    itemEditando,
    setItemEditando,
    mostrarModalDescontoTotal,
    setMostrarModalDescontoTotal,
    tipoDescontoTotal,
    setTipoDescontoTotal,
    valorDescontoTotal,
    setValorDescontoTotal,
    codigoCupom,
    cupomAplicado,
    loadingCupom,
    erroCupom,
    recalcularTotais,
    abrirModalDescontoItem,
    salvarDescontoItem,
    removerItemEditando,
    abrirModalDescontoTotal,
    aplicarDescontoTotal,
    removerDescontoTotal,
    aplicarCupom,
    removerCupom,
    handleCodigoCupomChange,
    handleCodigoCupomKeyDown,
  };
}
