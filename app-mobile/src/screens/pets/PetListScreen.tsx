import React, { useEffect, useState, useCallback } from 'react';
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
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { listarPets, deletarPet } from '../../services/pets.service';
import { Pet } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { calcularIdade } from '../../utils/format';

export default function PetListScreen() {
  const navigation = useNavigation<any>();
  const [pets, setPets] = useState<Pet[]>([]);
  const [refreshing, setRefreshing] = useState(false);

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
      Alert.alert('Erro', 'Não foi possível carregar seus pets.');
    } finally {
      setRefreshing(false);
    }
  }

  function confirmarExcluir(pet: Pet) {
    Alert.alert(
      'Excluir pet',
      `Deseja excluir ${pet.nome}? Esta ação não pode ser desfeita.`,
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
              Alert.alert('Erro', 'Não foi possível excluir o pet.');
            }
          },
        },
      ]
    );
  }

  function renderPet({ item }: { item: Pet }) {
    const emojiEspecie =
      item.especie === 'gato' ? '🐱' : item.especie === 'cão' ? '🐶' : '🐾';
    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('FormPet', { pet: item })}
      >
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
            <Text style={styles.detalhe}>⚖️ {item.peso} kg{item.porte ? ` · ${item.porte}` : ''}</Text>
          )}
        </View>
        <View style={styles.acoes}>
          <TouchableOpacity
            style={styles.botaoCalculadora}
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
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={carregar} tintColor={CORES.primario} />
        }
        ListEmptyComponent={
          !refreshing ? (
            <View style={styles.vazio}>
              <Text style={styles.vazioEmoji}>🐾</Text>
              <Text style={styles.vazioTexto}>Você ainda não cadastrou nenhum pet.</Text>
              <Text style={styles.vazioSub}>Toque no botão + para adicionar seu primeiro amiguinho!</Text>
            </View>
          ) : null
        }
      />
      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('FormPet', {})}
      >
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  lista: { padding: ESPACO.md },
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
  botaoCalculadora: {
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
  vazioSub: { fontSize: FONTE.normal, color: CORES.textoSecundario, textAlign: 'center' },
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
