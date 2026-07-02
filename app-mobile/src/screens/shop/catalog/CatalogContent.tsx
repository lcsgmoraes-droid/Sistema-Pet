import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { CatalogOrder } from "../../../services/shop.service";
import { CORES } from "../../../theme";
import { Produto } from "../../../types";
import { CatalogFilterModal } from "./CatalogFilterModal";
import { CatalogProductCard } from "./CatalogProductCard";
import { catalogStyles as styles } from "./CatalogStyles";
import { CatalogoFiltros } from "./CatalogUtils";

interface CatalogContentProps {
  busca: string;
  onBusca: (texto: string) => void;
  filtrosAtivos: number;
  totalCarrinho: number;
  ordenacaoLabel: string;
  produtos: Produto[];
  produtosFiltrados: Produto[];
  total: number;
  pagina: number;
  carregando: boolean;
  refreshing: boolean;
  wishlistIds: number[];
  userEmail?: string | null;
  modalFiltrosVisivel: boolean;
  insetsBottom: number;
  filtros: CatalogoFiltros;
  ordenacao: CatalogOrder;
  buscaMarca: string;
  marcasFiltradas: string[];
  pesosEmbalagemDisponiveis: number[];
  onNavigateScanner: () => void;
  onNavigateCart: () => void;
  onOpenProduct: (produto: Produto) => void;
  onToggleWishlist: (produtoId: number) => void;
  onAddToCart: (produto: Produto) => void;
  onRegisterAviseme: (produto: Produto) => void;
  onRefresh: () => void;
  onCarregarMais: () => void;
  onAbrirFiltros: () => void;
  onFecharFiltros: () => void;
  onLimparFiltros: () => void;
  onSetBuscaMarca: (value: string) => void;
  onSelecionarFiltro: <K extends keyof CatalogoFiltros>(
    campo: K,
    valor: CatalogoFiltros[K],
  ) => void;
  onSelecionarPesoEmbalagem: (peso: number | null) => void;
  onSetOrdenacao: (value: CatalogOrder) => void;
}

export function CatalogContent({
  busca,
  onBusca,
  filtrosAtivos,
  totalCarrinho,
  ordenacaoLabel,
  produtos,
  produtosFiltrados,
  total,
  pagina,
  carregando,
  refreshing,
  wishlistIds,
  userEmail,
  modalFiltrosVisivel,
  insetsBottom,
  filtros,
  ordenacao,
  buscaMarca,
  marcasFiltradas,
  pesosEmbalagemDisponiveis,
  onNavigateScanner,
  onNavigateCart,
  onOpenProduct,
  onToggleWishlist,
  onAddToCart,
  onRegisterAviseme,
  onRefresh,
  onCarregarMais,
  onAbrirFiltros,
  onFecharFiltros,
  onLimparFiltros,
  onSetBuscaMarca,
  onSelecionarFiltro,
  onSelecionarPesoEmbalagem,
  onSetOrdenacao,
}: CatalogContentProps) {
  return (
    <View style={styles.container}>
      <View style={styles.buscaRow}>
        <View style={styles.buscaContainer}>
          <Ionicons
            name="search-outline"
            size={18}
            color={CORES.textoClaro}
            style={{ marginRight: 6 }}
          />
          <TextInput
            style={styles.buscaInput}
            placeholder="Buscar produtos..."
            placeholderTextColor={CORES.textoClaro}
            value={busca}
            onChangeText={onBusca}
            returnKeyType="search"
          />
          {busca.length > 0 && (
            <TouchableOpacity onPress={() => onBusca("")}>
              <Ionicons
                name="close-circle"
                size={18}
                color={CORES.textoClaro}
              />
            </TouchableOpacity>
          )}
        </View>

        <ToolbarButton icon="barcode-outline" onPress={onNavigateScanner} />
        <ToolbarButton
          icon="funnel-outline"
          onPress={onAbrirFiltros}
          active={filtrosAtivos > 0}
          badge={filtrosAtivos > 0 ? filtrosAtivos : undefined}
        />
        <ToolbarButton
          icon="cart-outline"
          onPress={onNavigateCart}
          primary
          badge={totalCarrinho || undefined}
        />
      </View>

      <View style={styles.resumoContainer}>
        <Text style={styles.resumoCatalogo}>
          {filtrosAtivos > 0
            ? `${produtosFiltrados.length} produto(s) filtrado(s)`
            : `Mostrando ${produtos.length} de ${total || produtos.length} produtos`}
        </Text>
        <Text style={styles.ordenacaoResumo}>{ordenacaoLabel}</Text>
      </View>

      {carregando && pagina === 1 ? (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={CORES.primario} />
        </View>
      ) : (
        <FlatList
          data={produtosFiltrados}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <CatalogProductCard
              item={item}
              naWishlist={wishlistIds.includes(item.id)}
              userEmail={userEmail}
              onOpenProduct={onOpenProduct}
              onToggleWishlist={onToggleWishlist}
              onAddToCart={onAddToCart}
              onRegisterAviseme={onRegisterAviseme}
            />
          )}
          numColumns={2}
          columnWrapperStyle={styles.colunaPar}
          contentContainerStyle={styles.lista}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={CORES.primario}
            />
          }
          onEndReached={onCarregarMais}
          onEndReachedThreshold={0.5}
          ListEmptyComponent={<CatalogEmptyState />}
        />
      )}

      <CatalogFilterModal
        visible={modalFiltrosVisivel}
        insetsBottom={insetsBottom}
        filtros={filtros}
        ordenacao={ordenacao}
        buscaMarca={buscaMarca}
        marcasFiltradas={marcasFiltradas}
        pesosEmbalagemDisponiveis={pesosEmbalagemDisponiveis}
        onClose={onFecharFiltros}
        onLimparFiltros={onLimparFiltros}
        onSetBuscaMarca={onSetBuscaMarca}
        onSelecionarFiltro={onSelecionarFiltro}
        onSelecionarPesoEmbalagem={onSelecionarPesoEmbalagem}
        onSetOrdenacao={onSetOrdenacao}
      />
    </View>
  );
}

function ToolbarButton({
  icon,
  onPress,
  active,
  primary,
  badge,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  active?: boolean;
  primary?: boolean;
  badge?: number;
}) {
  const isFilled = active || primary;
  return (
    <TouchableOpacity
      style={[
        styles.botaoScanner,
        active && styles.botaoFiltroAtivo,
        primary && { backgroundColor: CORES.primario },
      ]}
      onPress={onPress}
    >
      <Ionicons
        name={icon}
        size={22}
        color={isFilled ? "#fff" : CORES.primario}
      />
      {badge ? (
        <View style={styles.badge}>
          <Text style={styles.badgeNum}>{badge}</Text>
        </View>
      ) : null}
    </TouchableOpacity>
  );
}

function CatalogEmptyState() {
  return (
    <View style={styles.vazio}>
      <Ionicons name="search-outline" size={36} color={CORES.textoClaro} />
      <Text style={styles.vazioTexto}>Nenhum produto encontrado.</Text>
      <Text style={styles.vazioSubtexto}>
        Tente buscar com outro termo ou ajustar os filtros.
      </Text>
    </View>
  );
}
