import { Ionicons } from "@expo/vector-icons";
import React, { type Dispatch, type SetStateAction } from "react";
import { FlatList, Image, Modal, Text, TextInput, TouchableOpacity, View } from "react-native";

import type { RacaoCadastrada } from "../../../services/shop.service";
import { CORES, ESPACO } from "../../../theme";
import type { Pet } from "../../../types";
import { calcularIdadeMeses, formatarMoeda } from "../../../utils/format";
import { foodCalculatorStyles as styles } from "./FoodCalculatorStyles";
import type { FoodCalculatorSelectorKind } from "./FoodCalculatorUtils";

export type FoodCalculatorSelectorModalProps = {
  seletorAberto: FoodCalculatorSelectorKind;
  setSeletorAberto: Dispatch<SetStateAction<FoodCalculatorSelectorKind>>;
  pets: Pet[];
  setPetSelecionado: Dispatch<SetStateAction<Pet | null>>;
  setPesoPet: Dispatch<SetStateAction<string>>;
  setIdadeMeses: Dispatch<SetStateAction<string>>;
  racoes: RacaoCadastrada[];
  racoesFiltradas: RacaoCadastrada[];
  buscaRacao: string;
  setBuscaRacao: Dispatch<SetStateAction<string>>;
  selecionarRacao: (racao: RacaoCadastrada) => void;
};

export function FoodCalculatorSelectorModal({
  seletorAberto,
  setSeletorAberto,
  pets,
  setPetSelecionado,
  setPesoPet,
  setIdadeMeses,
  racoes,
  racoesFiltradas,
  buscaRacao,
  setBuscaRacao,
  selecionarRacao,
}: FoodCalculatorSelectorModalProps) {
  return (
    <>
      {/* Modal seletor de ração / pet */}
      <Modal
        visible={seletorAberto !== null}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSeletorAberto(null)}
      >
        <View style={styles.modal}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitulo}>
              {seletorAberto === 'pet' ? 'Selecionar pet' : seletorAberto === 'principal' ? 'Selecionar ração' : 'Selecionar para comparar'}
            </Text>
            <TouchableOpacity onPress={() => setSeletorAberto(null)}>
              <Ionicons name="close" size={24} color={CORES.texto} />
            </TouchableOpacity>
          </View>

          {/* Lista de pets */}
          {seletorAberto === 'pet' && (
            pets.length === 0 ? (
              <View style={styles.modalVazio}>
                <Text style={{ fontSize: 40 }}>🐾</Text>
                <Text style={styles.modalVazioTexto}>Nenhum pet cadastrado.</Text>
                <Text style={styles.modalVazioSub}>Vá em Pets e adicione seu pet com peso e idade.</Text>
              </View>
            ) : (
              <FlatList
                data={pets}
                keyExtractor={(p) => String(p.id)}
                contentContainerStyle={{ padding: ESPACO.md }}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.racaoItem}
                    onPress={() => {
                      setPetSelecionado(item);
                      if (item.peso) setPesoPet(String(item.peso));
                      // Usa idade_aproximada; se ausente, calcula a partir da data_nascimento
                      if (item.idade_aproximada) {
                        setIdadeMeses(String(item.idade_aproximada));
                      } else {
                        const calc = calcularIdadeMeses(item.data_nascimento);
                        setIdadeMeses(calc ? String(calc) : '');
                      }
                      setSeletorAberto(null);
                    }}
                  >
                    {item.foto_url ? (
                      <Image source={{ uri: item.foto_url }} style={styles.racaoFoto} resizeMode="cover" />
                    ) : (
                      <View style={[styles.racaoFoto, styles.racaoFotoPlaceholder]}>
                        <Text style={{ fontSize: 22 }}>🐾</Text>
                      </View>
                    )}
                    <View style={{ flex: 1 }}>
                      <Text style={styles.racaoNome}>{item.nome}</Text>
                      <Text style={styles.racaoSub}>
                        {item.especie ?? ''}
                        {item.peso ? ` · ${item.peso}kg` : ''}
                        {item.idade_aproximada
                          ? ` · ${item.idade_aproximada} meses`
                          : calcularIdadeMeses(item.data_nascimento)
                          ? ` · ${calcularIdadeMeses(item.data_nascimento)} meses`
                          : ''}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
                  </TouchableOpacity>
                )}
              />
            )
          )}
          {/* Lista de rações */}
          {seletorAberto !== 'pet' && (
          racoes.length === 0 ? (
            <View style={styles.modalVazio}>
              <Text style={{ fontSize: 40 }}>🥫</Text>
              <Text style={styles.modalVazioTexto}>
                Nenhuma ração com peso de embalagem cadastrado.
              </Text>
              <Text style={styles.modalVazioSub}>
                Vá ao sistema ERP → Produtos → aba Ração e preencha o campo "Peso da Embalagem (kg)".
              </Text>
            </View>
          ) : (
            <>
            <View style={styles.buscaRacaoBox}>
              <Ionicons name="search-outline" size={18} color={CORES.textoClaro} />
              <TextInput
                style={styles.buscaRacaoInput}
                value={buscaRacao}
                onChangeText={setBuscaRacao}
                placeholder="Digite o nome da racao..."
                placeholderTextColor={CORES.textoClaro}
                autoCapitalize="none"
              />
              {buscaRacao ? (
                <TouchableOpacity onPress={() => setBuscaRacao('')}>
                  <Ionicons name="close-circle" size={18} color={CORES.textoClaro} />
                </TouchableOpacity>
              ) : null}
            </View>
            <FlatList
              data={racoesFiltradas}
              keyExtractor={(r) => String(r.id)}
              contentContainerStyle={{ padding: ESPACO.md }}
              ListEmptyComponent={
                <View style={styles.modalVazio}>
                  <Text style={styles.modalVazioTexto}>Nenhuma racao encontrada.</Text>
                  <Text style={styles.modalVazioSub}>Tente buscar por outro trecho do nome.</Text>
                </View>
              }
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.racaoItem}
                  onPress={() => selecionarRacao(item)}
                >
                  {item.foto_url ? (
                    <Image source={{ uri: item.foto_url }} style={styles.racaoFoto} resizeMode="contain" />
                  ) : (
                    <View style={[styles.racaoFoto, styles.racaoFotoPlaceholder]}>
                      <Text style={{ fontSize: 22 }}>🥫</Text>
                    </View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={styles.racaoNome}>{item.nome}</Text>
                    <Text style={styles.racaoSub}>
                      Embalagem: {item.peso_embalagem}kg
                      {item.classificacao_racao ? ` · ${item.classificacao_racao}` : ''}
                    </Text>
                    <Text style={styles.racaoPreco}>{formatarMoeda(item.preco)}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={CORES.textoClaro} />
                </TouchableOpacity>
              )}
            />
            </>
          )
          )}
        </View>
      </Modal>
    </>
  );
}
