import { Ionicons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { CameraView, useCameraPermissions } from "expo-camera";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  Vibration,
  View,
} from "react-native";
import {
  buscarClientesPdv,
  buscarProdutoPdvPorBarcode,
  buscarProdutosPdv,
  finalizarVendaPdv,
  listarFormasPagamentoPdv,
  obterCaixaAbertoPdv,
  previewBeneficiosPdv,
  salvarVendaPdv,
} from "../../services/funcionarioPdv.service";
import KeyboardSafeScrollView from "../../components/KeyboardSafeScrollView";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import {
  FuncionarioPdvCaixa,
  FuncionarioPdvBeneficiosPreview,
  FuncionarioPdvCliente,
  FuncionarioPdvFormaPagamento,
  FuncionarioPdvFormaPagamentoOpcao,
  FuncionarioPdvProduto,
} from "../../types";
import { formatarMoeda } from "../../utils/format";

type ItemCarrinhoPdv = {
  produto: FuncionarioPdvProduto;
  quantidade: number;
};

const QUANTIDADE_MINIMA_PDV = 0.001;

const FORMAS_PAGAMENTO: { key: FuncionarioPdvFormaPagamento; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "dinheiro", label: "Dinheiro", icon: "cash-outline" },
  { key: "pix", label: "Pix", icon: "qr-code-outline" },
  { key: "credito", label: "Credito", icon: "card-outline" },
  { key: "debito", label: "Debito", icon: "card-outline" },
];

function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}

function parseNumero(valor: string): number | null {
  let texto = String(valor ?? "").trim().replace(/\s/g, "");
  if (!texto) return null;
  if (texto.includes(",") && texto.includes(".")) {
    texto =
      texto.lastIndexOf(",") > texto.lastIndexOf(".")
        ? texto.replace(/\./g, "").replace(",", ".")
        : texto.replace(/,/g, "");
  } else if (texto.includes(",")) {
    texto = texto.replace(",", ".");
  }
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

function arredondarQuantidadePdv(valor: number) {
  return Math.round(Math.max(QUANTIDADE_MINIMA_PDV, valor) * 1000) / 1000;
}

function formatarQuantidade(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor ?? 0));
}

function formatarQuantidadeCampo(valor: number | null | undefined) {
  return formatarQuantidade(valor).replace(/\./g, "");
}

function formatarValorCampo(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: false,
  }).format(Number(valor ?? 0));
}

function ProdutoImagem({ uri, compacta = false }: { uri?: string | null; compacta?: boolean }) {
  return (
    <View style={[styles.produtoImagemWrap, compacta && styles.produtoImagemWrapCompacta]}>
      {uri ? (
        <Image source={{ uri }} style={styles.produtoImagem} resizeMode="cover" />
      ) : (
        <Ionicons name="image-outline" size={compacta ? 18 : 22} color={CORES.textoClaro} />
      )}
    </View>
  );
}

