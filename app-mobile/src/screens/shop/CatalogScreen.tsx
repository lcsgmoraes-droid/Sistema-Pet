import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  CatalogOrder,
  listarOpcoesFiltrosCatalogo,
  listarProdutos,
  registrarAviseme,
} from "../../services/shop.service";
import { useCartStore } from "../../store/cart.store";
import { useWishlistStore } from "../../store/wishlist.store";
import { useAuthStore } from "../../store/auth.store";
import { Produto } from "../../types";
import { CatalogContent } from "./catalog/CatalogContent";
import {
  aplicarFiltrosCatalogo,
  CatalogoFiltros,
  FILTROS_PADRAO,
  normalizarTexto,
  ORDER_OPTIONS,
} from "./catalog/CatalogUtils";

export default function CatalogScreen() {
  const navigation = useNavigation<any>();
  const insets = useSafeAreaInsets();
  const { adicionar, totalItens } = useCartStore();
  const {
    ids: wishlistIds,
    carregar: carregarWishlist,
    toggle: toggleWishlist,
  } = useWishlistStore();
  const { user } = useAuthStore();
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [busca, setBusca] = useState("");
  const [buscaMarca, setBuscaMarca] = useState("");
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [modalFiltrosVisivel, setModalFiltrosVisivel] = useState(false);
  const [filtros, setFiltros] = useState<CatalogoFiltros>(FILTROS_PADRAO);
  const [ordenacao, setOrdenacao] = useState<CatalogOrder>("prontos");
  const [marcasDisponiveis, setMarcasDisponiveis] = useState<string[]>([]);
  const [pesosEmbalagemDisponiveis, setPesosEmbalagemDisponiveis] = useState<
    number[]
  >([]);

  const ordenacaoLabel = useMemo(
    () =>
      ORDER_OPTIONS.find((item) => item.value === ordenacao)?.label ??
      "Relevancia",
    [ordenacao],
  );

  const marcasFiltradas = useMemo(() => {
    const termo = normalizarTexto(buscaMarca);
    return marcasDisponiveis
      .filter((marca) => !termo || normalizarTexto(marca).includes(termo))
      .slice(0, 8);
  }, [buscaMarca, marcasDisponiveis]);

  const produtosFiltrados = useMemo(
    () =>
      produtos.filter((produto) => aplicarFiltrosCatalogo(produto, filtros)),
    [filtros, produtos],
  );

  const filtrosAtivos = useMemo(
    () =>
      Number(filtros.especie !== FILTROS_PADRAO.especie) +
      Number(filtros.pesoEmbalagem !== FILTROS_PADRAO.pesoEmbalagem) +
      Number(!!filtros.marca),
    [filtros],
  );

  const carregar = useCallback(
    async (pg: number, q: string) => {
      if (pg === 1) setCarregando(true);

      try {
        const produtosPromise = listarProdutos({
          pagina: pg,
          busca: q || undefined,
          ordenacao,
          cacheBust: pg === 1 ? Date.now() : undefined,
          limit: filtrosAtivos > 0 ? 500 : undefined,
          marca: filtros.marca || undefined,
          pesoEmbalagemKg: filtros.pesoEmbalagem ?? undefined,
        });
        const opcoesPromise =
          pg === 1
            ? listarOpcoesFiltrosCatalogo({ busca: q || undefined, ordenacao })
            : Promise.resolve(null);
        const [{ produtos: novos, total: totalRecebido }, opcoes] =
          await Promise.all([produtosPromise, opcoesPromise]);

        if (pg === 1) {
          setProdutos(novos);
          if (opcoes) {
            setMarcasDisponiveis(opcoes.marcas);
            setPesosEmbalagemDisponiveis(opcoes.pesos_embalagem_kg);
          }
        } else {
          setProdutos((prev) => [...prev, ...novos]);
        }

        setTotal(totalRecebido);
        setPagina(pg);
      } catch {
        if (pg === 1) {
          setProdutos([]);
          setTotal(0);
        }
      } finally {
        setCarregando(false);
      }
    },
    [filtros.marca, filtros.pesoEmbalagem, filtrosAtivos, ordenacao],
  );

  useEffect(() => {
    carregarWishlist();
  }, []);

  useEffect(() => {
    carregar(1, busca);
  }, [carregar]);

  async function onRefresh() {
    setRefreshing(true);
    await carregar(1, busca);
    setRefreshing(false);
  }

  function onBusca(texto: string) {
    setBusca(texto);
    if (texto.length === 0 || texto.length >= 2) {
      carregar(1, texto);
    }
  }

  function carregarMais() {
    if (!carregando && produtos.length < total) {
      carregar(pagina + 1, busca);
    }
  }

  function limparFiltros() {
    setFiltros(FILTROS_PADRAO);
    setBuscaMarca("");
  }

  function selecionarFiltro<K extends keyof CatalogoFiltros>(
    campo: K,
    valor: CatalogoFiltros[K],
  ) {
    setFiltros((atuais) => ({ ...atuais, [campo]: valor }));
  }

  function selecionarPesoEmbalagem(peso: number | null) {
    setFiltros((atuais) => ({ ...atuais, pesoEmbalagem: peso }));
  }

  async function adicionarAoCarrinho(produto: Produto) {
    try {
      await adicionar(produto, 1);
    } catch {
      Alert.alert("Erro", "Nao foi possivel adicionar ao carrinho.");
    }
  }

  async function registrarAvisoProduto(produto: Produto) {
    if (!user?.email) {
      Alert.alert(
        "Entre na sua conta",
        "Para receber o aviso quando o produto voltar ao estoque, faca login primeiro.",
        [{ text: "OK" }],
      );
      return;
    }

    try {
      const res = await registrarAviseme(user.email, produto.id, produto.nome);
      Alert.alert(
        "Tudo certo",
        res.message || "Voc? ser? avisado por e-mail quando o produto voltar.",
      );
    } catch {
      Alert.alert(
        "Erro",
        "Nao foi possivel registrar o aviso. Tente novamente.",
      );
    }
  }

  return (
    <CatalogContent
      busca={busca}
      onBusca={onBusca}
      filtrosAtivos={filtrosAtivos}
      totalCarrinho={totalItens()}
      ordenacaoLabel={ordenacaoLabel}
      produtos={produtos}
      produtosFiltrados={produtosFiltrados}
      total={total}
      pagina={pagina}
      carregando={carregando}
      refreshing={refreshing}
      wishlistIds={wishlistIds}
      userEmail={user?.email}
      modalFiltrosVisivel={modalFiltrosVisivel}
      insetsBottom={insets.bottom}
      filtros={filtros}
      ordenacao={ordenacao}
      buscaMarca={buscaMarca}
      marcasFiltradas={marcasFiltradas}
      pesosEmbalagemDisponiveis={pesosEmbalagemDisponiveis}
      onNavigateScanner={() => navigation.navigate("BarcodeScanner")}
      onNavigateCart={() => navigation.navigate("Carrinho")}
      onOpenProduct={(produto) =>
        navigation.navigate("DetalhesProduto", { produto })
      }
      onToggleWishlist={toggleWishlist}
      onAddToCart={adicionarAoCarrinho}
      onRegisterAviseme={registrarAvisoProduto}
      onRefresh={onRefresh}
      onCarregarMais={carregarMais}
      onAbrirFiltros={() => setModalFiltrosVisivel(true)}
      onFecharFiltros={() => setModalFiltrosVisivel(false)}
      onLimparFiltros={limparFiltros}
      onSetBuscaMarca={setBuscaMarca}
      onSelecionarFiltro={selecionarFiltro}
      onSelecionarPesoEmbalagem={selecionarPesoEmbalagem}
      onSetOrdenacao={setOrdenacao}
    />
  );
}
