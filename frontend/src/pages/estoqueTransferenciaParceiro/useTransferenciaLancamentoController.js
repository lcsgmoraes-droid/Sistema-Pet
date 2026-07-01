import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { buscarClientes } from "../../api/clientes";
import { getProdutos } from "../../api/produtos";
import {
  calcularTotalDiferencaLancadaTransferencia,
  criarFormTransferencia,
  criarItemTransferencia,
  criarItensEdicaoTransferencia,
  extrairListaProdutos,
  extrairObservacaoManualTransferencia,
  incrementarItemTransferencia,
  montarPayloadTransferencia,
  normalizarNumero,
  produtoConfereCodigo,
} from "./transferenciaParceiroUtils";

export default function useTransferenciaLancamentoController({ setAbaAtiva } = {}) {
  const parceiroRef = useRef(null);
  const produtoRef = useRef(null);
  const produtoInputRef = useRef(null);
  const itensRef = useRef(null);

  const [form, setForm] = useState(() => criarFormTransferencia());
  const [parceiroSelecionado, setParceiroSelecionado] = useState(null);
  const [buscaParceiro, setBuscaParceiro] = useState("");
  const [sugestoesParceiros, setSugestoesParceiros] = useState([]);
  const [dropdownParceiroAberto, setDropdownParceiroAberto] = useState(false);
  const [loadingParceiros, setLoadingParceiros] = useState(false);

  const [buscaProduto, setBuscaProduto] = useState("");
  const [sugestoesProdutos, setSugestoesProdutos] = useState([]);
  const [dropdownProdutoAberto, setDropdownProdutoAberto] = useState(false);
  const [loadingProdutos, setLoadingProdutos] = useState(false);

  const [itens, setItens] = useState([]);
  const [salvando, setSalvando] = useState(false);
  const [transferenciaEditando, setTransferenciaEditando] = useState(null);

  useEffect(() => {
    const termo = buscaParceiro.trim();
    if (parceiroSelecionado || termo.length < 2) {
      setSugestoesParceiros([]);
      setLoadingParceiros(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        setLoadingParceiros(true);
        const clientes = await buscarClientes({ search: termo, limit: 8, ativo: true });
        setSugestoesParceiros(clientes);
      } catch (error) {
        console.error("Erro ao buscar pessoas:", error);
        setSugestoesParceiros([]);
      } finally {
        setLoadingParceiros(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [buscaParceiro, parceiroSelecionado]);

  useEffect(() => {
    const termo = buscaProduto.trim();
    if (termo.length < 2) {
      setSugestoesProdutos([]);
      setLoadingProdutos(false);
      return undefined;
    }

    const timer = setTimeout(async () => {
      try {
        setLoadingProdutos(true);
        const response = await getProdutos({
          busca: termo,
          page: 1,
          page_size: 8,
          include_variations: true,
          busca_completa: false,
          incluir_imagens: false,
          incluir_lotes: false,
          incluir_detalhes_composto: false,
        });
        setSugestoesProdutos(
          extrairListaProdutos(response?.data).filter(
            (produto) => !produto?.is_parent && produto?.tipo_produto !== "PAI",
          ),
        );
      } catch (error) {
        console.error("Erro ao buscar produtos:", error);
        setSugestoesProdutos([]);
      } finally {
        setLoadingProdutos(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [buscaProduto]);

  useEffect(() => {
    const handleClickFora = (event) => {
      if (!parceiroRef.current?.contains(event.target)) {
        setDropdownParceiroAberto(false);
      }
      if (!produtoRef.current?.contains(event.target)) {
        setDropdownProdutoAberto(false);
      }
    };

    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const totalQuantidade = useMemo(
    () => itens.reduce((acumulado, item) => acumulado + Number(item.quantidade || 0), 0),
    [itens],
  );

  const totalRessarcimento = useMemo(
    () => itens.reduce((acumulado, item) => acumulado + Number(item.total_item || 0), 0),
    [itens],
  );

  const totalDiferencaLancada = useMemo(
    () => calcularTotalDiferencaLancadaTransferencia(itens),
    [itens],
  );

  const itensSemValor = useMemo(
    () => itens.filter((item) => Number(item.total_item || 0) <= 0).length,
    [itens],
  );

  const selecionarParceiro = (parceiro) => {
    setParceiroSelecionado(parceiro);
    setForm((prev) => ({ ...prev, parceiro_id: String(parceiro.id) }));
    setBuscaParceiro("");
    setSugestoesParceiros([]);
    setDropdownParceiroAberto(false);
  };

  const limparParceiro = () => {
    setParceiroSelecionado(null);
    setBuscaParceiro("");
    setSugestoesParceiros([]);
    setDropdownParceiroAberto(false);
    setForm((prev) => ({ ...prev, parceiro_id: "" }));
  };

  const adicionarProduto = (produto, options = {}) => {
    setItens((prev) => {
      const indiceExistente = prev.findIndex((item) => item.produto_id === produto.id);
      if (indiceExistente >= 0) {
        return prev.map((item, index) =>
          index === indiceExistente ? incrementarItemTransferencia(item, produto) : item,
        );
      }
      return [...prev, criarItemTransferencia(produto)];
    });

    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
    setAbaAtiva?.("lancamento");
    window.setTimeout(() => {
      if (options.scroll !== false) {
        itensRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      produtoInputRef.current?.focus();
    }, 80);
  };

  const adicionarProdutoPorBuscaAtual = async () => {
    const termo = buscaProduto.trim();
    if (termo.length < 2) return;

    const local = sugestoesProdutos.find((produto) => produtoConfereCodigo(produto, termo));
    if (local) {
      adicionarProduto(local, { scroll: false });
      return;
    }

    try {
      setLoadingProdutos(true);
      const response = await getProdutos({
        busca: termo,
        page: 1,
        page_size: 12,
        include_variations: true,
        busca_completa: false,
        incluir_imagens: false,
        incluir_lotes: false,
        incluir_detalhes_composto: false,
      });
      const produtos = extrairListaProdutos(response?.data).filter(
        (produto) => !produto?.is_parent && produto?.tipo_produto !== "PAI",
      );
      const encontrado =
        produtos.find((produto) => produtoConfereCodigo(produto, termo)) ||
        (produtos.length === 1 ? produtos[0] : null);
      if (encontrado) {
        adicionarProduto(encontrado, { scroll: false });
      } else {
        setSugestoesProdutos(produtos);
        setDropdownProdutoAberto(true);
      }
    } catch (error) {
      console.error("Erro ao buscar produto pelo leitor:", error);
      toast.error("Nao foi possivel localizar o produto.");
    } finally {
      setLoadingProdutos(false);
    }
  };

  const atualizarQuantidade = (uid, valor) => {
    if (valor === "") {
      setItens((prev) =>
        prev.map((item) => (item.uid === uid ? { ...item, quantidade: "", total_item: 0 } : item)),
      );
      return;
    }

    const quantidade = normalizarNumero(valor);
    if (!Number.isFinite(quantidade) || quantidade < 0) return;
    setItens((prev) =>
      prev.map((item) =>
        item.uid === uid
          ? { ...item, quantidade, total_item: quantidade * Number(item.custo_unitario || 0) }
          : item,
      ),
    );
  };

  const atualizarCustoUnitario = (uid, valor) => {
    if (valor === "") {
      setItens((prev) =>
        prev.map((item) =>
          item.uid === uid ? { ...item, custo_unitario: "", total_item: 0 } : item,
        ),
      );
      return;
    }

    const custoUnitario = normalizarNumero(valor);
    if (!Number.isFinite(custoUnitario) || custoUnitario < 0) return;
    setItens((prev) =>
      prev.map((item) =>
        item.uid === uid
          ? {
              ...item,
              custo_unitario: custoUnitario,
              total_item: Number(item.quantidade || 0) * custoUnitario,
            }
          : item,
      ),
    );
  };

  const atualizarTotalItem = (uid, valor) => {
    if (valor === "") {
      setItens((prev) =>
        prev.map((item) => (item.uid === uid ? { ...item, total_item: "" } : item)),
      );
      return;
    }

    const totalItem = normalizarNumero(valor);
    if (!Number.isFinite(totalItem) || totalItem < 0) return;
    setItens((prev) =>
      prev.map((item) => {
        if (item.uid !== uid) return item;
        const quantidade = Number(item.quantidade || 0);
        return {
          ...item,
          total_item: totalItem,
          custo_unitario:
            quantidade > 0 ? totalItem / quantidade : Number(item.custo_unitario || 0),
        };
      }),
    );
  };

  const limparLancamentoAtual = () => {
    setTransferenciaEditando(null);
    setItens([]);
    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
    setForm((prev) => ({ ...prev, documento: "", observacao: "" }));
  };

  const iniciarEdicaoTransferencia = (registro) => {
    if (!registro?.conta_receber_id) return;
    if (Number(registro.valor_recebido || 0) > 0 || registro.status === "recebido") {
      toast.error("Transferencia com baixa registrada nao pode ser editada.");
      return;
    }
    if (registro.status === "cancelado") {
      toast.error("Transferencia cancelada nao pode ser editada.");
      return;
    }

    const parceiro = {
      id: registro.parceiro_id,
      nome: registro.parceiro_nome,
      codigo: registro.parceiro_codigo,
      email: registro.parceiro_email,
      tipo_cadastro: "pessoa",
    };

    setTransferenciaEditando(registro);
    setParceiroSelecionado(parceiro);
    setBuscaParceiro("");
    setSugestoesParceiros([]);
    setDropdownParceiroAberto(false);
    setForm(
      criarFormTransferencia({
        parceiro_id: registro.parceiro_id ? String(registro.parceiro_id) : "",
        data_vencimento: registro.data_vencimento || criarFormTransferencia().data_vencimento,
        documento: registro.documento || "",
        observacao: extrairObservacaoManualTransferencia(registro.observacoes),
      }),
    );
    setItens(criarItensEdicaoTransferencia(registro));
    setBuscaProduto("");
    setSugestoesProdutos([]);
    setDropdownProdutoAberto(false);
    window.setTimeout(() => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      produtoInputRef.current?.focus();
    }, 80);
  };

  const cancelarEdicaoTransferencia = () => {
    limparLancamentoAtual();
    toast("Edicao cancelada. O lancamento original continua sem alteracoes.");
  };

  const registrarTransferencia = async (onTransferenciaSalva) => {
    if (!parceiroSelecionado?.id) {
      toast.error("Selecione uma pessoa para registrar a transferencia.");
      return;
    }
    if (itens.length === 0) {
      toast.error("Adicione ao menos um produto na transferencia.");
      return;
    }
    if (itens.some((item) => Number(item.quantidade || 0) <= 0)) {
      toast.error("Informe uma quantidade maior que zero para todos os itens.");
      return;
    }
    if (itensSemValor > 0) {
      toast.error("Existem itens com valor total zerado. Ajuste os valores antes de transferir.");
      return;
    }

    try {
      setSalvando(true);
      const payload = montarPayloadTransferencia(parceiroSelecionado.id, form, itens);
      const response = transferenciaEditando?.conta_receber_id
        ? await api.put(
            `/estoque/transferencia-parceiro/${transferenciaEditando.conta_receber_id}`,
            payload,
          )
        : await api.post("/estoque/transferencia-parceiro", payload);
      const documentoGerado = response?.data?.documento || "registrada";
      toast.success(
        transferenciaEditando?.conta_receber_id
          ? `Transferencia ${documentoGerado} atualizada com sucesso.`
          : `Transferencia ${documentoGerado} registrada com sucesso.`,
      );

      limparLancamentoAtual();
      await onTransferenciaSalva?.();
    } catch (error) {
      console.error("Erro ao registrar transferencia:", error);
      toast.error(error?.response?.data?.detail || "Nao foi possivel registrar a transferencia.");
    } finally {
      setSalvando(false);
    }
  };

  return {
    parceiroRef,
    produtoRef,
    produtoInputRef,
    itensRef,
    form,
    parceiroSelecionado,
    buscaParceiro,
    setBuscaParceiro,
    sugestoesParceiros,
    dropdownParceiroAberto,
    setDropdownParceiroAberto,
    loadingParceiros,
    buscaProduto,
    setBuscaProduto,
    sugestoesProdutos,
    dropdownProdutoAberto,
    setDropdownProdutoAberto,
    loadingProdutos,
    itens,
    salvando,
    transferenciaEditando,
    totalQuantidade,
    totalRessarcimento,
    totalDiferencaLancada,
    itensSemValor,
    selecionarParceiro,
    limparParceiro,
    adicionarProduto,
    adicionarProdutoPorBuscaAtual,
    atualizarQuantidade,
    atualizarCustoUnitario,
    atualizarTotalItem,
    removerItem: (uid) => setItens((prev) => prev.filter((item) => item.uid !== uid)),
    atualizarCampo: (campo, valor) => setForm((prev) => ({ ...prev, [campo]: valor })),
    limparLancamentoAtual,
    iniciarEdicaoTransferencia,
    cancelarEdicaoTransferencia,
    registrarTransferencia,
  };
}
