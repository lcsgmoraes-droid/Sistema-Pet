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
import KeyboardSafeScrollView from "../../components/KeyboardSafeScrollView";
import {
  baixarContagemFuncionario,
  buscarFornecedoresContagemFuncionario,
  listarContagensFuncionario,
  obterContagemFuncionario,
  salvarContagemFuncionario,
} from "../../services/funcionarioContagem.service";
import {
  buscarProdutoFuncionarioPorBarcode,
  buscarProdutosFuncionario,
} from "../../services/funcionarioEstoque.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import {
  FuncionarioContagem,
  FuncionarioContagemFornecedor,
  FuncionarioContagemResumo,
  FuncionarioProdutoEstoque,
} from "../../types";
import { formatarMoeda } from "../../utils/format";

type ContagemItemLocal = {
  id: string;
  produto: FuncionarioProdutoEstoque;
  quantidade: number;
  observacao?: string | null;
};

function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  const message = error?.response?.data?.message;
  if (typeof message === "string" && message.trim()) return message;
  return fallback;
}

function parseNumero(valor: string): number | null {
  const normalizado = valor.replace(/\./g, "").replace(",", ".").trim();
  if (!normalizado) return null;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : null;
}

function formatarQuantidade(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
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

function CheckboxLinha({
  ativo,
  titulo,
  descricao,
  onPress,
}: {
  ativo: boolean;
  titulo: string;
  descricao: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.checkboxLinha} onPress={onPress}>
      <Ionicons
        name={ativo ? "checkbox-outline" : "square-outline"}
        size={24}
        color={ativo ? CORES.sucesso : CORES.textoClaro}
      />
      <View style={{ flex: 1 }}>
        <Text style={styles.checkboxTitulo}>{titulo}</Text>
        <Text style={styles.checkboxDescricao}>{descricao}</Text>
      </View>
    </TouchableOpacity>
  );
}

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
          <Ionicons name="clipboard-outline" size={24} color={CORES.aviso} />
        </View>
        <View style={styles.headerTexto}>
          <Text style={styles.titulo}>Contagem</Text>
          <Text style={styles.subtitulo}>Bipe, informe a quantidade e gere PDF ou Excel.</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.secaoTitulo}>Cabecalho</Text>
        <Text style={styles.label}>Titulo</Text>
        <TextInput
          value={titulo}
          onChangeText={alterarTitulo}
          placeholder="Ex: Devolucao fornecedor"
          style={styles.input}
        />

        <Text style={styles.label}>Fornecedor</Text>
        <View style={styles.buscaLinha}>
          <TextInput
            value={buscaFornecedor}
            onChangeText={(valor) => {
              setBuscaFornecedor(valor);
              setFornecedor(null);
              invalidarContagemSalva();
            }}
            placeholder="Opcional"
            style={styles.inputBusca}
            returnKeyType="search"
            onSubmitEditing={() => buscarFornecedor()}
          />
          {fornecedor ? (
            <TouchableOpacity style={styles.botaoBusca} onPress={limparFornecedor}>
              <Ionicons name="close" size={20} color="#fff" />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.botaoBusca} onPress={() => buscarFornecedor()}>
              <Ionicons name="search" size={20} color="#fff" />
            </TouchableOpacity>
          )}
        </View>

        {fornecedores.map((item) => (
          <TouchableOpacity key={item.id} style={styles.sugestao} onPress={() => selecionarFornecedor(item)}>
            <View style={styles.fornecedorIcone}>
              <Ionicons name="business-outline" size={18} color={CORES.primario} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.sugestaoNome}>{item.nome}</Text>
              <Text style={styles.sugestaoMeta}>{item.documento || "Fornecedor"}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
          </TouchableOpacity>
        ))}

        <Text style={styles.label}>Observacao da contagem</Text>
        <TextInput
          value={observacao}
          onChangeText={alterarObservacao}
          placeholder="Opcional"
          style={[styles.input, styles.inputMultilinha]}
          multiline
        />
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

        {sugestoes.map((item) => (
          <TouchableOpacity key={item.id} style={styles.sugestao} onPress={() => selecionarProduto(item)}>
            <ProdutoImagem uri={item.imagem_url} />
            <View style={{ flex: 1 }}>
              <Text style={styles.sugestaoNome} numberOfLines={2}>
                {item.nome}
              </Text>
              <Text style={styles.sugestaoMeta}>SKU {item.codigo || "-"} | {item.unidade || "UN"}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
          </TouchableOpacity>
        ))}
      </View>

      {produto ? (
        <View style={styles.card}>
          <View style={styles.produtoCabecalho}>
            <ProdutoImagem uri={produto.imagem_url} compacta />
            <View style={{ flex: 1 }}>
              <Text style={styles.produtoNome}>{produto.nome}</Text>
              <Text style={styles.produtoMeta}>SKU {produto.codigo || "-"} | {produto.unidade || "UN"}</Text>
            </View>
            <TouchableOpacity style={styles.botaoLimpar} onPress={() => setProduto(null)}>
              <Ionicons name="close" size={18} color={CORES.erro} />
            </TouchableOpacity>
          </View>

          <View style={styles.metricas}>
            <View style={styles.metrica}>
              <Text style={styles.metricaLabel}>Custo</Text>
              <Text style={styles.metricaValor}>{formatarMoeda(produto.preco_custo)}</Text>
            </View>
            <View style={styles.metrica}>
              <Text style={styles.metricaLabel}>Venda</Text>
              <Text style={styles.metricaValor}>{formatarMoeda(produto.preco_venda)}</Text>
            </View>
          </View>

          <Text style={styles.label}>Quantidade contada</Text>
          <TextInput
            value={quantidade}
            onChangeText={setQuantidade}
            placeholder="Ex: 12"
            keyboardType="decimal-pad"
            style={styles.input}
          />

          <Text style={styles.label}>Observacao do item</Text>
          <TextInput
            value={observacaoItem}
            onChangeText={setObservacaoItem}
            placeholder="Opcional"
            style={[styles.input, styles.inputMultilinha]}
            multiline
          />

          <TouchableOpacity style={styles.botaoSalvar} onPress={adicionarItem}>
            <Ionicons name="add-circle" size={20} color="#fff" />
            <Text style={styles.botaoSalvarTexto}>Adicionar item</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      <View style={styles.card}>
        <View style={styles.secaoCabecalho}>
          <Text style={styles.secaoTitulo}>Itens contados</Text>
          <Text style={styles.badge}>{itens.length}</Text>
        </View>

        {itens.length ? (
          itens.map((item) => (
            <View key={item.id} style={styles.itemLinha}>
              <ProdutoImagem uri={item.produto.imagem_url} compacta />
              <View style={{ flex: 1 }}>
                <Text style={styles.itemNome} numberOfLines={2}>
                  {item.produto.nome}
                </Text>
                <Text style={styles.itemMeta}>
                  SKU {item.produto.codigo || "-"} | Qtd. {formatarQuantidade(item.quantidade)} {item.produto.unidade || "UN"}
                </Text>
                {item.observacao ? <Text style={styles.itemObs} numberOfLines={2}>{item.observacao}</Text> : null}
              </View>
              <TouchableOpacity style={styles.botaoRemover} onPress={() => removerItem(item.id)}>
                <Ionicons name="trash-outline" size={18} color={CORES.erro} />
              </TouchableOpacity>
            </View>
          ))
        ) : (
          <View style={styles.vazio}>
            <Ionicons name="cube-outline" size={28} color={CORES.textoClaro} />
            <Text style={styles.vazioTexto}>Nenhum produto contado ainda.</Text>
          </View>
        )}

        <View style={styles.resumoBox}>
          <Text style={styles.resumoTexto}>Quantidade total</Text>
          <Text style={styles.resumoValor}>{formatarQuantidade(resumo.quantidadeTotal)}</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.secaoTitulo}>Arquivo</Text>
        <CheckboxLinha
          ativo={mostrarCusto}
          titulo="Mostrar custo"
          descricao="Inclui custo unitario e total de custo."
          onPress={() => setMostrarCusto((atual) => !atual)}
        />
        <CheckboxLinha
          ativo={mostrarVenda}
          titulo="Mostrar venda"
          descricao="Inclui venda unitaria e total de venda."
          onPress={() => setMostrarVenda((atual) => !atual)}
        />

        {mostrarCusto ? (
          <View style={styles.totalLinha}>
            <Text style={styles.totalLabel}>Total custo</Text>
            <Text style={styles.totalValor}>{formatarMoeda(resumo.totalCusto)}</Text>
          </View>
        ) : null}
        {mostrarVenda ? (
          <View style={styles.totalLinha}>
            <Text style={styles.totalLabel}>Total venda</Text>
            <Text style={styles.totalValor}>{formatarMoeda(resumo.totalVenda)}</Text>
          </View>
        ) : null}

        <TouchableOpacity
          style={[styles.botaoSalvar, salvando && styles.botaoDesabilitado]}
          onPress={() => salvar()}
          disabled={salvando}
        >
          {salvando ? <ActivityIndicator color="#fff" /> : <Ionicons name="save-outline" size={20} color="#fff" />}
          <Text style={styles.botaoSalvarTexto}>{contagemSalva ? "Salvar nova versao" : "Salvar contagem"}</Text>
        </TouchableOpacity>

        <View style={styles.exportLinha}>
          <TouchableOpacity
            style={[styles.botaoExportar, (!itens.length || exportando !== null) && styles.botaoDesabilitado]}
            onPress={() => exportar("pdf")}
            disabled={!itens.length || exportando !== null}
          >
            {exportando === "pdf" ? <ActivityIndicator color="#fff" /> : <Ionicons name="document-text-outline" size={18} color="#fff" />}
            <Text style={styles.botaoExportarTexto}>PDF</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.botaoExportar, (!itens.length || exportando !== null) && styles.botaoDesabilitado]}
            onPress={() => exportar("xlsx")}
            disabled={!itens.length || exportando !== null}
          >
            {exportando === "xlsx" ? <ActivityIndicator color="#fff" /> : <Ionicons name="grid-outline" size={18} color="#fff" />}
            <Text style={styles.botaoExportarTexto}>Excel</Text>
          </TouchableOpacity>
        </View>

        {contagemSalva ? (
          <View style={styles.resultado}>
            <Ionicons name="checkmark-circle-outline" size={18} color={CORES.sucesso} />
            <Text style={styles.resultadoTexto}>Contagem #{contagemSalva.id} salva.</Text>
          </View>
        ) : null}
      </View>

      {contagensRecentes.length || carregandoHistorico ? (
        <View style={styles.card}>
          <View style={styles.secaoCabecalho}>
            <Text style={styles.secaoTitulo}>Recentes</Text>
            {carregandoHistorico ? <ActivityIndicator color={CORES.primario} /> : null}
          </View>
          {contagensRecentes.slice(0, 5).map((item) => (
            <TouchableOpacity key={item.id} style={styles.historicoItem} onPress={() => abrirContagem(item.id)}>
              <View style={{ flex: 1 }}>
                <Text style={styles.historicoTitulo}>{item.titulo}</Text>
                <Text style={styles.historicoMeta}>
                  #{item.id} | {item.total_itens} item(ns) | {item.fornecedor_nome || "Sem fornecedor"}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
            </TouchableOpacity>
          ))}
        </View>
      ) : null}
    </KeyboardSafeScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  conteudo: { padding: ESPACO.md, gap: ESPACO.md, paddingBottom: ESPACO.xxl },
  centrado: { flex: 1, alignItems: "center", justifyContent: "center", padding: ESPACO.lg, backgroundColor: CORES.fundo },
  tituloPermissao: { fontSize: FONTE.titulo, fontWeight: "700", color: CORES.texto, marginVertical: ESPACO.md },
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
    backgroundColor: "#FEF3C7",
    alignItems: "center",
    justifyContent: "center",
    marginRight: ESPACO.md,
  },
  headerTexto: { flex: 1 },
  titulo: { fontSize: FONTE.titulo, fontWeight: "800", color: CORES.texto },
  subtitulo: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
    gap: ESPACO.sm,
    ...SOMBRA,
  },
  secaoCabecalho: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: ESPACO.sm },
  secaoTitulo: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  label: { fontSize: FONTE.normal, fontWeight: "700", color: CORES.texto, marginTop: ESPACO.xs },
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
  inputMultilinha: { minHeight: 78, textAlignVertical: "top" },
  buscaLinha: { flexDirection: "row", gap: ESPACO.sm, marginTop: ESPACO.xs },
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
  fornecedorIcone: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    backgroundColor: "#DBEAFE",
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
  sugestaoNome: { fontSize: FONTE.normal, fontWeight: "700", color: CORES.texto },
  sugestaoMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  botaoScan: {
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoScanTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
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
  produtoImagemWrapCompacta: { width: 44, height: 44 },
  produtoImagem: { width: "100%", height: "100%" },
  produtoCabecalho: { flexDirection: "row", alignItems: "flex-start", gap: ESPACO.sm },
  produtoNome: { fontSize: FONTE.grande, fontWeight: "800", color: CORES.texto },
  produtoMeta: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  botaoLimpar: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    backgroundColor: "#FEE2E2",
    alignItems: "center",
    justifyContent: "center",
  },
  metricas: { flexDirection: "row", gap: ESPACO.sm },
  metrica: { flex: 1, backgroundColor: CORES.fundo, borderRadius: RAIO.sm, padding: ESPACO.sm },
  metricaLabel: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  metricaValor: { fontSize: FONTE.media, fontWeight: "800", color: CORES.texto, marginTop: 2 },
  botaoSalvar: {
    height: 52,
    borderRadius: RAIO.md,
    backgroundColor: CORES.sucesso,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
    marginTop: ESPACO.sm,
  },
  botaoSalvarTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  botaoDesabilitado: { opacity: 0.5 },
  itemLinha: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  itemNome: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  itemMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  itemObs: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 4 },
  botaoRemover: {
    width: 36,
    height: 36,
    borderRadius: RAIO.circulo,
    backgroundColor: "#FEE2E2",
    alignItems: "center",
    justifyContent: "center",
  },
  vazio: { alignItems: "center", justifyContent: "center", paddingVertical: ESPACO.lg, gap: ESPACO.xs },
  vazioTexto: { color: CORES.textoSecundario, fontWeight: "700" },
  badge: {
    overflow: "hidden",
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 4,
    backgroundColor: "#E5E7EB",
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    fontWeight: "800",
  },
  resumoBox: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: CORES.fundo,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
  },
  resumoTexto: { color: CORES.textoSecundario, fontWeight: "700" },
  resumoValor: { color: CORES.texto, fontWeight: "900", fontSize: FONTE.media },
  checkboxLinha: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: ESPACO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  checkboxTitulo: { fontSize: FONTE.normal, color: CORES.texto, fontWeight: "800" },
  checkboxDescricao: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  totalLinha: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#F9FAFB",
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
  },
  totalLabel: { color: CORES.textoSecundario, fontWeight: "800" },
  totalValor: { color: CORES.texto, fontWeight: "900", fontSize: FONTE.media },
  exportLinha: { flexDirection: "row", gap: ESPACO.sm },
  botaoExportar: {
    flex: 1,
    height: 50,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: ESPACO.sm,
  },
  botaoExportarTexto: { color: "#fff", fontWeight: "800", fontSize: FONTE.media },
  resultado: {
    flexDirection: "row",
    gap: ESPACO.sm,
    alignItems: "center",
    backgroundColor: "#ECFDF5",
    borderColor: "#BBF7D0",
    borderWidth: 1,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  resultadoTexto: { flex: 1, color: "#065F46", fontWeight: "700" },
  historicoItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
  },
  historicoTitulo: { fontSize: FONTE.normal, fontWeight: "800", color: CORES.texto },
  historicoMeta: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  botaoPrimario: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.lg,
    paddingVertical: ESPACO.md,
  },
  botaoPrimarioTexto: { color: "#fff", fontWeight: "800" },
  scannerContainer: { flex: 1, backgroundColor: "#000" },
  camera: { flex: 1 },
  scannerOverlay: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(0,0,0,0.25)" },
  fecharScanner: {
    position: "absolute",
    top: 48,
    right: 24,
    width: 44,
    height: 44,
    borderRadius: RAIO.circulo,
    backgroundColor: "rgba(0,0,0,0.5)",
    alignItems: "center",
    justifyContent: "center",
  },
  frameScan: {
    width: 260,
    height: 160,
    borderWidth: 3,
    borderColor: "#fff",
    borderRadius: RAIO.md,
  },
  scannerTexto: { color: "#fff", marginTop: ESPACO.lg, fontSize: FONTE.media, fontWeight: "700" },
  botaoScanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: ESPACO.sm,
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    marginTop: ESPACO.md,
  },
  botaoScannerTexto: { color: "#fff", fontWeight: "800" },
});
