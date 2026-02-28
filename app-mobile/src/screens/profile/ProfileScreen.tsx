import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/auth.store';
import { updateProfile } from '../../services/auth.service';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { PONTOS } from '../../config';
import { formatarMoeda } from '../../utils/format';

export default function ProfileScreen() {
  const { user, logout, updateUser } = useAuthStore();
  const [editando, setEditando] = useState(false);
  const [editandoEndereco, setEditandoEndereco] = useState(false);
  const [nome, setNome] = useState(user?.nome ?? '');
  const [telefone, setTelefone] = useState(user?.telefone ?? '');
  const [cpf, setCpf] = useState(user?.cpf ?? '');

  // Endereço
  const [cep, setCep] = useState(user?.cep ?? '');
  const [rua, setRua] = useState(user?.endereco ?? '');
  const [numero, setNumero] = useState(user?.numero ?? '');
  const [bairro, setBairro] = useState(user?.bairro ?? '');
  const [cidade, setCidade] = useState(user?.cidade ?? '');
  const [estado, setEstado] = useState(user?.estado ?? '');
  const [buscandoCep, setBuscandoCep] = useState(false);

  const [salvando, setSalvando] = useState(false);

  const pontos = user?.pontos ?? 0;
  const valorPontos = (pontos / 100) * PONTOS.REAIS_POR_100_PONTOS;

  async function buscarCep(value: string) {
    const numeros = value.replace(/\D/g, '');
    if (numeros.length <= 5) {
      setCep(numeros);
    } else {
      setCep(numeros.slice(0, 5) + '-' + numeros.slice(5, 8));
    }
    if (numeros.length === 8) {
      setBuscandoCep(true);
      try {
        const resp = await fetch(`https://viacep.com.br/ws/${numeros}/json/`);
        const data = await resp.json();
        if (!data.erro) {
          setRua(data.logradouro ?? rua);
          setBairro(data.bairro ?? bairro);
          setCidade(data.localidade ?? cidade);
          setEstado(data.uf ?? estado);
        }
      } catch {}
      finally { setBuscandoCep(false); }
    }
  }

  async function salvarPerfil() {
    setSalvando(true);
    try {
      const updated = await updateProfile({
        nome: nome.trim() || undefined,
        telefone: telefone.trim() || undefined,
        cpf: cpf.trim() || undefined,
      });
      updateUser(updated);
      setEditando(false);
      Alert.alert('Salvo!', 'Seus dados foram atualizados.');
    } catch {
      Alert.alert('Erro', 'Não foi possível salvar.');
    } finally {
      setSalvando(false);
    }
  }

  async function salvarEndereco() {
    setSalvando(true);
    try {
      const updated = await updateProfile({
        cep: cep.trim() || undefined,
        endereco: rua.trim() || undefined,
        numero: numero.trim() || undefined,
        bairro: bairro.trim() || undefined,
        cidade: cidade.trim() || undefined,
        estado: estado.trim() || undefined,
      });
      updateUser(updated);
      setEditandoEndereco(false);
      Alert.alert('Salvo!', 'Endereço atualizado. Será sugerido no checkout.');
    } catch {
      Alert.alert('Erro', 'Não foi possível salvar o endereço.');
    } finally {
      setSalvando(false);
    }
  }

  function handleLogout() {
    Alert.alert(
      'Sair',
      'Deseja sair da sua conta?',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Sair', style: 'destructive', onPress: logout },
      ]
    );
  }

  const enderecoCompleto = user?.cidade
    ? `${user?.endereco ?? ''}, ${user?.numero ?? 's/n'} - ${user?.bairro ?? ''} - ${user?.cidade}/${user?.estado ?? ''}`
    : null;

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {/* Avatar e nome */}
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarEmoji}>
              {user?.nome ? user.nome[0].toUpperCase() : '👤'}
            </Text>
          </View>
          <Text style={styles.nomeUsuario}>{user?.nome || 'Meu perfil'}</Text>
          <Text style={styles.emailUsuario}>{user?.email}</Text>
        </View>

        {/* Card de pontos */}
        <View style={styles.pontosCard}>
          <View style={styles.pontosLeft}>
            <Ionicons name="trophy" size={28} color={CORES.pontos} />
            <View>
              <Text style={styles.pontosValor}>{pontos} pontos</Text>
              <Text style={styles.pontosLabel}>
                ≈ {formatarMoeda(valorPontos)} em desconto
              </Text>
            </View>
          </View>
          <View style={styles.pontosInfo}>
            <Text style={styles.pontosInfoTexto}>
              R$1 gasto = 1 ponto{'\n'}100 pts = R${PONTOS.REAIS_POR_100_PONTOS} desconto
            </Text>
          </View>
        </View>

        {/* Dados pessoais */}
        <View style={styles.secao}>
          <View style={styles.secaoHeader}>
            <Text style={styles.secaoTitulo}>Dados pessoais</Text>
            {!editando ? (
              <TouchableOpacity onPress={() => setEditando(true)}>
                <Text style={styles.editarTexto}>Editar</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity onPress={() => setEditando(false)}>
                <Text style={[styles.editarTexto, { color: CORES.erro }]}>Cancelar</Text>
              </TouchableOpacity>
            )}
          </View>

          {editando ? (
            <>
              <Campo label="Nome">
                <TextInput
                  style={styles.input}
                  value={nome}
                  onChangeText={setNome}
                  placeholder="Seu nome"
                  placeholderTextColor={CORES.textoClaro}
                />
              </Campo>
              <Campo label="Telefone">
                <TextInput
                  style={styles.input}
                  value={telefone}
                  onChangeText={setTelefone}
                  placeholder="(99) 99999-9999"
                  placeholderTextColor={CORES.textoClaro}
                  keyboardType="phone-pad"
                />
              </Campo>
              <Campo label="CPF">
                <TextInput
                  style={styles.input}
                  value={cpf}
                  onChangeText={setCpf}
                  placeholder="000.000.000-00"
                  placeholderTextColor={CORES.textoClaro}
                  keyboardType="numeric"
                />
              </Campo>
              <TouchableOpacity
                style={[styles.botaoSalvar, salvando && { opacity: 0.7 }]}
                onPress={salvarPerfil}
                disabled={salvando}
              >
                {salvando ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.botaoSalvarTexto}>Salvar alterações</Text>
                )}
              </TouchableOpacity>
            </>
          ) : (
            <>
              <InfoRow label="E-mail" valor={user?.email} />
              <InfoRow label="Nome" valor={user?.nome || '—'} />
              <InfoRow label="Telefone" valor={user?.telefone || '—'} />
              <InfoRow label="CPF" valor={user?.cpf || '—'} />
            </>
          )}
        </View>

        {/* Endereço de entrega */}
        <View style={styles.secao}>
          <View style={styles.secaoHeader}>
            <Text style={styles.secaoTitulo}>📍 Endereço padrão</Text>
            {!editandoEndereco ? (
              <TouchableOpacity onPress={() => setEditandoEndereco(true)}>
                <Text style={styles.editarTexto}>{enderecoCompleto ? 'Editar' : 'Cadastrar'}</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity onPress={() => setEditandoEndereco(false)}>
                <Text style={[styles.editarTexto, { color: CORES.erro }]}>Cancelar</Text>
              </TouchableOpacity>
            )}
          </View>

          {editandoEndereco ? (
            <>
              <Campo label={buscandoCep ? 'CEP (buscando...)' : 'CEP'}>
                <TextInput
                  style={styles.input}
                  value={cep}
                  onChangeText={buscarCep}
                  placeholder="00000-000"
                  placeholderTextColor={CORES.textoClaro}
                  keyboardType="numeric"
                  maxLength={9}
                />
              </Campo>
              <Campo label="Rua / Avenida">
                <TextInput style={styles.input} value={rua} onChangeText={setRua} placeholder="Rua..." placeholderTextColor={CORES.textoClaro} />
              </Campo>
              <View style={{ flexDirection: 'row', gap: ESPACO.sm }}>
                <View style={{ flex: 1 }}>
                  <Campo label="Número">
                    <TextInput style={styles.input} value={numero} onChangeText={setNumero} placeholder="123" placeholderTextColor={CORES.textoClaro} keyboardType="numeric" />
                  </Campo>
                </View>
                <View style={{ flex: 2 }}>
                  <Campo label="Bairro">
                    <TextInput style={styles.input} value={bairro} onChangeText={setBairro} placeholder="Bairro" placeholderTextColor={CORES.textoClaro} />
                  </Campo>
                </View>
              </View>
              <View style={{ flexDirection: 'row', gap: ESPACO.sm }}>
                <View style={{ flex: 2 }}>
                  <Campo label="Cidade">
                    <TextInput style={styles.input} value={cidade} onChangeText={setCidade} placeholder="Cidade" placeholderTextColor={CORES.textoClaro} />
                  </Campo>
                </View>
                <View style={{ flex: 1 }}>
                  <Campo label="UF">
                    <TextInput style={styles.input} value={estado} onChangeText={setEstado} placeholder="SP" placeholderTextColor={CORES.textoClaro} autoCapitalize="characters" maxLength={2} />
                  </Campo>
                </View>
              </View>
              <TouchableOpacity
                style={[styles.botaoSalvar, salvando && { opacity: 0.7 }]}
                onPress={salvarEndereco}
                disabled={salvando}
              >
                {salvando ? <ActivityIndicator color="#fff" /> : <Text style={styles.botaoSalvarTexto}>Salvar endereço</Text>}
              </TouchableOpacity>
            </>
          ) : enderecoCompleto ? (
            <View style={styles.enderecoCard}>
              <Ionicons name="location" size={20} color={CORES.primario} />
              <View style={{ flex: 1 }}>
                <Text style={styles.enderecoTexto}>{enderecoCompleto}</Text>
                {user?.cep && <Text style={styles.enderecoSub}>CEP: {user.cep}</Text>}
              </View>
            </View>
          ) : (
            <Text style={styles.enderecoVazio}>
              Cadastre seu endereço para agilizar o checkout de entregas.
            </Text>
          )}
        </View>

        {/* Menu de opções futuras */}
        <View style={styles.secao}>
          <Text style={styles.secaoTitulo}>Em breve</Text>
          <MenuItem emoji="📅" titulo="Agendamento de banho & tosa" em_breve />
          <MenuItem emoji="🩺" titulo="Consultas veterinárias" em_breve />
          <MenuItem emoji="📋" titulo="Resultado de exames" em_breve />
          <MenuItem emoji="💉" titulo="Carteirinha de vacinas" em_breve />
        </View>

        {/* Sair */}
        <TouchableOpacity style={styles.botaoSair} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={20} color={CORES.erro} />
          <Text style={styles.botaoSairTexto}>Sair da conta</Text>
        </TouchableOpacity>

        <Text style={styles.versao}>PetShop App v1.0.0</Text>
        <View style={{ height: ESPACO.xxl }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.campo}>
      <Text style={styles.campoLabel}>{label}</Text>
      {children}
    </View>
  );
}

