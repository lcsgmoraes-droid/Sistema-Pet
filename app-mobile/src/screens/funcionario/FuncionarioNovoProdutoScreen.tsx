import { Ionicons } from "@expo/vector-icons";
import { useIsFocused, useNavigation } from "@react-navigation/native";
import { useCameraPermissions } from "expo-camera";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator, Alert, Linking, Modal, Text, TextInput, TouchableOpacity, View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import KeyboardSafeScrollView from "../../components/KeyboardSafeScrollView";
import {
  consultarCodigoProdutoRapido, criarProdutoRapido, ProdutoRapido, ProdutoRapidoPayload,
} from "../../services/funcionarioProdutos.service";
import { CORES } from "../../theme";
import { formatarMoeda } from "../../utils/format";
import {
  erroCadastroProduto, formatarCampoMonetarioProduto, valorMonetarioProduto,
} from "../../utils/produtoRapido";
import { FuncionarioPdvScanner } from "./pdv/FuncionarioPdvScanner";
import { novoProdutoStyles as styles } from "./produto/NovoProdutoStyles";
import { ProdutoRapidoFotos } from "./produto/ProdutoRapidoFotos";
import { useProdutoRapidoFotos } from "./produto/useProdutoRapidoFotos";
import { useSkuProdutoRapido } from "./produto/useSkuProdutoRapido";

const UNIDADES: { valor: ProdutoRapidoPayload["unidade"]; nome: string }[] = [
  { valor: "UN", nome: "Unidade" }, { valor: "KG", nome: "Quilo" },
  { valor: "CX", nome: "Caixa" }, { valor: "PC", nome: "Peça" }, { valor: "LT", nome: "Litro" },
];

export default function FuncionarioNovoProdutoScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const isFocused = useIsFocused();
  const insets = useSafeAreaInsets();
  const [scannerAberto, setScannerAberto] = useState(false);
  const [etapa, setEtapa] = useState<"codigo" | "formulario" | "existente" | "salvo">("codigo");
  const [codigo, setCodigo] = useState("");
  const [nome, setNome] = useState("");
  const [sku, setSku] = useState("");
  const [descricao, setDescricao] = useState("");
  const skuInfo = useSkuProdutoRapido(sku);
  const fotos = useProdutoRapidoFotos();
  const [preco, setPreco] = useState("");
  const [custo, setCusto] = useState("");
  const [unidade, setUnidade] = useState<ProdutoRapidoPayload["unidade"]>("UN");
  const [produto, setProduto] = useState<ProdutoRapido | null>(null);
  const [salvando, setOcupado] = useState(false);
  const ocupado = salvando || fotos.ocupado;
  const [erro, setErro] = useState("");
  const operacaoEmCurso = useRef(false);
  const montado = useRef(true);
  const navigation = useNavigation<any>();
  const descartarSaida = useRef(false);

  useEffect(() => {
    montado.current = true;
    return () => { montado.current = false; };
  }, []);

  useEffect(() => navigation.addListener("beforeRemove", (event: any) => {
    if (descartarSaida.current) return;
    if (ocupado) {
      event.preventDefault();
      Alert.alert("Aguarde", "Estamos concluindo a operação. Aguarde antes de sair.");
      return;
    }
    if (fotos.pendentes || (etapa === "formulario" && (nome || sku || descricao || preco || custo))) {
      event.preventDefault();
      Alert.alert("Há dados sem enviar", "Se sair agora, os dados e fotos pendentes desta tela serão descartados.", [
        { text: "Continuar aqui", style: "cancel" },
        { text: "Sair", style: "destructive", onPress: () => { descartarSaida.current = true; navigation.dispatch(event.data.action); } },
      ]);
    }
  }), [navigation, ocupado, fotos.pendentes, etapa, nome, sku, descricao, preco, custo]);

  async function consultar(valor: string) {
    if (operacaoEmCurso.current) return;
    const codigoLimpo = valor.trim();
    setScannerAberto(false);
    if (!codigoLimpo || codigoLimpo.length > 20 || !/^[A-Za-z0-9 ._/-]+$/.test(codigoLimpo)) {
      setErro("Informe um código de barras válido, com até 20 caracteres.");
      return;
    }
    operacaoEmCurso.current = true;
    setOcupado(true);
    setErro("");
    setCodigo(codigoLimpo);
    try {
      const encontrado = await consultarCodigoProdutoRapido(codigoLimpo);
      if (!montado.current) return;
      setProduto(encontrado);
      setEtapa(encontrado ? "existente" : "formulario");
    } catch (error) {
      if (montado.current) {
        setErro(erroCadastroProduto(error, "Não foi possível consultar o ERP. Confira sua conexão e tente novamente."));
      }
    } finally {
      operacaoEmCurso.current = false;
      if (montado.current) setOcupado(false);
    }
  }

  async function abrirScanner() {
    try {
      const permissao = permission?.granted ? permission : await requestPermission();
      if (!montado.current) return;
      if (!permissao.granted) {
        Alert.alert("Câmera desativada", "Você pode digitar o código ou permitir a câmera nas configurações.", [
          { text: "Digitar código", style: "cancel" },
          { text: "Configurações", onPress: () => { void Linking.openSettings(); } },
        ]);
        return;
      }
      setErro("");
      setScannerAberto(true);
    } catch {
      setErro("Não foi possível abrir a câmera. Digite o código de barras para continuar.");
    }
  }

  async function salvar() {
    if (operacaoEmCurso.current || fotos.ocupado) return;
    if (skuInfo.status === "ocupado") { setErro(skuInfo.mensagem); return; }
    const precoVenda = valorMonetarioProduto(preco);
    const precoCusto = valorMonetarioProduto(custo);
    if (!nome.trim() || precoVenda <= 0) {
      setErro("Preencha o nome e um preço de venda maior que zero.");
      return;
    }
    if (precoVenda > 99999999.99 || precoCusto > 99999999.99) {
      setErro("O valor máximo por campo é R$ 99.999.999,99.");
      return;
    }
    operacaoEmCurso.current = true;
    setOcupado(true);
    setErro("");
    try {
      const criado = await criarProdutoRapido({
        codigo_barras: codigo, nome: nome.trim(), preco_venda: precoVenda,
        preco_custo: precoCusto, unidade,
        codigo: sku.trim().toUpperCase() || undefined,
        descricao_curta: descricao.trim() || undefined,
      });
      if (!montado.current) return;
      setProduto(criado);
      setEtapa("salvo");
      await fotos.enviar(criado.id);
    } catch (error) {
      if (!montado.current) return;
      const resposta = (error as { response?: { status?: number; data?: { detail?: { produto?: ProdutoRapido; campo?: string } } } }).response;
      if (resposta?.status === 409 && resposta.data?.detail?.campo === "codigo") {
        setErro(erroCadastroProduto(error, "Este SKU já está em uso. Escolha outro ou deixe vazio."));
      } else if (resposta?.status === 409 && resposta.data?.detail?.produto) {
        setProduto(resposta.data.detail.produto);
        setEtapa("existente");
      } else {
        setErro(erroCadastroProduto(error, "Não foi possível confirmar o cadastro. Seus dados foram mantidos; confira a conexão e tente salvar novamente."));
      }
    } finally {
      operacaoEmCurso.current = false;
      if (montado.current) setOcupado(false);
    }
  }

  function limparFormulario() {
    setEtapa("codigo"); setCodigo(""); setNome(""); setPreco(""); setCusto("");
    setUnidade("UN"); setProduto(null); setErro(""); setSku(""); setDescricao(""); fotos.limpar();
  }

  function reiniciar() {
    if (ocupado) return;
    if (fotos.pendentes) {
      Alert.alert("Fotos pendentes", "Ainda há fotos sem enviar. Deseja descartá-las e começar outro cadastro?", [
        { text: "Voltar às fotos", style: "cancel" },
        { text: "Descartar fotos", style: "destructive", onPress: limparFormulario },
      ]);
      return;
    }
    limparFormulario();
  }

  return (
    <View style={styles.container}>
      <KeyboardSafeScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 32 }]}>
        <View style={styles.card}>
          <View style={styles.heading}>
            <Ionicons name="cube-outline" size={28} color={CORES.primario} />
            <Text style={styles.titulo}>Cadastro rápido</Text>
          </View>
          <Text style={styles.texto}>Cadastre o essencial agora e complete os detalhes em Produtos no ERP.</Text>
        </View>

        {etapa === "codigo" ? (
          <View style={styles.card}>
            <Text style={styles.subtitulo}>1. Leia o código de barras</Text>
            <TouchableOpacity accessibilityRole="button" style={[styles.primario, ocupado && styles.desabilitado]} disabled={ocupado} onPress={abrirScanner}>
              <Ionicons name="scan-outline" size={22} color="#fff" />
              <Text style={styles.primarioTexto}>Ler código de barras</Text>
            </TouchableOpacity>
            <Text style={styles.label}>Ou digite o código</Text>
            <TextInput
              accessibilityLabel="Código de barras" style={styles.input} value={codigo}
              onChangeText={(valor) => { setCodigo(valor); setErro(""); }} maxLength={20}
              placeholder="Ex.: 7891234567890" placeholderTextColor={CORES.textoClaro}
              autoCapitalize="none" autoCorrect={false} editable={!ocupado}
              returnKeyType="search" onSubmitEditing={() => consultar(codigo)}
            />
            <TouchableOpacity accessibilityRole="button" style={[styles.secundario, (ocupado || !codigo.trim()) && styles.desabilitado]} disabled={ocupado || !codigo.trim()} onPress={() => consultar(codigo)}>
              <Text style={styles.secundarioTexto}>Consultar código</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {etapa === "formulario" ? (
          <View style={styles.card}>
            <Text style={styles.subtitulo}>2. Preencha os dados essenciais</Text>
            <View style={styles.aviso}>
              <Text style={styles.avisoTexto}>Código {codigo} ainda não cadastrado.</Text>
            </View>
            <TouchableOpacity accessibilityRole="button" disabled={ocupado} onPress={() => { setEtapa("codigo"); setErro(""); }}>
              <Text style={styles.secundarioTexto}>Corrigir código</Text>
            </TouchableOpacity>
            <Text style={styles.label}>Nome do produto *</Text>
            <TextInput
              accessibilityLabel="Nome do produto" style={styles.input} value={nome} onChangeText={setNome}
              maxLength={200} editable={!ocupado} placeholder="Ex.: Ração para cães adultos 10 kg"
              placeholderTextColor={CORES.textoClaro} autoCapitalize="sentences"
            />
            <Text style={styles.label}>SKU / código interno · opcional</Text>
            <TextInput
              accessibilityLabel="SKU do produto" style={styles.input} value={sku}
              onChangeText={(valor) => { setSku(valor); setErro(""); }} editable={!ocupado}
              maxLength={50} autoCapitalize="characters" autoCorrect={false}
              placeholder="Gerado automaticamente se ficar vazio" placeholderTextColor={CORES.textoClaro}
            />
            <Text accessibilityLiveRegion="polite" style={skuInfo.status === "ocupado" ? styles.erro : styles.texto}>{skuInfo.mensagem}</Text>
            <Text style={styles.label}>Descrição · opcional</Text>
            <TextInput
              accessibilityLabel="Descrição do produto" style={[styles.input, styles.descricao]} value={descricao}
              onChangeText={setDescricao} editable={!ocupado} maxLength={1000} multiline
              placeholder="Ex.: sabor, tamanho, indicação de uso..." placeholderTextColor={CORES.textoClaro}
            />
            <Text style={styles.label}>Preço de venda (R$) *</Text>
            <TextInput
              accessibilityLabel="Preço de venda" style={styles.input} value={preco}
              onChangeText={(valor) => setPreco(formatarCampoMonetarioProduto(valor))}
              keyboardType="number-pad" maxLength={15} placeholder="0,00"
              placeholderTextColor={CORES.textoClaro} editable={!ocupado} selectTextOnFocus
            />
            <Text style={styles.label}>Preço de custo (R$) · opcional</Text>
            <TextInput
              accessibilityLabel="Preço de custo" style={styles.input} value={custo}
              onChangeText={(valor) => setCusto(formatarCampoMonetarioProduto(valor))}
              keyboardType="number-pad" maxLength={15} placeholder="0,00"
              placeholderTextColor={CORES.textoClaro} editable={!ocupado} selectTextOnFocus
            />
            <Text style={styles.label}>Unidade de venda</Text>
            <View style={styles.unidades}>
              {UNIDADES.map((item) => (
                <TouchableOpacity
                  key={item.valor} accessibilityRole="radio" accessibilityState={{ checked: unidade === item.valor }}
                  style={[styles.unidade, unidade === item.valor && styles.unidadeAtiva]}
                  disabled={ocupado} onPress={() => setUnidade(item.valor)}
                >
                  <Text style={unidade === item.valor ? styles.unidadeTextoAtivo : styles.texto}>{item.nome}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <ProdutoRapidoFotos fotos={fotos.fotos} ocupado={ocupado} salvo={false} adicionar={fotos.adicionar} remover={fotos.remover} />
            <Text style={styles.texto}>O estoque começa em zero. Depois, registre o saldo em Balanço de estoque. Categoria e dados fiscais podem ser preenchidos no ERP.</Text>
            <TouchableOpacity accessibilityRole="button" style={[styles.primario, (ocupado || skuInfo.status === "ocupado") && styles.desabilitado]} disabled={ocupado || skuInfo.status === "ocupado"} onPress={salvar}>
              <Text style={styles.primarioTexto}>{ocupado ? "Salvando..." : "Cadastrar produto"}</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {(etapa === "salvo" || etapa === "existente") && produto ? (
          <View style={styles.card}>
            <Ionicons name={etapa === "salvo" ? "checkmark-circle-outline" : "information-circle-outline"} size={42} color={CORES.primario} />
            <Text style={styles.titulo}>{etapa === "salvo" ? "Produto cadastrado!" : "Este produto já existe"}</Text>
            <Text style={styles.subtitulo}>{produto.nome}</Text>
            <Text style={styles.texto}>Código interno: {produto.codigo}</Text>
            <Text style={styles.texto}>Código de barras: {produto.codigo_barras || codigo}</Text>
            <Text style={styles.preco}>{formatarMoeda(produto.preco_venda)} / {produto.unidade}</Text>
            {produto.descricao_curta ? <Text style={styles.texto}>{produto.descricao_curta}</Text> : null}
            {etapa === "salvo" && fotos.fotos.length > 0 ? <>
              <ProdutoRapidoFotos fotos={fotos.fotos} ocupado={ocupado} salvo adicionar={fotos.adicionar} remover={fotos.remover} />
              {fotos.pendentes ? <TouchableOpacity accessibilityRole="button" style={[styles.secundario, ocupado && styles.desabilitado]} disabled={ocupado} onPress={() => fotos.enviar(produto.id)}>
                <Text style={styles.secundarioTexto}>{ocupado ? "Enviando fotos..." : "Tentar enviar fotos novamente"}</Text>
              </TouchableOpacity> : <Text style={styles.texto}>Fotos salvas na galeria do produto no ERP.</Text>}
            </> : null}
            {!produto.ativo || produto.situacao === false ? (
              <Text style={styles.erro}>Produto inativo. Revise o cadastro no ERP para reativá-lo.</Text>
            ) : null}
            <Text style={styles.texto}>
              {etapa === "salvo"
                ? "Já está salvo em Produtos no ERP. Complete os detalhes por lá e escolha quando anunciar no app e na loja online."
                : "O cadastro existente foi preservado. Você pode localizar este produto pelo código interno no ERP."}
            </Text>
            <TouchableOpacity accessibilityRole="button" style={styles.primario} disabled={ocupado} onPress={reiniciar}>
              <Text style={styles.primarioTexto}>Cadastrar outro produto</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {ocupado ? <View style={styles.heading}><ActivityIndicator color={CORES.primario} /><Text style={styles.texto}>{etapa === "codigo" ? "Consultando o ERP..." : "Aguarde..."}</Text></View> : null}
        {erro ? <Text accessibilityRole="alert" accessibilityLiveRegion="polite" style={styles.erro}>{erro}</Text> : null}
        {fotos.erro ? <Text accessibilityRole="alert" accessibilityLiveRegion="polite" style={styles.erro}>{fotos.erro}</Text> : null}
      </KeyboardSafeScrollView>

      <Modal visible={scannerAberto && isFocused} animationType="slide" onRequestClose={() => setScannerAberto(false)}>
        <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
          {scannerAberto && isFocused ? (
            <FuncionarioPdvScanner
              scanAtivo={!ocupado} buscandoProduto={ocupado}
              onBarcodeScanned={({ data }) => consultar(data)} onClose={() => setScannerAberto(false)}
              onResetScan={() => {}}
            />
          ) : null}
        </View>
      </Modal>
    </View>
  );
}
