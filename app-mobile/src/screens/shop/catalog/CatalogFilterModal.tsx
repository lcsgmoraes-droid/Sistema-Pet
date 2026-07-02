import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  Modal,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { CORES, ESPACO } from "../../../theme";
import { catalogStyles as styles } from "./CatalogStyles";
import {
  CatalogoFiltros,
  ESPECIE_OPTIONS,
  formatarPesoEmbalagemFiltro,
  ORDER_OPTIONS,
} from "./CatalogUtils";
import { CatalogOrder } from "../../../services/shop.service";

interface CatalogFilterModalProps {
  visible: boolean;
  insetsBottom: number;
  filtros: CatalogoFiltros;
  ordenacao: CatalogOrder;
  buscaMarca: string;
  marcasFiltradas: string[];
  pesosEmbalagemDisponiveis: number[];
  onClose: () => void;
  onLimparFiltros: () => void;
  onSetBuscaMarca: (value: string) => void;
  onSelecionarFiltro: <K extends keyof CatalogoFiltros>(
    campo: K,
    valor: CatalogoFiltros[K],
  ) => void;
  onSelecionarPesoEmbalagem: (peso: number | null) => void;
  onSetOrdenacao: (value: CatalogOrder) => void;
}

export function CatalogFilterModal({
  visible,
  insetsBottom,
  filtros,
  ordenacao,
  buscaMarca,
  marcasFiltradas,
  pesosEmbalagemDisponiveis,
  onClose,
  onLimparFiltros,
  onSetBuscaMarca,
  onSelecionarFiltro,
  onSelecionarPesoEmbalagem,
  onSetOrdenacao,
}: CatalogFilterModalProps) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.modalBackdrop}>
        <View style={styles.modalCard}>
          <View style={styles.modalHeader}>
            <View>
              <Text style={styles.modalTitulo}>Filtros</Text>
              <Text style={styles.modalSubtitulo}>
                Encontre produtos por pet, pacote e marca.
              </Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.modalFechar}>
              <Ionicons name="close" size={22} color={CORES.texto} />
            </TouchableOpacity>
          </View>

          <ScrollView
            style={styles.modalScroll}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={[
              styles.modalConteudo,
              { paddingBottom: 120 + insetsBottom },
            ]}
          >
            <FiltroSecao titulo="Especie">
              {ESPECIE_OPTIONS.map((item) => (
                <OpcaoFiltro
                  key={item.value}
                  label={item.label}
                  selecionado={filtros.especie === item.value}
                  onPress={() => onSelecionarFiltro("especie", item.value)}
                />
              ))}
            </FiltroSecao>

            <FiltroSecao titulo="Peso da embalagem">
              <OpcaoFiltro
                label="Todos"
                selecionado={filtros.pesoEmbalagem === null}
                onPress={() => onSelecionarPesoEmbalagem(null)}
              />
              {pesosEmbalagemDisponiveis.map((peso) => (
                <OpcaoFiltro
                  key={String(peso)}
                  label={formatarPesoEmbalagemFiltro(peso)}
                  selecionado={filtros.pesoEmbalagem === peso}
                  onPress={() => onSelecionarPesoEmbalagem(peso)}
                />
              ))}
              {pesosEmbalagemDisponiveis.length === 0 && (
                <Text style={styles.filtroVazioTexto}>
                  Nenhum peso cadastrado.
                </Text>
              )}
            </FiltroSecao>

            <FiltroSecao titulo="Marca">
              <View style={styles.marcaBuscaContainer}>
                <Ionicons
                  name="search-outline"
                  size={16}
                  color={CORES.textoClaro}
                />
                <TextInput
                  style={styles.marcaBuscaInput}
                  placeholder="Buscar marca"
                  placeholderTextColor={CORES.textoClaro}
                  value={buscaMarca}
                  onChangeText={onSetBuscaMarca}
                  returnKeyType="search"
                />
                {buscaMarca.length > 0 && (
                  <TouchableOpacity onPress={() => onSetBuscaMarca("")}>
                    <Ionicons
                      name="close-circle"
                      size={18}
                      color={CORES.textoClaro}
                    />
                  </TouchableOpacity>
                )}
              </View>
              <OpcaoFiltro
                label="Todas"
                selecionado={!filtros.marca}
                onPress={() => {
                  onSelecionarFiltro("marca", "");
                  onSetBuscaMarca("");
                }}
              />
              {filtros.marca ? (
                <Text style={styles.marcaSelecionadaTexto}>
                  Selecionada: {filtros.marca}
                </Text>
              ) : null}
              {marcasFiltradas.map((marca) => (
                <OpcaoFiltro
                  key={marca}
                  label={marca}
                  selecionado={filtros.marca === marca}
                  onPress={() => {
                    onSelecionarFiltro("marca", marca);
                    onSetBuscaMarca(marca);
                  }}
                />
              ))}
              {marcasFiltradas.length === 0 && (
                <Text style={styles.filtroVazioTexto}>
                  Nenhuma marca encontrada.
                </Text>
              )}
            </FiltroSecao>

            <FiltroSecao titulo="Ordenar por">
              {ORDER_OPTIONS.map((item) => (
                <OpcaoFiltro
                  key={item.value}
                  label={item.label}
                  selecionado={ordenacao === item.value}
                  onPress={() => onSetOrdenacao(item.value)}
                />
              ))}
            </FiltroSecao>
          </ScrollView>

          <View
            style={[
              styles.modalAcoes,
              { paddingBottom: Math.max(ESPACO.xl, insetsBottom + ESPACO.md) },
            ]}
          >
            <TouchableOpacity
              style={styles.botaoLimpar}
              onPress={onLimparFiltros}
            >
              <Text style={styles.botaoLimparTexto}>Limpar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.botaoAplicar} onPress={onClose}>
              <Text style={styles.botaoAplicarTexto}>Aplicar filtros</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function FiltroSecao({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.filtroSecao}>
      <Text style={styles.filtroSecaoTitulo}>{titulo}</Text>
      <View style={styles.filtroOpcoes}>{children}</View>
    </View>
  );
}

function OpcaoFiltro({
  label,
  selecionado,
  onPress,
}: {
  label: string;
  selecionado: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.filtroChip, selecionado && styles.filtroChipAtivo]}
      onPress={onPress}
    >
      <Text
        style={[
          styles.filtroChipTexto,
          selecionado && styles.filtroChipTextoAtivo,
        ]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );
}
