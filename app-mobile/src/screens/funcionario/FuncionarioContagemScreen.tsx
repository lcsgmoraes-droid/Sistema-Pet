import { useIsFocused } from "@react-navigation/native";
import { useCameraPermissions } from "expo-camera";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Vibration } from "react-native";

import {
  baixarContagemFuncionario,
  buscarFornecedoresContagemFuncionario,
  excluirContagemFuncionario,
  listarContagensFuncionario,
  obterContagemFuncionario,
  salvarContagemFuncionario,
} from "../../services/funcionarioContagem.service";
import {
  buscarProdutoFuncionarioPorBarcode,
  buscarProdutosFuncionario,
} from "../../services/funcionarioEstoque.service";
import type {
  FuncionarioContagem,
  FuncionarioContagemFornecedor,
  FuncionarioContagemResumo,
  FuncionarioProdutoEstoque,
} from "../../types";
import { FuncionarioContagemContent } from "./contagem/FuncionarioContagemContent";
import {
  FuncionarioContagemPermissionRequest,
  FuncionarioContagemScanner,
} from "./contagem/FuncionarioContagemScanner";
import { mensagemErroApi, parseNumero, type ContagemItemLocal } from "./contagem/FuncionarioContagemUtils";

export default function FuncionarioContagemScreen() {
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const [scannerAberto, setScannerAberto] = useState(false);
  const [scanAtivo, setScanAtivo] = useState(true);
  const [buscandoProduto, setBuscandoProduto] = useState(false);
  const [buscaManual, setBuscaManual] = useState("");
  const [sugestoes, setSugestoes] = useState<FuncionarioProdutoEstoque[]>([]);
  const [produto, setProduto] = useState<FuncionarioProdutoEstoque | null>(null);
  const [quantidade, setQuantidade] = useState("1");
  const [observacaoItem, setObservacaoItem] = useState("");
  const [itens, setItens] = useState<ContagemItemLocal[]>([]);
  const [titulo, setTitulo] = useState("Contagem para devolucao");
  const [observacao, setObservacao] = useState("");
  const [buscaFornecedor, setBuscaFornecedor] = useState("");
  const [fornecedores, setFornecedores] = useState<FuncionarioContagemFornecedor[]>([]);
  const [fornecedor, setFornecedor] = useState<FuncionarioContagemFornecedor | null>(null);
  const [mostrarCusto, setMostrarCusto] = useState(false);
  const [mostrarVenda, setMostrarVenda] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [exportando, setExportando] = useState<"pdf" | "xlsx" | null>(null);
  const [contagemSalva, setContagemSalva] = useState<FuncionarioContagem | null>(null);
  const [contagensRecentes, setContagensRecentes] = useState<FuncionarioContagemResumo[]>([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [excluindoContagemId, setExcluindoContagemId] = useState<number | null>(null);
  const ultimoScan = useRef("");
  const produtoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fornecedorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (scannerAberto && !permission?.granted) {
      requestPermission();
    }
  }, [scannerAberto, permission?.granted, requestPermission]);

  useEffect(() => {
    if (!isFocused) return;
    carregarRecentes(false);
  }, [isFocused]);

  useEffect(() => {
    if (!isFocused) return;
    const termo = buscaManual.trim();
    if (produtoTimer.current) clearTimeout(produtoTimer.current);
    if (termo.length < 2) {
      setSugestoes([]);
      return;
    }
    produtoTimer.current = setTimeout(() => {
      buscarManualProduto(false);
    }, 350);
    return () => {
      if (produtoTimer.current) clearTimeout(produtoTimer.current);
    };
  }, [buscaManual, isFocused]);

  useEffect(() => {
    if (!isFocused || fornecedor) return;
    const termo = buscaFornecedor.trim();
    if (fornecedorTimer.current) clearTimeout(fornecedorTimer.current);
    if (termo.length < 2) {
      setFornecedores([]);
      return;
    }
    fornecedorTimer.current = setTimeout(() => {
      buscarFornecedor(false);
    }, 350);
    return () => {
      if (fornecedorTimer.current) clearTimeout(fornecedorTimer.current);
    };
  }, [buscaFornecedor, fornecedor, isFocused]);

  const quantidadeNumero = useMemo(() => parseNumero(quantidade), [quantidade]);
  const resumo = useMemo(() => {
    const quantidadeTotal = itens.reduce((total, item) => total + item.quantidade, 0);
    const totalCusto = itens.reduce(
      (total, item) => total + item.quantidade * Number(item.produto.preco_custo ?? 0),
      0,
    );
    const totalVenda = itens.reduce(
      (total, item) => total + item.quantidade * Number(item.produto.preco_venda ?? 0),
      0,
    );
    return { quantidadeTotal, totalCusto, totalVenda };
  }, [itens]);

  function invalidarContagemSalva() {
    if (contagemSalva) setContagemSalva(null);
  }

  function limparContagemAtual() {
    setProduto(null);
    setBuscaManual("");
    setSugestoes([]);
    setQuantidade("1");
    setObservacaoItem("");
    setItens([]);
    setTitulo("Contagem para devolucao");
    setObservacao("");
    setFornecedor(null);
    setBuscaFornecedor("");
    setFornecedores([]);
    setContagemSalva(null);
  }

  function selecionarProduto(item: FuncionarioProdutoEstoque) {
    setProduto(item);
    setQuantidade("1");
    setObservacaoItem("");
    setSugestoes([]);
    setBuscaManual("");
  }

  async function carregarRecentes(mostrarErro = true) {
    setCarregandoHistorico(true);
    try {
      setContagensRecentes(await listarContagensFuncionario());
    } catch (error: any) {
      if (mostrarErro) {
        Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel carregar as contagens."));
      }
    } finally {
      setCarregandoHistorico(false);
    }
  }

  async function buscarManualProduto(mostrarAlerta = true) {
    const termo = buscaManual.trim();
    if (termo.length < 2) return;
    setBuscandoProduto(true);
    try {
      setSugestoes(await buscarProdutosFuncionario(termo));
    } catch (error: any) {
      if (mostrarAlerta) {
        Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar no ERP."));
      }
    } finally {
      setBuscandoProduto(false);
    }
  }

  async function buscarFornecedor(mostrarAlerta = true) {
    const termo = buscaFornecedor.trim();
    if (termo.length < 2) return;
    try {
      setFornecedores(await buscarFornecedoresContagemFuncionario(termo));
    } catch (error: any) {
      if (mostrarAlerta) {
        Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar fornecedor."));
      }
    }
  }

  function selecionarFornecedor(item: FuncionarioContagemFornecedor) {
    setFornecedor(item);
    setBuscaFornecedor(item.nome);
    setFornecedores([]);
    invalidarContagemSalva();
  }

  function limparFornecedor() {
    setFornecedor(null);
    setBuscaFornecedor("");
    setFornecedores([]);
    invalidarContagemSalva();
  }

  function alterarBuscaFornecedor(valor: string) {
    setBuscaFornecedor(valor);
    setFornecedor(null);
    invalidarContagemSalva();
  }

  async function onBarcodeScanned({ data }: { data: string }) {
    if (!scanAtivo || buscandoProduto || data === ultimoScan.current) return;
    ultimoScan.current = data;
    setScanAtivo(false);
    setBuscandoProduto(true);
    Vibration.vibrate(80);

    try {
      const encontrado = await buscarProdutoFuncionarioPorBarcode(data);
      if (!encontrado) {
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
      selecionarProduto(encontrado);
      setScannerAberto(false);
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel buscar o produto."));
    } finally {
      setBuscandoProduto(false);
    }
  }

  function adicionarItem() {
    if (!produto) {
      Alert.alert("Produto obrigatorio", "Escaneie ou busque um produto antes de adicionar.");
      return;
    }
    if (quantidadeNumero == null || quantidadeNumero <= 0) {
      Alert.alert("Quantidade invalida", "Informe a quantidade contada.");
      return;
    }

    const observacaoLimpa = observacaoItem.trim() || null;
    setItens((atuais) => {
      const existente = atuais.find((item) => item.produto.id === produto.id);
      if (!existente) {
        return [
          ...atuais,
          {
            id: String(produto.id),
            produto,
            quantidade: quantidadeNumero,
            observacao: observacaoLimpa,
          },
        ];
      }
      return atuais.map((item) =>
        item.produto.id === produto.id
          ? {
              ...item,
              quantidade: item.quantidade + quantidadeNumero,
              observacao: observacaoLimpa || item.observacao,
            }
          : item,
      );
    });
    invalidarContagemSalva();
    setProduto(null);
    setQuantidade("1");
    setObservacaoItem("");
  }

  function removerItem(id: string) {
    setItens((atuais) => atuais.filter((item) => item.id !== id));
    invalidarContagemSalva();
  }

  function alterarTitulo(valor: string) {
    setTitulo(valor);
    invalidarContagemSalva();
  }

  function alterarObservacao(valor: string) {
    setObservacao(valor);
    invalidarContagemSalva();
  }

  async function salvar(mostrarAlerta = true): Promise<FuncionarioContagem | null> {
    if (!itens.length) {
      Alert.alert("Lista vazia", "Adicione ao menos um produto contado.");
      return null;
    }
    setSalvando(true);
    try {
      const resposta = await salvarContagemFuncionario({
        titulo: titulo.trim() || "Contagem para devolucao",
        fornecedor_id: fornecedor?.id ?? null,
        observacao: observacao.trim() || null,
        itens: itens.map((item) => ({
          produto_id: item.produto.id,
          quantidade: item.quantidade,
          observacao: item.observacao ?? null,
        })),
      });
      setContagemSalva(resposta);
      await carregarRecentes(false);
      if (mostrarAlerta) {
        Alert.alert("Contagem salva", `Arquivo base #${resposta.id} pronto para exportar.`);
      }
      return resposta;
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel salvar a contagem."));
      return null;
    } finally {
      setSalvando(false);
    }
  }

  async function exportar(formato: "pdf" | "xlsx") {
    const alvo = contagemSalva ?? (await salvar(false));
    if (!alvo) return;
    setExportando(formato);
    try {
      await baixarContagemFuncionario(alvo.id, formato, {
        mostrar_custo: mostrarCusto,
        mostrar_venda: mostrarVenda,
      });
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel gerar o arquivo."));
    } finally {
      setExportando(null);
    }
  }

  async function abrirContagem(contagemId: number) {
    setCarregandoHistorico(true);
    try {
      const aberta = await obterContagemFuncionario(contagemId);
      setContagemSalva(aberta);
      setTitulo(aberta.titulo);
      setObservacao(aberta.observacao ?? "");
      setFornecedor(
        aberta.fornecedor_id
          ? {
              id: aberta.fornecedor_id,
              nome: aberta.fornecedor_nome || "Fornecedor",
              documento: null,
            }
          : null,
      );
      setBuscaFornecedor(aberta.fornecedor_nome ?? "");
      setItens(
        aberta.itens.map((item) => ({
          id: String(item.produto_id),
          quantidade: item.quantidade,
          observacao: item.observacao,
          produto: {
            id: item.produto_id,
            nome: item.nome,
            codigo: item.codigo,
            codigo_barras: item.codigo_barras,
            gtin_ean: item.gtin_ean,
            unidade: item.unidade,
            preco_custo: item.preco_custo,
            preco_venda: item.preco_venda,
            estoque_atual: 0,
            imagem_url: null,
            permite_balanco: true,
          },
        })),
      );
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel abrir a contagem."));
    } finally {
      setCarregandoHistorico(false);
    }
  }

  function confirmarExcluirContagem(contagem: FuncionarioContagemResumo) {
    Alert.alert(
      "Excluir contagem",
      `Deseja excluir a contagem #${contagem.id}? Essa acao nao mexe no estoque.`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Excluir",
          style: "destructive",
          onPress: () => excluirContagem(contagem.id),
        },
      ],
    );
  }

  async function excluirContagem(contagemId: number) {
    setExcluindoContagemId(contagemId);
    try {
      await excluirContagemFuncionario(contagemId);
      setContagensRecentes((atuais) => atuais.filter((item) => item.id !== contagemId));
      if (contagemSalva?.id === contagemId) {
        limparContagemAtual();
      }
    } catch (error: any) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel excluir a contagem."));
    } finally {
      setExcluindoContagemId(null);
    }
  }

  function abrirScanner() {
    ultimoScan.current = "";
    setScanAtivo(true);
    setScannerAberto(true);
  }

  function reativarScanner() {
    ultimoScan.current = "";
    setScanAtivo(true);
  }

  if (scannerAberto && permission && !permission.granted) {
    return <FuncionarioContagemPermissionRequest requestPermission={requestPermission} />;
  }

  if (scannerAberto && isFocused) {
    return (
      <FuncionarioContagemScanner
        scanAtivo={scanAtivo}
        buscandoProduto={buscandoProduto}
        onBarcodeScanned={onBarcodeScanned}
        onClose={() => setScannerAberto(false)}
        onResetScan={reativarScanner}
      />
    );
  }

  return (
    <FuncionarioContagemContent
      titulo={titulo}
      alterarTitulo={alterarTitulo}
      buscaFornecedor={buscaFornecedor}
      alterarBuscaFornecedor={alterarBuscaFornecedor}
      fornecedor={fornecedor}
      limparFornecedor={limparFornecedor}
      buscarFornecedor={buscarFornecedor}
      fornecedores={fornecedores}
      selecionarFornecedor={selecionarFornecedor}
      observacao={observacao}
      alterarObservacao={alterarObservacao}
      abrirScanner={abrirScanner}
      buscaManual={buscaManual}
      setBuscaManual={setBuscaManual}
      buscarManualProduto={buscarManualProduto}
      buscandoProduto={buscandoProduto}
      sugestoes={sugestoes}
      selecionarProduto={selecionarProduto}
      produto={produto}
      limparProduto={() => setProduto(null)}
      quantidade={quantidade}
      setQuantidade={setQuantidade}
      observacaoItem={observacaoItem}
      setObservacaoItem={setObservacaoItem}
      adicionarItem={adicionarItem}
      itens={itens}
      removerItem={removerItem}
      resumo={resumo}
      mostrarCusto={mostrarCusto}
      setMostrarCusto={setMostrarCusto}
      mostrarVenda={mostrarVenda}
      setMostrarVenda={setMostrarVenda}
      salvando={salvando}
      salvar={salvar}
      exportando={exportando}
      exportar={exportar}
      contagemSalva={contagemSalva}
      contagensRecentes={contagensRecentes}
      carregandoHistorico={carregandoHistorico}
      abrirContagem={abrirContagem}
      confirmarExcluirContagem={confirmarExcluirContagem}
      excluindoContagemId={excluindoContagemId}
    />
  );
}
