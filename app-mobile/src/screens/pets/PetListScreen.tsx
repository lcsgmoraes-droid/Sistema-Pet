import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  RefreshControl,
  Alert,
} from 'react-native';
import { useFocusEffect, useNavigation, useRoute } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { listarPets, deletarPet } from '../../services/pets.service';
import { Pet, VetFocusSection } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { calcularIdade } from '../../utils/format';

function getFocusLabel(section?: VetFocusSection) {
  if (section === 'vacinas') return 'carteirinha de vacinas';
  if (section === 'exames') return 'exames e resultados';
  if (section === 'consultas') return 'consultas veterinarias';
  return 'saude veterinaria';
}

export default function PetListScreen() {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const [pets, setPets] = useState<Pet[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const focusSection = route.params?.focusSection as VetFocusSection | undefined;

  useFocusEffect(
    useCallback(() => {
      carregar();
    }, [])
  );

  async function carregar() {
    setRefreshing(true);
    try {
      const lista = await listarPets();
      setPets(lista);
    } catch {
      Alert.alert('Erro', 'Nao foi possivel carregar seus pets.');
    } finally {
      setRefreshing(false);
    }
  }

  function confirmarExcluir(pet: Pet) {
    Alert.alert(
      'Excluir pet',
      `Deseja excluir ${pet.nome}? Esta acao nao pode ser desfeita.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Excluir',
          style: 'destructive',
          onPress: async () => {
            try {
              await deletarPet(pet.id);
              setPets((prev) => prev.filter((p) => p.id !== pet.id));
            } catch {
              Alert.alert('Erro', 'Nao foi possivel excluir o pet.');
            }
          },
        },
      ]
    );
  }

  function abrirDetalhe(item: Pet) {
    navigation.navigate('DetalhePet', { pet: item, focusSection });
  }

  function renderPet({ item }: { item: Pet }) {
    const emojiEspecie =
      item.especie === 'gato' ? '🐱' : item.especie === 'cão' ? '🐶' : '🐾';

    return (
      <TouchableOpacity style={styles.card} onPress={() => abrirDetalhe(item)}>
        {item.foto_url ? (
          <Image source={{ uri: item.foto_url }} style={styles.foto} />
        ) : (
          <View style={[styles.foto, styles.fotoPlaceholder]}>
            <Text style={{ fontSize: 32 }}>{emojiEspecie}</Text>
          </View>
        )}

        <View style={styles.info}>
          <Text style={styles.nome}>{item.nome}</Text>
          <Text style={styles.detalhe}>
            {item.especie}
            {item.raca ? ` · ${item.raca}` : ''}
          </Text>
          {item.data_nascimento && (
            <Text style={styles.detalhe}>🎂 {calcularIdade(item.data_nascimento)}</Text>
          )}
          {item.peso && (
            <Text style={styles.detalhe}>
              ⚖️ {item.peso} kg{item.porte ? ` · ${item.porte}` : ''}
            </Text>
          )}
        </View>

        <View style={styles.acoes}>
          <TouchableOpacity
            style={styles.botaoAcao}
            onPress={() => navigation.navigate('FormPet', { pet: item })}
          >
            <Ionicons name="create-outline" size={20} color={CORES.primario} />
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.botaoAcao}
            onPress={() => navigation.navigate('CalculadoraRacao', { pet: item })}
          >
            <Ionicons name="calculator-outline" size={20} color={CORES.primario} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => confirmarExcluir(item)}>
            <Ionicons name="trash-outline" size={20} color={CORES.erro} />
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={pets}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderPet}
        contentContainerStyle={styles.lista}
        ListHeaderComponent={
          focusSection ? (
            <View style={styles.focusBanner}>
              <View style={styles.focusBannerIcone}>
                <Ionicons name="medkit-outline" size={18} color={CORES.primario} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.focusBannerTitulo}>Escolha o pet</Text>
                <Text style={styles.focusBannerTexto}>
                  Vamos abrir direto em {getFocusLabel(focusSection)}.
                </Text>
              </View>
            </View>
          ) : null
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={carregar}
            tintColor={CORES.primario}
          />
        }
        ListEmptyComponent={
          !refreshing ? (
            <View style={styles.vazio}>
              <Text style={styles.vazioEmoji}>🐾</Text>
              <Text style={styles.vazioTexto}>Voce ainda nao cadastrou nenhum pet.</Text>
              <Text style={styles.vazioSub}>
                {focusSection
                  ? `Cadastre um pet para liberar ${getFocusLabel(focusSection)} no app.`
                  : 'Toque no botao + para adicionar seu primeiro amiguinho!'}
              </Text>
            </View>
          ) : null
        }
      />

      <TouchableOpacity style={styles.fab} onPress={() => navigation.navigate('FormPet', {})}>
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  lista: { padding: ESPACO.md },
  focusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
    padding: ESPACO.md,
    marginBottom: ESPACO.md,
    borderRadius: RAIO.md,
    backgroundColor: '#EFF6FF',
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  focusBannerIcone: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#DBEAFE',
  },
  focusBannerTitulo: {
    fontSize: FONTE.normal,
    fontWeight: '700',
    color: CORES.texto,
  },
  focusBannerTexto: {
    marginTop: 2,
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
  },
  card: {
    flexDirection: 'row',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.sm,
    alignItems: 'center',
    ...SOMBRA,
  },
  foto: { width: 70, height: 70, borderRadius: 35, marginRight: ESPACO.md },
  fotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  info: { flex: 1 },
  nome: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  detalhe: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  acoes: { gap: ESPACO.sm, alignItems: 'center' },
  botaoAcao: {
    padding: 6,
    backgroundColor: CORES.primarioClaro,
    borderRadius: RAIO.circulo,
  },
  vazio: { alignItems: 'center', paddingTop: 60, paddingHorizontal: ESPACO.xl },
  vazioEmoji: { fontSize: 60, marginBottom: ESPACO.md },
  vazioTexto: {
    fontSize: FONTE.grande,
    fontWeight: 'bold',
    color: CORES.texto,
    textAlign: 'center',
    marginBottom: 8,
  },
  vazioSub: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    textAlign: 'center',
  },
  fab: {
    position: 'absolute',
    bottom: ESPACO.xl,
    right: ESPACO.xl,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
    ...SOMBRA,
  },
});
