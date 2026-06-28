import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Switch,
  Image,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import KeyboardSafeScrollView from '../../components/KeyboardSafeScrollView';
import { criarPet, atualizarPet, uploadFotoPet } from '../../services/pets.service';
import { Pet, PetFormData } from '../../types';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';

const ESPECIES = ['cão', 'gato', 'coelho', 'hamster', 'pássaro', 'peixe', 'outro'];
const PORTES = ['mini', 'pequeno', 'médio', 'grande', 'gigante'];
const SEXOS = ['macho', 'fêmea'];
const NIVEIS_ATIVIDADE = ['baixo', 'normal', 'alto'];

interface Props {
  route: { params?: { pet?: Pet } };
  navigation: any;
}

export default function PetFormScreen({ route, navigation }: Props) {
  const petExistente = route.params?.pet;
  const isEdicao = !!petExistente;

  const [nome, setNome] = useState(petExistente?.nome ?? '');
  const [especie, setEspecie] = useState(petExistente?.especie ?? '');
  const [raca, setRaca] = useState(petExistente?.raca ?? '');
  const [sexo, setSexo] = useState(petExistente?.sexo ?? '');
  const [castrado, setCastrado] = useState(petExistente?.castrado ?? false);
  const [peso, setPeso] = useState(petExistente?.peso ? String(petExistente.peso) : '');
  const [porte, setPorte] = useState(petExistente?.porte ?? '');
  const [cor, setCor] = useState(petExistente?.cor ?? '');
  // Data em dd/mm/aaaa para exibição; converte para ISO ao salvar
  const [dataNascimento, setDataNascimento] = useState(() => {
    if (!petExistente?.data_nascimento) return '';
    const iso = petExistente.data_nascimento.split('T')[0]; // aaaa-mm-dd
    const [a, m, d] = iso.split('-');
    return `${d}/${m}/${a}`;
  });
  const [alergias, setAlergias] = useState(petExistente?.alergias ?? '');
  const [observacoes, setObservacoes] = useState(petExistente?.observacoes ?? '');
  const [salvando, setSalvando] = useState(false);

  // Foto do pet
  const [fotoUrl, setFotoUrl] = useState(petExistente?.foto_url ?? null);
  const [fotoPendente, setFotoPendente] = useState<string | null>(null); // URI local antes do upload
  const [fazendoUpload, setFazendoUpload] = useState(false);
  const ignorarAvisoSaidaRef = useRef(false);

  async function pickFoto() {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permissão necessária', 'Permita o acesso à galeria nas configurações do celular.');
      return;
    }
    Alert.alert(
      'Enquadrar foto',
      'Depois de escolher a imagem, toque em Cortar para confirmar o enquadramento. Em seguida, volte ao CorePet e toque em Salvar foto.',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Escolher foto', onPress: abrirEditorFoto },
      ]
    );
  }

  async function abrirEditorFoto() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      ignorarAvisoSaidaRef.current = false;
      setFotoPendente(result.assets[0].uri);
      Alert.alert(
        'Foto pronta',
        'O corte foi confirmado. Para enviar a nova foto, toque em Salvar foto.',
        [{ text: 'OK' }]
      );
    }
  }

  useEffect(() => {
    const unsubscribe = navigation.addListener('beforeRemove', (e: any) => {
      if (!fotoPendente || salvando || fazendoUpload || ignorarAvisoSaidaRef.current) {
        return;
      }

      e.preventDefault();
      Alert.alert(
        'Foto sem salvar',
        'Você escolheu uma nova foto para o pet. Deseja salvar as alterações antes de sair?',
        [
          { text: 'Continuar editando', style: 'cancel' },
          {
            text: 'Sair sem salvar',
            style: 'destructive',
            onPress: () => {
              ignorarAvisoSaidaRef.current = true;
              setFotoPendente(null);
              navigation.dispatch(e.data.action);
            },
          },
          { text: 'Salvar alterações', onPress: () => salvar() },
        ]
      );
    });

    return unsubscribe;
  }, [fazendoUpload, fotoPendente, navigation, salvando, salvar]);

  function handleDataNascimento(texto: string) {
    setDataNascimento(mascaraData(texto));
  }

  async function salvar() {
    if (!nome.trim()) {
      Alert.alert('Campo obrigatório', 'Digite o nome do pet.');
      return;
    }
    if (!especie) {
      Alert.alert('Campo obrigatório', 'Selecione a espécie do pet.');
      return;
    }

    const form: PetFormData = {
      nome: nome.trim(),
      especie,
      raca: raca.trim() || undefined,
      sexo: sexo || undefined,
      castrado,
      peso: peso ? parseFloat(peso) : undefined,
      porte: porte || undefined,
      cor: cor.trim() || undefined,
      data_nascimento: dataNascimento ? dataNascimentoParaISO(dataNascimento) : undefined,
      alergias: alergias.trim() || undefined,
      observacoes: observacoes.trim() || undefined,
    };

    setSalvando(true);
    try {
      let petSalvo: Pet;
      if (isEdicao) {
        petSalvo = await atualizarPet(petExistente!.id, form);
        Alert.alert('Salvo!', `${nome} foi atualizado(a).`);
      } else {
        petSalvo = await criarPet(form);
        Alert.alert('Pet cadastrado!', `${nome} foi adicionado(a) com sucesso. 🐾`);
      }
      // Upload da foto pendente após salvar o pet
      if (fotoPendente) {
        setFazendoUpload(true);
        try {
          const petAtualizado = await uploadFotoPet(petSalvo.id, fotoPendente);
          setFotoUrl(petAtualizado.foto_url ?? null);
          setFotoPendente(null);
        } catch (uploadErr: any) {
          Alert.alert(
            'Foto não salva',
            uploadErr?.response?.data?.detail ||
              'O pet foi salvo, mas a foto não foi enviada. Tente salvar novamente.'
          );
          return;
        } finally {
          setFazendoUpload(false);
        }
      }
      ignorarAvisoSaidaRef.current = true;
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Erro', err?.response?.data?.detail || 'Não foi possível salvar.');
    } finally {
      setSalvando(false);
    }
  }

  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Foto do pet */}
      <TouchableOpacity style={styles.fotoBox} onPress={pickFoto}>
        {fotoPendente ? (
          <Image source={{ uri: fotoPendente }} style={styles.foto} />
        ) : fotoUrl ? (
          <Image source={{ uri: fotoUrl }} style={styles.foto} />
        ) : (
          <View style={styles.fotoPlaceholder}>
            <Ionicons name="camera-outline" size={32} color={CORES.textoClaro} />
            <Text style={styles.fotoPlaceholderTexto}>Adicionar foto</Text>
          </View>
        )}
        <View style={styles.fotoCamera}>
          <Ionicons name="camera" size={16} color="#fff" />
        </View>
      </TouchableOpacity>
      {fazendoUpload && (
        <View style={{ alignItems: 'center', marginBottom: ESPACO.sm }}>
          <ActivityIndicator size="small" color={CORES.primario} />
          <Text style={{ fontSize: FONTE.pequena, color: CORES.textoSecundario }}>Salvando foto...</Text>
        </View>
      )}
      {fotoPendente && !fazendoUpload && (
        <View style={styles.fotoPendenteCard}>
          <View style={styles.fotoPendenteCabecalho}>
            <Ionicons name="checkmark-circle" size={22} color={CORES.sucesso} />
            <View style={styles.fotoPendenteTexto}>
              <Text style={styles.fotoPendenteTitulo}>Foto pronta para salvar</Text>
              <Text style={styles.fotoPendenteSub}>
                Toque em Salvar foto para enviar a nova imagem do pet.
              </Text>
            </View>
          </View>
          <View style={styles.fotoPendenteAcoes}>
            <TouchableOpacity
              style={[styles.fotoPendenteBotao, salvando && styles.botaoDesativado]}
              onPress={salvar}
              disabled={salvando}
            >
              <Text style={styles.fotoPendenteBotaoTexto}>Salvar foto</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.fotoPendenteBotaoSecundario} onPress={pickFoto}>
              <Text style={styles.fotoPendenteBotaoSecundarioTexto}>Trocar foto</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Nome */}
      <Campo label="Nome do pet *">
        <TextInput
          style={styles.input}
          placeholder="Ex: Rex, Mia, Bolinha..."
          placeholderTextColor={CORES.textoClaro}
          value={nome}
          onChangeText={setNome}
          autoCapitalize="words"
        />
      </Campo>

      {/* Espécie */}
      <Campo label="Espécie *">
        <View style={styles.chips}>
          {ESPECIES.map((e) => (
            <TouchableOpacity
              key={e}
              style={[styles.chip, especie === e && styles.chipAtivo]}
              onPress={() => setEspecie(e)}
            >
              <Text style={[styles.chipTexto, especie === e && styles.chipTextoAtivo]}>
                {emojiEspecie(e)} {e}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </Campo>

      {/* Raça */}
      <Campo label="Raça (opcional)">
        <TextInput
          style={styles.input}
          placeholder="Ex: Labrador, Persa, SRD..."
          placeholderTextColor={CORES.textoClaro}
          value={raca}
          onChangeText={setRaca}
        />
      </Campo>

      {/* Sexo */}
      <Campo label="Sexo">
        <View style={styles.chips}>
          {SEXOS.map((s) => (
            <TouchableOpacity
              key={s}
              style={[styles.chip, sexo === s && styles.chipAtivo]}
              onPress={() => setSexo(s)}
            >
              <Text style={[styles.chipTexto, sexo === s && styles.chipTextoAtivo]}>
                {s === 'macho' ? '♂️' : '♀️'} {s}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </Campo>

      {/* Castrado */}
      <View style={styles.switchRow}>
        <Text style={styles.label}>Castrado(a)</Text>
        <Switch
          value={castrado}
          onValueChange={setCastrado}
          trackColor={{ false: CORES.borda, true: CORES.primarioClaro }}
          thumbColor={castrado ? CORES.primario : '#f4f3f4'}
        />
      </View>

      {/* Peso */}
      <Campo label="Peso (kg)">
        <TextInput
          style={styles.input}
          placeholder="Ex: 8.5"
          placeholderTextColor={CORES.textoClaro}
          keyboardType="decimal-pad"
          value={peso}
          onChangeText={setPeso}
        />
      </Campo>

      {/* Porte */}
      <Campo label="Porte">
        <View style={styles.chips}>
          {PORTES.map((p) => (
            <TouchableOpacity
              key={p}
              style={[styles.chip, porte === p && styles.chipAtivo]}
              onPress={() => setPorte(p)}
            >
              <Text style={[styles.chipTexto, porte === p && styles.chipTextoAtivo]}>{p}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </Campo>

      {/* Data de nascimento */}
      <Campo label="Data de nascimento">
        <TextInput
          style={styles.input}
          placeholder="Ex: 15/03/2021"
          placeholderTextColor={CORES.textoClaro}
          value={dataNascimento}
          onChangeText={handleDataNascimento}
          keyboardType="numeric"
          maxLength={10}
        />
      </Campo>

      {/* Cor */}
      <Campo label="Cor / pelagem">
        <TextInput
          style={styles.input}
          placeholder="Ex: caramelo, preto e branco..."
          placeholderTextColor={CORES.textoClaro}
          value={cor}
          onChangeText={setCor}
        />
      </Campo>

      {/* Alergias */}
      <Campo label="Alergias conhecidas">
        <TextInput
          style={[styles.input, styles.textarea]}
          placeholder="Liste alergias, se houver..."
          placeholderTextColor={CORES.textoClaro}
          multiline
          numberOfLines={3}
          value={alergias}
          onChangeText={setAlergias}
        />
      </Campo>

      {/* Observações */}
      <Campo label="Observações">
        <TextInput
          style={[styles.input, styles.textarea]}
          placeholder="Outras informações importantes..."
          placeholderTextColor={CORES.textoClaro}
          multiline
          numberOfLines={3}
          value={observacoes}
          onChangeText={setObservacoes}
        />
      </Campo>

      <TouchableOpacity
        style={[styles.botao, salvando && styles.botaoDesativado]}
        onPress={salvar}
        disabled={salvando}
      >
        {salvando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.botaoTexto}>
            {isEdicao ? 'Salvar alterações' : 'Cadastrar pet'} 🐾
          </Text>
        )}
      </TouchableOpacity>

      <View style={{ height: ESPACO.xxl }} />
    </KeyboardSafeScrollView>
  );
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.campo}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

// Aplica máscara dd/mm/aaaa com barras automáticas
function mascaraData(valor: string): string {
  const nums = valor.replace(/\D/g, '').slice(0, 8);
  if (nums.length <= 2) return nums;
  if (nums.length <= 4) return `${nums.slice(0, 2)}/${nums.slice(2)}`;
  return `${nums.slice(0, 2)}/${nums.slice(2, 4)}/${nums.slice(4)}`;
}

// Converte dd/mm/aaaa → aaaa-mm-dd para o backend
function dataNascimentoParaISO(data: string): string {
  const [d, m, a] = data.split('/');
  if (!a || a.length < 4) return '';
  return `${a}-${m?.padStart(2, '0')}-${d?.padStart(2, '0')}`;
}

function emojiEspecie(e: string): string {
  const map: Record<string, string> = {
    cão: '🐶', gato: '🐱', coelho: '🐰', hamster: '🐹',
    pássaro: '🦜', peixe: '🐟', outro: '🐾',
  };
  return map[e] ?? '🐾';
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg, paddingBottom: 140 },
  campo: { marginBottom: ESPACO.md },
  label: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto, marginBottom: ESPACO.xs },
  input: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 2,
    fontSize: FONTE.media,
    color: CORES.texto,
    backgroundColor: CORES.superficie,
  },
  textarea: { minHeight: 80, textAlignVertical: 'top' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: ESPACO.xs },
  chip: {
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.xs + 2,
    borderRadius: RAIO.circulo,
    borderWidth: 1,
    borderColor: CORES.borda,
    backgroundColor: CORES.superficie,
  },
  chipAtivo: { backgroundColor: CORES.primario, borderColor: CORES.primario },
  chipTexto: { fontSize: FONTE.normal, color: CORES.texto },
  chipTextoAtivo: { color: '#fff', fontWeight: '600' },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: ESPACO.md,
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    borderWidth: 1,
    borderColor: CORES.borda,
  },
  botao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md,
    alignItems: 'center',
    marginTop: ESPACO.md,
  },
  botaoDesativado: { opacity: 0.7 },
  botaoTexto: { color: '#fff', fontSize: FONTE.media, fontWeight: 'bold' },
  fotoBox: {
    alignSelf: 'center',
    marginBottom: ESPACO.lg,
    position: 'relative',
  },
  foto: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 2,
    borderColor: CORES.primario,
  },
  fotoPlaceholder: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: CORES.borda,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: CORES.borda,
    borderStyle: 'dashed',
    gap: 4,
  },
  fotoPlaceholderTexto: { fontSize: FONTE.pequena, color: CORES.textoClaro },
  fotoCamera: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    backgroundColor: CORES.primario,
    borderRadius: 16,
    padding: 6,
    borderWidth: 2,
    borderColor: '#fff',
  },
  fotoPendenteCard: {
    backgroundColor: '#F0FDF4',
    borderWidth: 1,
    borderColor: '#BBF7D0',
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.md,
    gap: ESPACO.sm,
  },
  fotoPendenteCabecalho: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: ESPACO.sm,
  },
  fotoPendenteTexto: {
    flex: 1,
    minWidth: 0,
  },
  fotoPendenteTitulo: {
    fontSize: FONTE.normal,
    fontWeight: '700',
    color: CORES.texto,
    marginBottom: 2,
  },
  fotoPendenteSub: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    lineHeight: 17,
  },
  fotoPendenteAcoes: {
    flexDirection: 'row',
    gap: ESPACO.sm,
  },
  fotoPendenteBotao: {
    flex: 1,
    minHeight: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: CORES.sucesso,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.sm,
  },
  fotoPendenteBotaoTexto: {
    color: '#fff',
    fontSize: FONTE.pequena,
    fontWeight: '700',
    textAlign: 'center',
  },
  fotoPendenteBotaoSecundario: {
    flex: 1,
    minHeight: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.sm,
  },
  fotoPendenteBotaoSecundarioTexto: {
    color: CORES.primario,
    fontSize: FONTE.pequena,
    fontWeight: '700',
    textAlign: 'center',
  },
});