function InfoRow({ label, valor }: { label: string; valor?: string | null }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValor}>{valor || '—'}</Text>
    </View>
  );
}

function MenuItem({ emoji, titulo, em_breve }: { emoji: string; titulo: string; em_breve?: boolean }) {
  return (
    <View style={styles.menuItem}>
      <Text style={styles.menuEmoji}>{emoji}</Text>
      <Text style={styles.menuTitulo}>{titulo}</Text>
      {em_breve && (
        <View style={styles.emBreve}>
          <Text style={styles.emBreveTexto}>Em breve</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg },
  avatarSection: { alignItems: 'center', marginBottom: ESPACO.lg },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: ESPACO.sm,
  },
  avatarEmoji: { fontSize: 36, color: '#fff' },
  nomeUsuario: { fontSize: FONTE.titulo, fontWeight: 'bold', color: CORES.texto },
  emailUsuario: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  pontosCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF8E1',
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    borderWidth: 1,
    borderColor: '#FFE082',
    gap: ESPACO.md,
    justifyContent: 'space-between',
    ...SOMBRA,
  },
  pontosLeft: { flexDirection: 'row', alignItems: 'center', gap: ESPACO.sm },
  pontosValor: { fontSize: FONTE.grande, fontWeight: 'bold', color: '#92400E' },
  pontosLabel: { fontSize: FONTE.pequena, color: '#78350F' },
  pontosInfo: { alignItems: 'flex-end' },
  pontosInfoTexto: { fontSize: FONTE.pequena, color: '#78350F', textAlign: 'right' },
  secao: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    ...SOMBRA,
  },
  secaoHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: ESPACO.md },
  secaoTitulo: { fontSize: FONTE.grande, fontWeight: 'bold', color: CORES.texto },
  editarTexto: { color: CORES.primario, fontWeight: '500' },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: ESPACO.sm },
  infoLabel: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  infoValor: { fontSize: FONTE.normal, color: CORES.texto, fontWeight: '500', flex: 1, textAlign: 'right' },
  campo: { marginBottom: ESPACO.sm },
  campoLabel: { fontSize: FONTE.pequena, fontWeight: '600', color: CORES.textoSecundario, marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    fontSize: FONTE.normal,
    color: CORES.texto,
    backgroundColor: CORES.fundo,
  },
  botaoSalvar: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.sm + 4,
    alignItems: 'center',
    marginTop: ESPACO.sm,
  },
  botaoSalvarTexto: { color: '#fff', fontWeight: 'bold', fontSize: FONTE.normal },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: ESPACO.sm,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
    gap: ESPACO.sm,
  },
  menuEmoji: { fontSize: 20, width: 28 },
  menuTitulo: { flex: 1, fontSize: FONTE.normal, color: CORES.texto },
  emBreve: {
    backgroundColor: '#EEF2FF',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RAIO.circulo,
  },
  emBreveTexto: { fontSize: FONTE.pequena, color: '#4338CA', fontWeight: '500' },
  botaoSair: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: ESPACO.sm,
    paddingVertical: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.erro,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.sm,
    backgroundColor: '#FEF2F2',
  },
  botaoSairTexto: { color: CORES.erro, fontWeight: 'bold', fontSize: FONTE.normal },
  versao: { textAlign: 'center', fontSize: FONTE.pequena, color: CORES.textoClaro },
  enderecoCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: ESPACO.sm,
    backgroundColor: '#EFF6FF',
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: '#BFDBFE',
  },
  enderecoTexto: { fontSize: FONTE.normal, color: CORES.texto, flex: 1 },
  enderecoSub: { fontSize: FONTE.pequena, color: CORES.textoSecundario, marginTop: 2 },
  enderecoVazio: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: ESPACO.sm,
  },
});
