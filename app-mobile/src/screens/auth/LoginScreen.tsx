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
  Image,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../store/auth.store';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const { login } = useAuthStore();

  async function handleLogin() {
    if (!email.trim() || !senha.trim()) {
      Alert.alert('Campos obrigatórios', 'Preencha e-mail e senha.');
      return;
    }
    setCarregando(true);
    try {
      await login(email.trim().toLowerCase(), senha);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail === 'Incorrect username or password'
          ? 'E-mail ou senha incorretos.'
          : err?.response?.data?.detail || 'Erro ao fazer login. Tente novamente.';
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
        {/* Logo / cabeçalho */}
        <View style={styles.header}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoEmoji}>🐾</Text>
          </View>
          <Text style={styles.titulo}>PetShop App</Text>
          <Text style={styles.subtitulo}>Faça login para continuar</Text>
        </View>

        {/* Formulário */}
        <View style={styles.form}>
          <Text style={styles.label}>E-mail</Text>
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

          <Text style={styles.label}>Senha</Text>
          <View style={styles.inputComIcone}>
            <TextInput
              style={[styles.input, { flex: 1, marginBottom: 0, borderWidth: 0 }]}
              placeholder="Sua senha"
              placeholderTextColor={CORES.textoClaro}
              secureTextEntry={!mostrarSenha}
              value={senha}
              onChangeText={setSenha}
            />
            <TouchableOpacity onPress={() => setMostrarSenha(!mostrarSenha)} style={styles.iconeOlho}>
              <Ionicons name={mostrarSenha ? 'eye-off-outline' : 'eye-outline'} size={22} color={CORES.textoClaro} />
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={[styles.botao, carregando && styles.botaoDesativado]}
            onPress={handleLogin}
            disabled={carregando}
          >
            {carregando ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.botaoTexto}>Entrar</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkCadastro}
            onPress={() => navigation.navigate('Register')}
          >
            <Text style={styles.linkTexto}>
              Não tem conta? <Text style={styles.linkDestaque}>Cadastre-se grátis</Text>
            </Text>
          </TouchableOpacity>
        </View>

        {/* Rodapé de benefícios */}
        <View style={styles.beneficios}>
          <BeneficioItem emoji="📷" texto="Compre sem fila — escaneia e paga no app" />
          <BeneficioItem emoji="🏆" texto="Ganhe pontos em cada compra" />
          <BeneficioItem emoji="🐶" texto="Calculadora de ração personalizada" />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function BeneficioItem({ emoji, texto }: { emoji: string; texto: string }) {
  return (
    <View style={styles.beneficioItem}>
      <Text style={styles.beneficioEmoji}>{emoji}</Text>
      <Text style={styles.beneficioTexto}>{texto}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: CORES.fundo,
  },
  scroll: {
    flexGrow: 1,
    padding: ESPACO.lg,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: ESPACO.xl,
  },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: CORES.primario,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: ESPACO.md,
  },
  logoEmoji: {
    fontSize: 36,
  },
  titulo: {
    fontSize: FONTE.destaque,
    fontWeight: 'bold',
    color: CORES.texto,
  },
  subtitulo: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    marginTop: 4,
  },
  form: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.lg,
    marginBottom: ESPACO.lg,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 2,
  },
  label: {
    fontSize: FONTE.normal,
    fontWeight: '600',
    color: CORES.texto,
    marginBottom: ESPACO.xs,
  },
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
  botao: {
    backgroundColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.md - 2,
    alignItems: 'center',
    marginTop: ESPACO.xs,
  },
  botaoDesativado: {
    opacity: 0.7,
  },
  botaoTexto: {
    color: '#fff',
    fontSize: FONTE.media,
    fontWeight: 'bold',
  },
  linkCadastro: {
    alignItems: 'center',
    marginTop: ESPACO.md,
  },
  linkTexto: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
  },
  linkDestaque: {
    color: CORES.primario,
    fontWeight: '600',
  },
  beneficios: {
    gap: ESPACO.sm,
  },
  beneficioItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
  },
  beneficioEmoji: {
    fontSize: 18,
  },
  beneficioTexto: {
    fontSize: FONTE.normal,
    color: CORES.textoSecundario,
    flex: 1,
  },
  inputComIcone: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    marginBottom: ESPACO.md,
    backgroundColor: CORES.fundo,
  },
  iconeOlho: { padding: ESPACO.sm },
});
