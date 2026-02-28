import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/auth.store';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';

export default function RegisterScreen({ navigation }: any) {
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmarSenha, setConfirmarSenha] = useState('');
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [mostrarConfSenha, setMostrarConfSenha] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const { register } = useAuthStore();

  async function handleRegister() {
    if (!email.trim() || !senha.trim()) {
      Alert.alert('Campos obrigatórios', 'Preencha e-mail e senha.');
      return;
    }
    if (senha !== confirmarSenha) {
      Alert.alert('Senhas diferentes', 'A confirmação de senha não confere.');
      return;
    }
    if (senha.length < 6) {
      Alert.alert('Senha curta', 'A senha deve ter pelo menos 6 caracteres.');
      return;
    }
    setCarregando(true);
    try {
      await register(email.trim().toLowerCase(), senha, nome.trim() || undefined);
      // Login automático após registro — AppNavigator redireciona sozinho
    } catch (err: any) {
      console.log('=== ERRO REGISTRO ===');
      console.log('message:', err?.message);
      console.log('code:', err?.code);
      console.log('status:', err?.response?.status);
      console.log('data:', JSON.stringify(err?.response?.data));
      const detalhe = err?.response?.data?.detail;
      const msg =
        typeof detalhe === 'string' && detalhe.includes('already registered')
          ? 'Este e-mail já está cadastrado.'
          : detalhe || err?.message || 'Erro ao criar conta. Tente novamente.';
      Alert.alert('Erro', msg);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoEmoji}>🐾</Text>
          </View>
          <Text style={styles.titulo}>Criar conta</Text>
          <Text style={styles.subtitulo}>É grátis e bem rapidinho!</Text>
        </View>

        {/* Bônus de boas-vindas */}
        <View style={styles.bonusCard}>
          <Text style={styles.bonusEmoji}>🎁</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.bonusTitulo}>Bônus de boas-vindas!</Text>
            <Text style={styles.bonusTexto}>
              Cadastre-se agora e ganhe <Text style={styles.bonusDestaque}>50 pontos</Text> para usar na sua primeira compra.
            </Text>
          </View>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>Nome (opcional)</Text>
          <TextInput
            style={styles.input}
            placeholder="Seu nome"
            placeholderTextColor={CORES.textoClaro}
            value={nome}
            onChangeText={setNome}
            autoCapitalize="words"
          />

          <Text style={styles.label}>E-mail *</Text>
          <TextInput
            style={styles.input}
            placeholder="seu@email.com"
            placeholderTextColor={CORES.textoClaro}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            value={email}
            onChangeText={setEmail}
          />

          <Text style={styles.label}>Senha *</Text>
          <View style={styles.inputComIcone}>
            <TextInput
              style={[styles.input, { flex: 1, marginBottom: 0, borderWidth: 0 }]}
              placeholder="Mínimo 6 caracteres"
              placeholderTextColor={CORES.textoClaro}
              secureTextEntry={!mostrarSenha}
              value={senha}
              onChangeText={setSenha}
            />
            <TouchableOpacity onPress={() => setMostrarSenha(!mostrarSenha)} style={styles.iconeOlho}>
              <Ionicons name={mostrarSenha ? 'eye-off-outline' : 'eye-outline'} size={22} color={CORES.textoClaro} />
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Confirmar senha *</Text>
          <View style={[
            styles.inputComIcone,
            confirmarSenha && senha !== confirmarSenha && styles.inputComIconeErro,
          ]}>
            <TextInput
              style={[styles.input, { flex: 1, marginBottom: 0, borderWidth: 0 }]}
              placeholder="Repita a senha"
              placeholderTextColor={CORES.textoClaro}
              secureTextEntry={!mostrarConfSenha}
              value={confirmarSenha}
              onChangeText={setConfirmarSenha}
            />
            <TouchableOpacity onPress={() => setMostrarConfSenha(!mostrarConfSenha)} style={styles.iconeOlho}>
              <Ionicons name={mostrarConfSenha ? 'eye-off-outline' : 'eye-outline'} size={22} color={CORES.textoClaro} />
            </TouchableOpacity>
          </View>
          {confirmarSenha && senha !== confirmarSenha && (
            <Text style={styles.erroTexto}>As senhas não conferem</Text>
          )}

          <TouchableOpacity
            style={[styles.botao, carregando && styles.botaoDesativado]}
            onPress={handleRegister}
            disabled={carregando}
          >
            {carregando ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.botaoTexto}>Criar minha conta</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkLogin}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.linkTexto}>
              Já tem conta? <Text style={styles.linkDestaque}>Fazer login</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  scroll: { flexGrow: 1, padding: ESPACO.lg },
  header: { alignItems: 'center', marginBottom: ESPACO.lg, marginTop: ESPACO.xl },
  logoCircle: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: ESPACO.sm,
  },
  logoEmoji: { fontSize: 32 },
  titulo: { fontSize: FONTE.titulo, fontWeight: 'bold', color: CORES.texto },
  subtitulo: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  bonusCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF8E1',
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.lg,
    borderWidth: 1,
    borderColor: '#FFE082',
    gap: ESPACO.sm,
  },
  bonusEmoji: { fontSize: 28 },
  bonusTitulo: { fontSize: FONTE.normal, fontWeight: 'bold', color: '#92400E' },
  bonusTexto: { fontSize: FONTE.pequena, color: '#78350F', marginTop: 2 },
  bonusDestaque: { fontWeight: 'bold', color: '#B45309' },
  form: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 2,
  },
  label: { fontSize: FONTE.normal, fontWeight: '600', color: CORES.texto, marginBottom: ESPACO.xs },
  input: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm + 2,
    fontSize: FONTE.media,
    color: CORES.texto,
    marginBottom: ESPACO.md,
    backgroundColor: CORES.fundo,
  },
  inputErro: { borderColor: CORES.erro },
  erroTexto: { color: CORES.erro, fontSize: FONTE.pequena, marginTop: -ESPACO.sm, marginBottom: ESPACO.sm },
  botao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md - 2,
    alignItems: 'center',
    marginTop: ESPACO.xs,
  },
  botaoDesativado: { opacity: 0.7 },
  botaoTexto: { color: '#fff', fontSize: FONTE.media, fontWeight: 'bold' },
  linkLogin: { alignItems: 'center', marginTop: ESPACO.md },
  linkTexto: { fontSize: FONTE.normal, color: CORES.textoSecundario },
  linkDestaque: { color: CORES.primario, fontWeight: '600' },
  inputComIcone: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.md,
    backgroundColor: CORES.fundo,
  },
  inputComIconeErro: { borderColor: CORES.erro },
  iconeOlho: { padding: ESPACO.sm },
});
