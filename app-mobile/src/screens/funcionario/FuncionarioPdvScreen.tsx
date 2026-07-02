import { useIsFocused } from "@react-navigation/native";
import { useCameraPermissions } from "expo-camera";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Vibration } from "react-native";

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
import type {
  FuncionarioPdvBeneficiosPreview,
  FuncionarioPdvCaixa,
  FuncionarioPdvCliente,
  FuncionarioPdvFormaPagamento,
  FuncionarioPdvFormaPagamentoOpcao,
  FuncionarioPdvProduto,
} from "../../types";
import { formatarMoeda } from "../../utils/format";
import { FuncionarioPdvContent } from "./pdv/FuncionarioPdvContent";
import {
  FuncionarioPdvPermissionRequest,
  FuncionarioPdvScanner,
} from "./pdv/FuncionarioPdvScanner";
import {
  arredondarQuantidadePdv,
  mensagemErroApi,
  parseNumero,
  type ItemCarrinhoPdv,
} from "./pdv/FuncionarioPdvUtils";

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

  function abrirScanner() {
    ultimoScan.current = "";
    setScanAtivo(true);
    setScannerAberto(true);
  }

  function resetarScanner() {
    ultimoScan.current = "";
    setScanAtivo(true);
  }

  if (scannerAberto && permission && !permission.granted) {
    return <FuncionarioPdvPermissionRequest requestPermission={requestPermission} />;
  }

  if (scannerAberto && isFocused) {
    return (
      <FuncionarioPdvScanner
        scanAtivo={scanAtivo}
        buscandoProduto={buscandoProduto}
        onBarcodeScanned={onBarcodeScanned}
        onClose={() => setScannerAberto(false)}
        onResetScan={resetarScanner}
      />
    );
  }

  return (
    <FuncionarioPdvContent
      caixa={caixa}
      carregarCaixa={carregarCaixa}
      carregandoCaixa={carregandoCaixa}
      abrirScanner={abrirScanner}
      buscaManual={buscaManual}
      setBuscaManual={setBuscaManual}
      buscarManualProduto={buscarManualProduto}
      buscandoProduto={buscandoProduto}
      sugestoes={sugestoes}
      adicionarProduto={adicionarProduto}
      carrinho={carrinho}
      totalItens={totalItens}
      quantidadeEditando={quantidadeEditando}
      valorEditando={valorEditando}
      alterarQuantidade={alterarQuantidade}
      editarQuantidadeItem={editarQuantidadeItem}
      finalizarEdicaoQuantidade={finalizarEdicaoQuantidade}
      editarValorItem={editarValorItem}
      finalizarEdicaoValor={finalizarEdicaoValor}
      cliente={cliente}
      setCliente={setCliente}
      mostrarDetalhesCliente={mostrarDetalhesCliente}
      setMostrarDetalhesCliente={setMostrarDetalhesCliente}
      clienteBusca={clienteBusca}
      setClienteBusca={setClienteBusca}
      buscarCliente={buscarCliente}
      clientesSugestoes={clientesSugestoes}
      setClientesSugestoes={setClientesSugestoes}
      carregandoBeneficios={carregandoBeneficios}
      cupomCodigo={cupomCodigo}
      setCupomCodigo={setCupomCodigo}
      carregarBeneficios={carregarBeneficios}
      erroBeneficios={erroBeneficios}
      beneficiosPreview={beneficiosPreview}
      totalComBeneficios={totalComBeneficios}
      usarCashback={usarCashback}
      setUsarCashback={setUsarCashback}
      cashbackValor={cashbackValor}
      setCashbackValor={setCashbackValor}
      valorAPagar={valorAPagar}
      formaPagamento={formaPagamento}
      setFormaPagamento={setFormaPagamento}
      setFormaPagamentoIdSelecionada={setFormaPagamentoIdSelecionada}
      setNumeroParcelas={setNumeroParcelas}
      setNsuCartao={setNsuCartao}
      valorRecebido={valorRecebido}
      setValorRecebido={setValorRecebido}
      troco={troco}
      ehCartao={ehCartao}
      formaPagamentoSelecionada={formaPagamentoSelecionada}
      opcoesCartao={opcoesCartao}
      nsuCartao={nsuCartao}
      parcelasCredito={parcelasCredito}
      numeroParcelas={numeroParcelas}
      observacoes={observacoes}
      setObservacoes={setObservacoes}
      total={total}
      finalizando={finalizando}
      salvandoAberta={salvandoAberta}
      salvarAberta={salvarAberta}
      finalizar={finalizar}
    />
  );
}