export default function FuncionarioPdvScreen() {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [scannerAberto, setScannerAberto] = useState(false);
  const [scanAtivo, setScanAtivo] = useState(true);
  const [buscandoProduto, setBuscandoProduto] = useState(false);
  const [buscaManual, setBuscaManual] = useState("");
  const [sugestoes, setSugestoes] = useState<FuncionarioPdvProduto[]>([]);
  const [carrinho, setCarrinho] = useState<ItemCarrinhoPdv[]>([]);
  const [quantidadeEditando, setQuantidadeEditando] = useState<Record<number, string>>({});
  const [valorEditando, setValorEditando] = useState<Record<number, string>>({});
  const [clienteBusca, setClienteBusca] = useState("");
  const [clientesSugestoes, setClientesSugestoes] = useState<FuncionarioPdvCliente[]>([]);
  const [cliente, setCliente] = useState<FuncionarioPdvCliente | null>(null);
  const [mostrarDetalhesCliente, setMostrarDetalhesCliente] = useState(false);
  const [formaPagamento, setFormaPagamento] = useState<FuncionarioPdvFormaPagamento>("dinheiro");
  const [formasPagamentoErp, setFormasPagamentoErp] = useState<FuncionarioPdvFormaPagamentoOpcao[]>([]);
  const [formaPagamentoIdSelecionada, setFormaPagamentoIdSelecionada] = useState<number | null>(null);
  const [numeroParcelas, setNumeroParcelas] = useState(1);
  const [nsuCartao, setNsuCartao] = useState("");
  const [valorRecebido, setValorRecebido] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [caixa, setCaixa] = useState<FuncionarioPdvCaixa | null>(null);
  const [carregandoCaixa, setCarregandoCaixa] = useState(false);
  const [finalizando, setFinalizando] = useState(false);
  const [salvandoAberta, setSalvandoAberta] = useState(false);
  const [beneficiosPreview, setBeneficiosPreview] = useState<FuncionarioPdvBeneficiosPreview | null>(null);
  const [carregandoBeneficios, setCarregandoBeneficios] = useState(false);
  const [erroBeneficios, setErroBeneficios] = useState<string | null>(null);
  const [cupomCodigo, setCupomCodigo] = useState("");
  const [usarCashback, setUsarCashback] = useState(false);
  const [cashbackValor, setCashbackValor] = useState("");
  const ultimoScan = useRef("");
  const previewSequencia = useRef(0);

  useEffect(() => {
    if (scannerAberto && !permission?.granted) {
      requestPermission();
    }
  }, [scannerAberto, permission?.granted, requestPermission]);

  useEffect(() => {
    if (!isFocused) return;
    carregarCaixa();
    carregarFormasPagamento();
  }, [isFocused]);

  useEffect(() => {
    if (!isFocused) return;
    const termo = buscaManual.trim();
    if (termo.length < 2) {
      setSugestoes([]);
      return;
    }

    const autocompleteProdutosTimer = setTimeout(() => {
      buscarManualProduto(false);
    }, 350);

    return () => clearTimeout(autocompleteProdutosTimer);
  }, [buscaManual, isFocused]);

  useEffect(() => {
    if (!isFocused || cliente) return;
    const termo = clienteBusca.trim();
    if (termo.length < 2) {
      setClientesSugestoes([]);
      return;
    }

    const autocompleteClientesTimer = setTimeout(() => {
      buscarCliente(false);
    }, 350);

    return () => clearTimeout(autocompleteClientesTimer);
  }, [clienteBusca, cliente, isFocused]);

  const total = useMemo(
    () =>
      carrinho.reduce(
        (soma, item) => soma + item.quantidade * Number(item.produto.preco_venda ?? 0),
        0,
      ),
    [carrinho],
  );
  const itensPayload = useMemo(
    () =>
      carrinho.map((item) => ({
        produto_id: item.produto.id,
        quantidade: item.quantidade,
        preco_unitario: Number(item.produto.preco_venda ?? 0),
      })),
    [carrinho],
  );
  const itensPreviewKey = useMemo(() => JSON.stringify(itensPayload), [itensPayload]);
  const cashbackSolicitado = useMemo(
    () => (usarCashback ? parseNumero(cashbackValor) ?? 0 : 0),
    [cashbackValor, usarCashback],
  );
  const totalComBeneficios = beneficiosPreview?.total_venda ?? total;
  const valorAPagar = beneficiosPreview?.valor_pagamento ?? totalComBeneficios;
  const valorRecebidoNumero = useMemo(() => parseNumero(valorRecebido) ?? 0, [valorRecebido]);
  const troco = formaPagamento === "dinheiro" ? Math.max(0, valorRecebidoNumero - valorAPagar) : 0;
  const totalItens = useMemo(
    () => carrinho.reduce((soma, item) => soma + item.quantidade, 0),
    [carrinho],
  );
  const ehCartao = formaPagamento === "credito" || formaPagamento === "debito";
  const opcoesCartao = useMemo(
    () => formasPagamentoErp.filter((item) => item.key === formaPagamento),
    [formasPagamentoErp, formaPagamento],
  );
  const formaPagamentoSelecionada = useMemo(
    () => opcoesCartao.find((item) => item.id === formaPagamentoIdSelecionada) ?? null,
    [opcoesCartao, formaPagamentoIdSelecionada],
  );
  const parcelasCredito = useMemo(() => {
    const formaParcelamento = formaPagamentoSelecionada;
    const podeParcelar =
      formaPagamento === "credito" &&
      Boolean(formaParcelamento?.permite_parcelamento || formaParcelamento?.split_parcelas);
    const maximo = Math.max(
      1,
      Number(
        podeParcelar
          ? formaParcelamento?.parcelas_maximas ?? formaParcelamento?.max_parcelas ?? formaParcelamento?.numero_parcelas ?? 1
          : 1,
      ),
    );
    return Array.from({ length: maximo }, (_, indice) => indice + 1);
  }, [formaPagamento, formaPagamentoSelecionada]);

  useEffect(() => {
    if (!ehCartao) {
      setFormaPagamentoIdSelecionada(null);
      setNsuCartao("");
      setNumeroParcelas(1);
      return;
    }
    if (formaPagamentoIdSelecionada && !opcoesCartao.some((item) => item.id === formaPagamentoIdSelecionada)) {
      setFormaPagamentoIdSelecionada(null);
    }
    if (formaPagamento !== "credito") {
      setNumeroParcelas(1);
      return;
    }
    if (!parcelasCredito.includes(numeroParcelas)) {
      setNumeroParcelas(parcelasCredito[0] ?? 1);
    }
  }, [ehCartao, formaPagamento, formaPagamentoIdSelecionada, numeroParcelas, opcoesCartao, parcelasCredito]);

  useEffect(() => {
    if (!isFocused || carrinho.length === 0) {
      setBeneficiosPreview(null);
      setErroBeneficios(null);
      return;
    }

    const timer = setTimeout(() => {
      carregarBeneficios();
    }, 450);

    return () => clearTimeout(timer);
  }, [isFocused, itensPreviewKey, cliente?.id, cupomCodigo, usarCashback, cashbackValor]);

  async function carregarCaixa() {
    setCarregandoCaixa(true);
    try {
      setCaixa(await obterCaixaAbertoPdv());
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel consultar o caixa."));
    } finally {
      setCarregandoCaixa(false);
    }
  }

  async function carregarFormasPagamento() {
    try {
      setFormasPagamentoErp(await listarFormasPagamentoPdv());
    } catch {
      setFormasPagamentoErp([]);
    }
  }

  async function carregarBeneficios() {
    if (!itensPayload.length) {
      setBeneficiosPreview(null);
      setErroBeneficios(null);
      return;
    }

    const sequenciaAtual = previewSequencia.current + 1;
    previewSequencia.current = sequenciaAtual;
    setCarregandoBeneficios(true);
    setErroBeneficios(null);
    try {
      const preview = await previewBeneficiosPdv({
        cliente_id: cliente?.id ?? null,
        itens: itensPayload,
        cupom_codigo: cupomCodigo.trim() || null,
        cashback_valor: cashbackSolicitado,
      });
      if (previewSequencia.current === sequenciaAtual) {
        setBeneficiosPreview(preview);
      }
    } catch (error: any) {
      if (previewSequencia.current === sequenciaAtual) {
        setBeneficiosPreview(null);
        setErroBeneficios(mensagemErroApi(error, "Nao foi possivel calcular os beneficios."));
      }
    } finally {
      if (previewSequencia.current === sequenciaAtual) {
        setCarregandoBeneficios(false);
      }
    }
  }

  function adicionarProduto(produto: FuncionarioPdvProduto) {
    if (!produto.vendavel) {
      Alert.alert("Produto nao vendavel", produto.aviso || "Este produto nao pode ser vendido no PDV.");
      return;
    }
    setQuantidadeEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[produto.id];
      return proximo;
    });
    setValorEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[produto.id];
      return proximo;
    });
    setCarrinho((atual) => {
      const existente = atual.find((item) => item.produto.id === produto.id);
      if (existente) {
        return atual.map((item) =>
          item.produto.id === produto.id ? { ...item, quantidade: item.quantidade + 1 } : item,
        );
      }
      return [...atual, { produto, quantidade: 1 }];
    });
    setSugestoes([]);
    setBuscaManual("");
  }

  function limparEdicaoItem(produtoId: number) {
    setQuantidadeEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[produtoId];
      return proximo;
    });
    setValorEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[produtoId];
      return proximo;
    });
  }

  function aplicarQuantidade(produtoId: number, quantidade: number) {
    if (!Number.isFinite(quantidade) || quantidade <= 0) return;
    setCarrinho((atual) =>
      atual.map((item) =>
        item.produto.id === produtoId ? { ...item, quantidade: arredondarQuantidadePdv(quantidade) } : item,
      ),
    );
  }

  function removerProduto(produtoId: number) {
    setCarrinho((atual) => atual.filter((item) => item.produto.id !== produtoId));
    limparEdicaoItem(produtoId);
  }

  function alterarQuantidade(produtoId: number, quantidade: number) {
    if (!Number.isFinite(quantidade) || quantidade <= 0) {
      removerProduto(produtoId);
      return;
    }
    limparEdicaoItem(produtoId);
    aplicarQuantidade(produtoId, quantidade);
  }

  function editarQuantidadeItem(produtoId: number, texto: string) {
    setQuantidadeEditando((atual) => ({ ...atual, [produtoId]: texto }));
    setValorEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[produtoId];
      return proximo;
    });
    const quantidade = parseNumero(texto);
    if (quantidade !== null && quantidade > 0) {
      aplicarQuantidade(produtoId, quantidade);
    }
  }

  function finalizarEdicaoQuantidade(produtoId: number) {
    const texto = quantidadeEditando[produtoId];
    const quantidade = parseNumero(texto ?? "");
    if (quantidade !== null && quantidade > 0) {
      aplicarQuantidade(produtoId, quantidade);
    }
    setQuantidadeEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[produtoId];
      return proximo;
    });
  }

  function editarValorItem(item: ItemCarrinhoPdv, texto: string) {
    setValorEditando((atual) => ({ ...atual, [item.produto.id]: texto }));
    setQuantidadeEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[item.produto.id];
      return proximo;
    });
    const valor = parseNumero(texto);
    const precoUnitario = Number(item.produto.preco_venda ?? 0);
    if (valor !== null && valor > 0 && precoUnitario > 0) {
      aplicarQuantidade(item.produto.id, valor / precoUnitario);
    }
  }

  function finalizarEdicaoValor(item: ItemCarrinhoPdv) {
    const texto = valorEditando[item.produto.id];
    const valor = parseNumero(texto ?? "");
    const precoUnitario = Number(item.produto.preco_venda ?? 0);
    if (valor !== null && valor > 0 && precoUnitario > 0) {
      aplicarQuantidade(item.produto.id, valor / precoUnitario);
    }
    setValorEditando((atual) => {
      const proximo = { ...atual };
      delete proximo[item.produto.id];
      return proximo;
    });
  }

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscandoProduto || data === ultimoScan.current) return;
    ultimoScan.current = data;
    setScanAtivo(false);
    setBuscandoProduto(true);
    Vibration.vibrate(80);

    try {
      const produto = await buscarProdutoPdvPorBarcode(data);
      if (!produto) {
        Alert.alert("Nao encontrado", `Codigo ${data} nao encontrado no ERP.`, [
          {
            text: "Escanear outro",
            onPress: () => {
              ultimoScan.current = "";
              setScanAtivo(true);
            },
          },
        ]);
        return;
      }
      adicionarProduto(produto);
      setScannerAberto(false);
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar o produto."));
    } finally {
      setBuscandoProduto(false);
    }
  }

  async function buscarManualProduto(mostrarAlerta = true) {
    const termo = buscaManual.trim();
    if (termo.length < 2) return;
    setBuscandoProduto(true);
    try {
      setSugestoes(await buscarProdutosPdv(termo));
    } catch (error: any) {
      if (mostrarAlerta) {
        Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar produtos."));
      }
    } finally {
      setBuscandoProduto(false);
    }
  }

  async function buscarCliente(mostrarAlerta = true) {
    const termo = clienteBusca.trim();
    if (termo.length < 2) return;
    try {
      setClientesSugestoes(await buscarClientesPdv(termo));
    } catch (error: any) {
      if (mostrarAlerta) {
        Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar clientes."));
      }
    }
  }

  function limparVendaAtual() {
    setCarrinho([]);
    setQuantidadeEditando({});
    setValorEditando({});
    setCliente(null);
    setMostrarDetalhesCliente(false);
    setClienteBusca("");
    setClientesSugestoes([]);
    setValorRecebido("");
    setObservacoes("");
    setCupomCodigo("");
    setUsarCashback(false);
    setCashbackValor("");
    setBeneficiosPreview(null);
    setFormaPagamentoIdSelecionada(null);
    setNumeroParcelas(1);
    setNsuCartao("");
  }

  async function salvarAberta() {
    if (!caixa?.aberto) {
      Alert.alert("Caixa fechado", caixa?.mensagem || "Abra um caixa no ERP web antes de salvar pelo app.");
      return;
    }
    if (!carrinho.length) {
      Alert.alert("Carrinho vazio", "Adicione ao menos um produto para salvar.");
      return;
    }
    setSalvandoAberta(true);
    try {
      const previewAtual = await previewBeneficiosPdv({
        cliente_id: cliente?.id ?? null,
        itens: itensPayload,
        cupom_codigo: cupomCodigo.trim() || null,
        cashback_valor: 0,
      });
      setBeneficiosPreview(previewAtual);
      setErroBeneficios(null);

      const resposta = await salvarVendaPdv({
        cliente_id: cliente?.id ?? null,
        itens: itensPayload,
        observacoes: observacoes.trim() || null,
        cupom_codigo: cupomCodigo.trim() || null,
        desconto_cupom: previewAtual.desconto_cupom,
        cashback_valor: 0,
      });
      Alert.alert("Venda salva", `${resposta.numero_venda} ficou aberta para recebimento no caixa.`);
      limparVendaAtual();
      carregarCaixa();
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel salvar a venda."));
    } finally {
      setSalvandoAberta(false);
    }
  }

  async function finalizar() {
    if (!caixa?.aberto) {
      Alert.alert("Caixa fechado", caixa?.mensagem || "Abra um caixa no ERP web antes de vender pelo app.");
      return;
    }
    if (!carrinho.length) {
      Alert.alert("Carrinho vazio", "Adicione ao menos um produto para finalizar.");
      return;
    }
    setFinalizando(true);
    try {
      const previewAtual = await previewBeneficiosPdv({
        cliente_id: cliente?.id ?? null,
        itens: itensPayload,
        cupom_codigo: cupomCodigo.trim() || null,
        cashback_valor: cashbackSolicitado,
      });
      setBeneficiosPreview(previewAtual);
      setErroBeneficios(null);

      if (previewAtual.total_venda <= 0) {
        Alert.alert("Total invalido", "O total da venda precisa ser maior que zero.");
        return;
      }

      if (formaPagamento === "dinheiro" && previewAtual.valor_pagamento > 0 && valorRecebidoNumero + 0.01 < previewAtual.valor_pagamento) {
        Alert.alert("Valor recebido", "Informe um valor recebido igual ou maior que o total.");
        return;
      }
      if (ehCartao && !formaPagamentoSelecionada) {
        Alert.alert("Cartao", "Selecione a bandeira/operadora do cartao.");
        return;
      }
      const trocoFinal = formaPagamento === "dinheiro" ? Math.max(0, valorRecebidoNumero - previewAtual.valor_pagamento) : 0;
      const resposta = await finalizarVendaPdv({
        cliente_id: cliente?.id ?? null,
        itens: itensPayload,
        pagamento: {
          forma_pagamento: formaPagamento,
          valor: Number(previewAtual.valor_pagamento.toFixed(2)),
          valor_recebido: formaPagamento === "dinheiro" && previewAtual.valor_pagamento > 0 ? Number(valorRecebidoNumero.toFixed(2)) : null,
          troco: formaPagamento === "dinheiro" && previewAtual.valor_pagamento > 0 ? Number(trocoFinal.toFixed(2)) : null,
          numero_parcelas: formaPagamento === "credito" ? numeroParcelas : 1,
          forma_pagamento_id: ehCartao ? formaPagamentoSelecionada?.id ?? null : null,
          bandeira: ehCartao ? formaPagamentoSelecionada?.bandeira ?? formaPagamentoSelecionada?.nome ?? null : null,
          operadora: ehCartao ? formaPagamentoSelecionada?.operadora ?? null : null,
          nsu_cartao: ehCartao ? nsuCartao.trim() || null : null,
        },
        observacoes: observacoes.trim() || null,
        cupom_codigo: cupomCodigo.trim() || null,
        desconto_cupom: previewAtual.desconto_cupom,
        cashback_valor: previewAtual.cashback_valor,
      });
      Alert.alert("Venda registrada", `${resposta.numero_venda} - ${formatarMoeda(resposta.total)}`);
      limparVendaAtual();
      carregarCaixa();
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel finalizar a venda."));
    } finally {
      setFinalizando(false);
    }
  }

  if (scannerAberto && permission && !permission.granted) {
    return (
      <View style={styles.centrado}>
        <Ionicons name="camera-outline" size={42} color={CORES.primario} />
        <Text style={styles.tituloPermissao}>Permitir camera</Text>
        <TouchableOpacity style={styles.botaoPrimario} onPress={requestPermission}>
          <Text style={styles.botaoPrimarioTexto}>Permitir</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (scannerAberto && isFocused) {
    return (
      <View style={styles.scannerContainer}>
        <CameraView
          style={styles.camera}
          facing="back"
          onBarcodeScanned={scanAtivo ? onBarcodeScanned : undefined}
          barcodeScannerSettings={{
            barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e", "code128", "code39", "qr"],
          }}
        >
          <View style={styles.scannerOverlay}>
            <TouchableOpacity style={styles.fecharScanner} onPress={() => setScannerAberto(false)}>
              <Ionicons name="close" size={28} color="#fff" />
            </TouchableOpacity>
            <View style={styles.frameScan} />
            <Text style={styles.scannerTexto}>
              {buscandoProduto ? "Buscando no ERP..." : "Aponte para o codigo de barras"}
            </Text>
            {!scanAtivo ? (
              <TouchableOpacity
                style={styles.botaoScanner}
                onPress={() => {
                  ultimoScan.current = "";
                  setScanAtivo(true);
                }}
              >
                <Ionicons name="scan-outline" size={18} color="#fff" />
                <Text style={styles.botaoScannerTexto}>Escanear novamente</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        </CameraView>
      </View>
    );
  }

  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.conteudo}>
        <View style={styles.headerCard}>
          <View style={styles.headerIcone}>
            <Ionicons name="cart-outline" size={24} color={CORES.primario} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.titulo}>PDV rapido</Text>
            <Text style={styles.subtitulo}>Venda simples usando os dados e regras do ERP.</Text>
          </View>
          <TouchableOpacity style={styles.botaoAtualizarCaixa} onPress={carregarCaixa} disabled={carregandoCaixa}>
            {carregandoCaixa ? (
              <ActivityIndicator color={CORES.primario} />
            ) : (
              <Ionicons name="refresh" size={18} color={CORES.primario} />
            )}
          </TouchableOpacity>
        </View>

        <View style={[styles.caixaBox, caixa?.aberto ? styles.caixaAberto : styles.caixaFechado]}>
          <Ionicons
            name={caixa?.aberto ? "checkmark-circle-outline" : "alert-circle-outline"}
            size={20}
            color={caixa?.aberto ? CORES.sucesso : CORES.aviso}
          />
          <Text style={styles.caixaTexto}>
            {caixa?.aberto ? `Caixa #${caixa.numero_caixa ?? caixa.caixa_id} aberto` : caixa?.mensagem || "Consultando caixa..."}
          </Text>
        </View>

        <View style={styles.card}>
          <TouchableOpacity
            style={styles.botaoScan}
            onPress={() => {
              ultimoScan.current = "";
              setScanAtivo(true);
              setScannerAberto(true);
            }}
          >
            <Ionicons name="camera" size={20} color="#fff" />
            <Text style={styles.botaoScanTexto}>Ler codigo de barras</Text>
          </TouchableOpacity>

          <View style={styles.buscaLinha}>
            <TextInput
              value={buscaManual}
              onChangeText={setBuscaManual}
              placeholder="Buscar produto por nome, codigo ou barras"
              style={styles.inputBusca}
              returnKeyType="search"
              onSubmitEditing={() => buscarManualProduto()}
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={() => buscarManualProduto()} disabled={buscandoProduto}>
              {buscandoProduto ? <ActivityIndicator color="#fff" /> : <Ionicons name="search" size={20} color="#fff" />}
            </TouchableOpacity>
          </View>

          {sugestoes.map((produto) => (
            <TouchableOpacity key={produto.id} style={styles.sugestao} onPress={() => adicionarProduto(produto)}>
              <ProdutoImagem uri={produto.imagem_url} />
              <View style={{ flex: 1 }}>
                <Text style={styles.sugestaoNome} numberOfLines={2}>{produto.nome}</Text>
                <Text style={styles.sugestaoMeta}>
                  SKU {produto.codigo || "-"} | Estoque {formatarQuantidade(produto.estoque_atual)} | {formatarMoeda(produto.preco_venda)}
                </Text>
              </View>
              <Ionicons name="add-circle-outline" size={22} color={CORES.sucesso} />
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.card}>
          <View style={styles.linhaTitulo}>
            <Text style={styles.secaoTitulo}>Carrinho</Text>
            <Text style={styles.badge}>{formatarQuantidade(totalItens)} item(ns)</Text>
          </View>
          {carrinho.length === 0 ? (
            <View style={styles.vazio}>
              <Ionicons name="cube-outline" size={34} color={CORES.textoClaro} />
              <Text style={styles.vazioTexto}>Nenhum produto adicionado</Text>
            </View>
          ) : (
            carrinho.map((item) => (
              <View key={item.produto.id} style={styles.itemCarrinho}>
                <ProdutoImagem uri={item.produto.imagem_url} compacta />
                <View style={styles.itemCarrinhoConteudo}>
                  <View style={styles.itemCarrinhoTopo}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.itemNome} numberOfLines={2}>{item.produto.nome}</Text>
                      <Text style={styles.itemMeta}>
                        {formatarMoeda(item.produto.preco_venda)} / {(item.produto.unidade || "un").toLowerCase()}
                      </Text>
                    </View>
                    <Text style={styles.itemSubtotal}>
                      {formatarMoeda(item.quantidade * Number(item.produto.preco_venda ?? 0))}
                    </Text>
                  </View>
                  <View style={styles.itemControles}>
                    <View style={styles.campoCarrinho}>
                      <Text style={styles.campoCarrinhoLabel}>Qtd.</Text>
                      <View style={styles.quantidadeBox}>
                        <TouchableOpacity
                          style={styles.botaoQuantidade}
                          onPress={() => alterarQuantidade(item.produto.id, item.quantidade - 1)}
                        >
                          <Ionicons name="remove" size={16} color={CORES.texto} />
                        </TouchableOpacity>
                        <TextInput
                          value={quantidadeEditando[item.produto.id] ?? formatarQuantidadeCampo(item.quantidade)}
                          onChangeText={(valor) => editarQuantidadeItem(item.produto.id, valor)}
                          onBlur={() => finalizarEdicaoQuantidade(item.produto.id)}
                          keyboardType="decimal-pad"
                          returnKeyType="done"
                          selectTextOnFocus
                          style={styles.inputQuantidade}
                        />
                        <TouchableOpacity
                          style={styles.botaoQuantidade}
                          onPress={() => alterarQuantidade(item.produto.id, item.quantidade + 1)}
                        >
                          <Ionicons name="add" size={16} color={CORES.texto} />
                        </TouchableOpacity>
                      </View>
                    </View>
                    <View style={styles.campoCarrinho}>
                      <Text style={styles.campoCarrinhoLabel}>Valor (R$)</Text>
                      <TextInput
                        value={
                          valorEditando[item.produto.id] ??
                          formatarValorCampo(item.quantidade * Number(item.produto.preco_venda ?? 0))
                        }
                        onChangeText={(valor) => editarValorItem(item, valor)}
                        onBlur={() => finalizarEdicaoValor(item)}
                        keyboardType="decimal-pad"
                        returnKeyType="done"
                        selectTextOnFocus
                        style={styles.inputValorItem}
                      />
                    </View>
                  </View>
                </View>
              </View>
            ))
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.secaoTitulo}>Comprador opcional</Text>
          {cliente ? (
            <>
              <View style={styles.clienteSelecionado}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.clienteNome}>{cliente.nome}</Text>
                  <Text style={styles.clienteMeta}>
                    Codigo {cliente.codigo || "-"} | {cliente.tipo_cadastro || "pessoa"}
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.botaoDetalhesCliente}
                  onPress={() => setMostrarDetalhesCliente((atual) => !atual)}
                >
                  <Ionicons name="information-circle-outline" size={17} color={CORES.primario} />
                  <Text style={styles.botaoDetalhesClienteTexto}>Detalhes</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.botaoLimpar}
                  onPress={() => {
                    setCliente(null);
                    setMostrarDetalhesCliente(false);
                    setUsarCashback(false);
                    setCashbackValor("");
                  }}
                >
                  <Ionicons name="close" size={18} color={CORES.erro} />
                </TouchableOpacity>
              </View>
              {mostrarDetalhesCliente ? (
                <View style={styles.detalhesCliente}>
                  <Text style={styles.detalhesClienteTitulo}>Detalhes do cliente</Text>
                  <Text style={styles.detalhesClienteLinha}>Telefone: {cliente.celular || cliente.telefone || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Documento: {cliente.documento || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Email: {cliente.email || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Endereco: {cliente.endereco || "-"}</Text>
                  <Text style={styles.detalhesClienteLinha}>Credito: {formatarMoeda(cliente.credito ?? 0)}</Text>
                  <Text style={styles.detalhesClienteSubtitulo}>Cartao fidelidade</Text>
                  <Text style={styles.detalhesClienteLinha}>
                    {cliente.fidelidade
                      ? `Pontos ${cliente.fidelidade.pontos ?? 0} | Carimbos ${cliente.fidelidade.carimbos ?? 0}`
                      : "Sem informacao de fidelidade"}
                  </Text>
                  <Text style={styles.detalhesClienteSubtitulo}>Cupons disponiveis</Text>
                  {(cliente.cupons_disponiveis ?? []).length ? (
                    (cliente.cupons_disponiveis ?? []).slice(0, 3).map((cupom: any, indice: number) => (
                      <Text key={`${cupom.code ?? indice}`} style={styles.detalhesClienteLinha}>
                        {cupom.code ?? "Cupom"} {cupom.discount_applied ? `- ${formatarMoeda(cupom.discount_applied)}` : ""}
                      </Text>
                    ))
                  ) : (
                    <Text style={styles.detalhesClienteLinha}>Nenhum cupom nominal carregado.</Text>
                  )}
                </View>
              ) : null}
            </>
          ) : (
            <>
              <View style={styles.buscaLinha}>
                <TextInput
                  value={clienteBusca}
                  onChangeText={setClienteBusca}
                  placeholder="Buscar pessoa por nome ou telefone"
                  style={styles.inputBusca}
                  returnKeyType="search"
                  onSubmitEditing={() => buscarCliente()}
                />
                <TouchableOpacity style={styles.botaoBusca} onPress={() => buscarCliente()}>
                  <Ionicons name="search" size={20} color="#fff" />
                </TouchableOpacity>
              </View>
              {clientesSugestoes.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={styles.sugestao}
                  onPress={() => {
                    setCliente(item);
                    setMostrarDetalhesCliente(false);
                    setClientesSugestoes([]);
                    setClienteBusca("");
                    setUsarCashback(false);
                    setCashbackValor("");
                  }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.sugestaoNome}>{item.nome}</Text>
                    <Text style={styles.sugestaoMeta}>
                      Codigo {item.codigo || "-"} | {item.celular || item.telefone || "-"}
                      {item.tipo_cadastro ? ` | ${item.tipo_cadastro}` : ""}
                    </Text>
                  </View>
                  <Ionicons name="person-add-outline" size={20} color={CORES.primario} />
                </TouchableOpacity>
              ))}
            </>
          )}
        </View>

        <View style={styles.card}>
          <View style={styles.linhaTitulo}>
            <Text style={styles.secaoTitulo}>Beneficios e campanhas</Text>
            {carregandoBeneficios ? <ActivityIndicator color={CORES.primario} /> : null}
          </View>

          <View style={styles.buscaLinha}>
            <TextInput
              value={cupomCodigo}
              onChangeText={setCupomCodigo}
              placeholder="Codigo do cupom"
              autoCapitalize="characters"
              style={styles.inputBusca}
            />
            <TouchableOpacity style={styles.botaoBusca} onPress={carregarBeneficios} disabled={!carrinho.length}>
              <Ionicons name="ticket-outline" size={20} color="#fff" />
            </TouchableOpacity>
          </View>

          {erroBeneficios ? (
            <View style={styles.beneficioErro}>
              <Ionicons name="alert-circle-outline" size={18} color={CORES.erro} />
              <Text style={styles.beneficioErroTexto}>{erroBeneficios}</Text>
            </View>
          ) : null}

          {beneficiosPreview?.cupons_disponiveis?.length ? (
            <View style={styles.cuponsLista}>
              {beneficiosPreview.cupons_disponiveis.slice(0, 3).map((cupom) => (
                <TouchableOpacity
                  key={cupom.code}
                  style={styles.cupomChip}
                  onPress={() => setCupomCodigo(cupom.code)}
                >
                  <Ionicons name="pricetag-outline" size={15} color={CORES.primario} />
                  <Text style={styles.cupomChipTexto}>
                    {cupom.code} - {formatarMoeda(cupom.discount_applied)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : null}

          {beneficiosPreview?.beneficios_gerados?.length ? (
            <View style={styles.beneficiosGeradosBox}>
              <Text style={styles.beneficiosGeradosTitulo}>Beneficios que esta venda vai gerar</Text>
              {beneficiosPreview.beneficios_gerados.slice(0, 4).map((beneficio, indice) => (
                <View key={`${beneficio.tipo}-${indice}`} style={styles.beneficioGeradoLinha}>
                  <Ionicons
                    name={beneficio.tipo === "cashback" ? "wallet-outline" : beneficio.tipo === "fidelidade" ? "star-outline" : "ticket-outline"}
                    size={16}
                    color={CORES.sucesso}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.beneficioGeradoTitulo}>{beneficio.titulo}</Text>
                    <Text style={styles.beneficioGeradoDescricao}>
                      {beneficio.descricao || (beneficio.valor ? formatarMoeda(beneficio.valor) : `${beneficio.quantidade ?? 0}`)}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          ) : null}

          {cliente ? (
            <View style={styles.cashbackBox}>
              <View style={{ flex: 1 }}>
                <Text style={styles.cashbackTitulo}>Cashback disponivel</Text>
                <Text style={styles.cashbackValor}>{formatarMoeda(beneficiosPreview?.cashback_disponivel ?? 0)}</Text>
              </View>
              <TouchableOpacity
                style={[styles.cashbackToggle, usarCashback && styles.cashbackToggleAtivo]}
                onPress={() => {
                  const saldo = beneficiosPreview?.cashback_disponivel ?? 0;
                  const sugerido = Math.min(saldo, totalComBeneficios);
                  setUsarCashback((atual) => !atual);
                  if (!usarCashback && sugerido > 0) {
                    setCashbackValor(String(sugerido.toFixed(2)).replace(".", ","));
                  }
                }}
              >
                <Ionicons
                  name={usarCashback ? "checkmark-circle" : "ellipse-outline"}
                  size={18}
                  color={usarCashback ? "#fff" : CORES.primario}
                />
                <Text style={[styles.cashbackToggleTexto, usarCashback && styles.cashbackToggleTextoAtivo]}>
                  Usar
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.beneficioInfo}>
              <Ionicons name="person-circle-outline" size={18} color={CORES.textoSecundario} />
              <Text style={styles.beneficioInfoTexto}>Selecione um cliente para ver cashback e cupons nominais.</Text>
            </View>
          )}

          {usarCashback ? (
            <>
              <Text style={styles.label}>Valor de cashback</Text>
              <TextInput
                value={cashbackValor}
                onChangeText={setCashbackValor}
                placeholder="Ex: 10,00"
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </>
          ) : null}

          {beneficiosPreview ? (
            <View style={styles.beneficioResumo}>
              <View style={styles.beneficioLinha}>
                <Text style={styles.beneficioResumoLabel}>Subtotal</Text>
                <Text style={styles.beneficioResumoValor}>{formatarMoeda(beneficiosPreview.subtotal)}</Text>
              </View>
              {beneficiosPreview.desconto_cupom > 0 ? (
                <View style={styles.beneficioLinha}>
                  <Text style={styles.beneficioResumoLabel}>Cupom</Text>
                  <Text style={styles.beneficioResumoDesconto}>- {formatarMoeda(beneficiosPreview.desconto_cupom)}</Text>
                </View>
              ) : null}
              {beneficiosPreview.cashback_valor > 0 ? (
                <View style={styles.beneficioLinha}>
                  <Text style={styles.beneficioResumoLabel}>Cashback</Text>
                  <Text style={styles.beneficioResumoDesconto}>- {formatarMoeda(beneficiosPreview.cashback_valor)}</Text>
                </View>
              ) : null}
              <View style={styles.beneficioLinha}>
                <Text style={styles.beneficioResumoTotal}>A pagar</Text>
                <Text style={styles.beneficioResumoTotal}>{formatarMoeda(valorAPagar)}</Text>
              </View>
            </View>
          ) : null}
        </View>

        <View style={styles.card}>
          <Text style={styles.secaoTitulo}>Pagamento</Text>
          <View style={styles.formasGrid}>
            {FORMAS_PAGAMENTO.map((forma) => (
              <TouchableOpacity
                key={forma.key}
                style={[styles.formaBotao, formaPagamento === forma.key && styles.formaBotaoAtivo]}
                onPress={() => {
                  setFormaPagamento(forma.key);
                  setFormaPagamentoIdSelecionada(null);
                  setNumeroParcelas(1);
                  setNsuCartao("");
                }}
              >
                <Ionicons
                  name={forma.icon}
                  size={20}
                  color={formaPagamento === forma.key ? CORES.primario : CORES.textoSecundario}
                />
                <Text style={[styles.formaTexto, formaPagamento === forma.key && styles.formaTextoAtivo]}>
                  {forma.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {formaPagamento === "dinheiro" ? (
            <>
              <Text style={styles.label}>Valor recebido</Text>
              <TextInput
                value={valorRecebido}
                onChangeText={setValorRecebido}
                placeholder="Ex: 100,00"
                keyboardType="decimal-pad"
                style={styles.input}
              />
              <Text style={styles.troco}>Troco: {formatarMoeda(troco)}</Text>
            </>
          ) : null}

          {ehCartao ? (
            <View style={styles.cartaoBox}>
              <Text style={styles.label}>Bandeira/operadora</Text>
              {!formaPagamentoSelecionada ? (
                <Text style={styles.cartaoInstrucao}>Selecione a bandeira/operadora do cartao</Text>
              ) : null}
              {opcoesCartao.length ? (
                <View style={styles.cartaoOpcoesGrid}>
                  {opcoesCartao.map((opcao) => {
                    const ativa = formaPagamentoSelecionada?.id === opcao.id;
                    return (
                      <TouchableOpacity
                        key={opcao.id}
                        style={[styles.cartaoOpcao, ativa && styles.cartaoOpcaoAtiva]}
                        onPress={() => {
                          setFormaPagamentoIdSelecionada(opcao.id);
                          setNumeroParcelas(1);
                        }}
                      >
                        <Text style={[styles.cartaoOpcaoTitulo, ativa && styles.cartaoOpcaoTituloAtivo]}>
                          {opcao.bandeira || opcao.nome}
                        </Text>
                        <Text style={styles.cartaoOpcaoSubtitulo}>
                          {opcao.operadora || opcao.tipo || "Cartao"} {opcao.taxa_percentual ? `- taxa ${opcao.taxa_percentual}%` : ""}
                        </Text>
                        {opcao.requer_nsu ? <Text style={styles.cartaoOpcaoAviso}>NSU recomendado</Text> : null}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ) : (
                <View style={styles.cartaoAviso}>
                  <Ionicons name="alert-circle-outline" size={18} color={CORES.erro} />
                  <Text style={styles.cartaoAvisoTexto}>Nenhuma forma de cartao configurada no ERP.</Text>
                </View>
              )}

              <Text style={styles.label}>NSU (opcional)</Text>
              <TextInput
                value={nsuCartao}
                onChangeText={setNsuCartao}
                placeholder="Codigo NSU da maquininha"
                keyboardType="number-pad"
                style={styles.input}
              />

              {formaPagamento === "credito" && parcelasCredito.length > 1 ? (
                <View style={styles.parcelasBox}>
                  <Text style={styles.label}>Parcelamento</Text>
                  <View style={styles.parcelasGrid}>
                    {parcelasCredito.map((parcela) => (
                      <TouchableOpacity
                        key={parcela}
                        style={[styles.parcelaBotao, numeroParcelas === parcela && styles.parcelaBotaoAtivo]}
                        onPress={() => setNumeroParcelas(parcela)}
                      >
                        <Text style={[styles.parcelaTexto, numeroParcelas === parcela && styles.parcelaTextoAtivo]}>
                          {parcela}x
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              ) : null}
            </View>
          ) : null}

          <Text style={styles.label}>Observacao</Text>
          <TextInput
            value={observacoes}
            onChangeText={setObservacoes}
            placeholder="Opcional"
            style={[styles.input, styles.inputMultilinha]}
            multiline
          />
        </View>

        <View style={styles.resumo}>
          <View>
            <Text style={styles.resumoLabel}>Total a pagar</Text>
            <Text style={styles.resumoValor}>{formatarMoeda(valorAPagar)}</Text>
            {valorAPagar !== total ? (
              <Text style={styles.resumoSubvalor}>Venda {formatarMoeda(totalComBeneficios)}</Text>
            ) : null}
          </View>
          <View style={styles.resumoAcoes}>
            <TouchableOpacity
              style={[styles.botaoSalvarAberta, (salvandoAberta || finalizando || !carrinho.length || !caixa?.aberto) && styles.botaoDesabilitado]}
              onPress={salvarAberta}
              disabled={salvandoAberta || finalizando || !carrinho.length || !caixa?.aberto}
            >
              {salvandoAberta ? <ActivityIndicator color={CORES.primario} /> : <Ionicons name="save-outline" size={18} color={CORES.primario} />}
              <Text style={styles.botaoSalvarAbertaTexto}>Salvar para o caixa</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.botaoFinalizar, (finalizando || salvandoAberta || !carrinho.length || !caixa?.aberto) && styles.botaoDesabilitado]}
              onPress={finalizar}
              disabled={finalizando || salvandoAberta || !carrinho.length || !caixa?.aberto}
            >
              {finalizando ? <ActivityIndicator color="#fff" /> : <Ionicons name="checkmark-circle" size={20} color="#fff" />}
              <Text style={styles.botaoFinalizarTexto}>Finalizar</Text>
            </TouchableOpacity>
          </View>
        </View>
    </KeyboardSafeScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, gap: ESPACO.md, paddingBottom: ESPACO.xxl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg, backgroundColor: CORES.fundo },
  tituloPermissao: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto, marginVertical: ESPACO.md },
  botaoPrimario: {
    height: 48,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    paddingHorizontal: ESPACO.lg,
    alignItems: "center",
    justifyContent: "center",
  },
  botaoPrimarioTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  headerCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    ...SOMBRA,
  },
  headerIcone: {
    width: 48,
    height: 48,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primarioClaro,
    alignItems: "center",
    justifyContent: "center",
    marginRight: ESPACO.md,
  },
  titulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto },
  subtitulo: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  botaoAtualizarCaixa: {
    width: 40,
    height: 40,
    borderRadius: RAIO.circulo,
    backgroundColor: CORES.primarioClaro,
    alignItems: "center",
    justifyContent: "center",
  },
  caixaBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
  },
  caixaAberto: { backgroundColor: "#ECFDF5", borderColor: "#BBF7D0" },
  caixaFechado: { backgroundColor: "#FFFBEB", borderColor: "#FDE68A" },
  caixaTexto: { flex: 1, color: CORES.texto, fontSize: FONTE.normal, fontWeight: "700" },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    gap: ESPACO.sm,
    ...SOMBRA,
  },
  botaoScan: {
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoScanTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  buscaLinha: { flexDirection: "row", gap: ESPACO.sm },
  inputBusca: {
    flex: 1,
    height: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    color: CORES.texto,
    fontSize: FONTE.normal,
    backgroundColor: "#fff",
  },
  botaoBusca: {
    width: 52,
    height: 48,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
  },
  sugestao: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginTop: ESPACO.xs,
  },
  sugestaoNome: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  sugestaoMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  linhaTitulo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  secaoTitulo: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  badge: {
    backgroundColor: CORES.primarioClaro,
    color: CORES.primario,
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
    fontWeight: "800",
    overflow: "hidden",
  },
  vazio: { alignItems: "center", paddingVertical: ESPACO.lg },
  vazioTexto: { marginTop: ESPACO.sm, color: CORES.textoSecundario, fontSize: FONTE.normal },
  itemCarrinho: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: ESPACO.sm,
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    paddingTop: ESPACO.sm,
  },
  produtoImagemWrap: {
    width: 54,
    height: 54,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.fundo,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
  },
  produtoImagemWrapCompacta: {
    width: 44,
    height: 44,
  },
  produtoImagem: { width: "100%", height: "100%" },
  itemNome: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  itemMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  itemCarrinhoConteudo: { flex: 1, gap: ESPACO.xs },
  itemCarrinhoTopo: { flexDirection: "row", alignItems: "flex-start", gap: ESPACO.sm },
  itemControles: { flexDirection: "row", flexWrap: "wrap", gap: ESPACO.sm },
  campoCarrinho: { gap: 3 },
  campoCarrinhoLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena, fontWeight: "800" },
  quantidadeBox: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: CORES.borda, borderRadius: RAIO.md },
  botaoQuantidade: { width: 34, height: 38, alignItems: "center", justifyContent: "center" },
  inputQuantidade: {
    width: 66,
    height: 38,
    textAlign: "center",
    color: CORES.texto,
    fontWeight: "800",
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: CORES.borda,
  },
  inputValorItem: {
    width: 92,
    height: 40,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.sm,
    textAlign: "right",
    color: CORES.texto,
    fontWeight: "800",
    backgroundColor: "#fff",
  },
  itemSubtotal: { minWidth: 82, textAlign: "right", fontWeight: "800", color: CORES.texto },
  clienteSelecionado: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#BBF7D0",
    backgroundColor: "#ECFDF5",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  clienteNome: { fontSize: FONTE.media, fontWeight: "800", color: CORES.texto },
  clienteMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  botaoDetalhesCliente: {
    height: 36,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: "#BFDBFE",
    paddingHorizontal: ESPACO.sm,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 4,
    marginRight: ESPACO.xs,
    backgroundColor: "#EFF6FF",
  },
  botaoDetalhesClienteTexto: { color: CORES.primario, fontWeight: "800", fontSize: FONTE.pequena },
  detalhesCliente: {
    borderWidth: 1,
    borderColor: "#BFDBFE",
    backgroundColor: "#EFF6FF",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: 3,
  },
  detalhesClienteTitulo: { color: CORES.texto, fontWeight: "900", fontSize: FONTE.media },
  detalhesClienteSubtitulo: { color: CORES.primario, fontWeight: "900", fontSize: FONTE.pequena, marginTop: ESPACO.xs },
  detalhesClienteLinha: { color: CORES.textoSecundario, fontSize: FONTE.pequena },
  botaoLimpar: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    backgroundColor: "#FEE2E2",
    alignItems: "center",
    justifyContent: "center",
  },
  formasGrid: { flexDirection: "row", flexWrap: "wrap", gap: ESPACO.sm },
  formaBotao: {
    flexGrow: 1,
    minWidth: "46%",
    height: 52,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
    backgroundColor: "#fff",
  },
  formaBotaoAtivo: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  formaTexto: { color: CORES.textoSecundario, fontWeight: "800" },
  formaTextoAtivo: { color: CORES.primario },
  cartaoBox: { gap: ESPACO.xs },
  cartaoInstrucao: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: -ESPACO.xs },
  cartaoOpcoesGrid: { gap: ESPACO.xs },
  cartaoOpcao: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: "#fff",
    padding: ESPACO.sm,
    gap: 2,
  },
  cartaoOpcaoAtiva: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  cartaoOpcaoTitulo: { color: CORES.texto, fontWeight: "900", fontSize: FONTE.normal },
  cartaoOpcaoTituloAtivo: { color: CORES.primario },
  cartaoOpcaoSubtitulo: { color: CORES.textoSecundario, fontSize: FONTE.pequena },
  cartaoOpcaoAviso: { color: CORES.primario, fontSize: FONTE.pequena, fontWeight: "800" },
  cartaoAviso: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.xs,
    borderWidth: 1,
    borderColor: "#FECACA",
    backgroundColor: "#FEF2F2",
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
  },
  cartaoAvisoTexto: { flex: 1, color: CORES.erro, fontWeight: "700", fontSize: FONTE.pequena },
  parcelasBox: { gap: ESPACO.xs },
  parcelasGrid: { flexDirection: "row", flexWrap: "wrap", gap: ESPACO.xs },
  parcelaBotao: {
    minWidth: 48,
    height: 38,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fff",
  },
  parcelaBotaoAtivo: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  parcelaTexto: { color: CORES.textoSecundario, fontWeight: "800" },
  parcelaTextoAtivo: { color: CORES.primario },
  label: { fontSize: FONTE.normal, fontWeight: "700", color: CORES.texto, marginTop: ESPACO.xs },
  beneficioErro: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.xs,
    backgroundColor: "#FEF2F2",
    borderWidth: 1,
    borderColor: "#FECACA",
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
  },
  beneficioErroTexto: { flex: 1, color: CORES.erro, fontSize: FONTE.pequena, fontWeight: "700" },
  beneficioInfo: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.xs,
    backgroundColor: CORES.fundo,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
  },
  beneficioInfoTexto: { flex: 1, color: CORES.textoSecundario, fontSize: FONTE.pequena },
  cuponsLista: { gap: ESPACO.xs },
  cupomChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.xs,
    borderWidth: 1,
    borderColor: "#BFDBFE",
    backgroundColor: "#EFF6FF",
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
  },
  cupomChipTexto: { flex: 1, color: CORES.primario, fontWeight: "800", fontSize: FONTE.pequena },
  beneficiosGeradosBox: {
    borderWidth: 1,
    borderColor: "#BBF7D0",
    backgroundColor: "#ECFDF5",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.xs,
  },
  beneficiosGeradosTitulo: { color: "#065F46", fontWeight: "900", fontSize: FONTE.normal },
  beneficioGeradoLinha: { flexDirection: "row", alignItems: "center", gap: ESPACO.sm },
  beneficioGeradoTitulo: { color: CORES.texto, fontWeight: "800", fontSize: FONTE.pequena },
  beneficioGeradoDescricao: { color: CORES.textoSecundario, fontSize: FONTE.pequena },
  cashbackBox: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#BBF7D0",
    backgroundColor: "#ECFDF5",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.md,
  },
  cashbackTitulo: { color: CORES.textoSecundario, fontWeight: "700", fontSize: FONTE.pequena },
  cashbackValor: { color: CORES.sucesso, fontWeight: "900", fontSize: FONTE.grande },
  cashbackToggle: {
    height: 40,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: CORES.primario,
    paddingHorizontal: ESPACO.md,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.xs,
    backgroundColor: "#fff",
  },
  cashbackToggleAtivo: { backgroundColor: CORES.primario },
  cashbackToggleTexto: { color: CORES.primario, fontWeight: "900" },
  cashbackToggleTextoAtivo: { color: "#fff" },
  beneficioResumo: {
    borderTopWidth: 1,
    borderTopColor: CORES.borda,
    paddingTop: ESPACO.sm,
    gap: ESPACO.xs,
  },
  beneficioLinha: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  beneficioResumoLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena },
  beneficioResumoValor: { color: CORES.texto, fontWeight: "800" },
  beneficioResumoDesconto: { color: CORES.sucesso, fontWeight: "900" },
  beneficioResumoTotal: { color: CORES.texto, fontSize: FONTE.media, fontWeight: "900" },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    fontSize: FONTE.media,
    color: CORES.texto,
    backgroundColor: "#fff",
  },
  inputMultilinha: { minHeight: 80, textAlignVertical: "top" },
  troco: { color: CORES.sucesso, fontWeight: "800", fontSize: FONTE.media },
  resumo: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: ESPACO.md,
    ...SOMBRA,
  },
  resumoLabel: { color: CORES.textoSecundario, fontSize: FONTE.pequena, fontWeight: "700" },
  resumoValor: { color: CORES.texto, fontSize: FONTE.titulo, fontWeight: "900", marginTop: 2 },
  resumoSubvalor: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  resumoAcoes: { flex: 1, gap: ESPACO.sm },
  botaoSalvarAberta: {
    minHeight: 48,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: "#BFDBFE",
    backgroundColor: "#EFF6FF",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.xs,
    paddingHorizontal: ESPACO.sm,
  },
  botaoSalvarAbertaTexto: { color: CORES.primario, fontSize: FONTE.pequena, fontWeight: "900" },
  botaoFinalizar: {
    minHeight: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoDesabilitado: { opacity: 0.5 },
  botaoFinalizarTexto: { color: "#fff", fontSize: FONTE.media, fontWeight: "900" },
  scannerContainer: { flex: 1, backgroundColor: "#000" },
  camera: { flex: 1 },
  scannerOverlay: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg },
  fecharScanner: {
    position: "absolute",
    top: 54,
    right: 24,
    width: 44,
    height: 44,
    borderRadius: RAIO.circulo,
    backgroundColor: "rgba(0,0,0,0.45)",
    alignItems: "center",
    justifyContent: "center",
  },
  frameScan: {
    width: "82%",
    height: 180,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: RAIO.lg,
    backgroundColor: "rgba(255,255,255,0.08)",
  },
  scannerTexto: { color: "#fff", marginTop: ESPACO.md, fontSize: FONTE.media, fontWeight: "800", textAlign: "center" },
  botaoScanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    marginTop: ESPACO.md,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
  },
  botaoScannerTexto: { color: "#fff", fontWeight: "800" },
});
