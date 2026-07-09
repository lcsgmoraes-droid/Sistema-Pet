import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import KeyboardSafeScrollView from '../../components/KeyboardSafeScrollView';
import SelectedStoreBanner from '../../components/SelectedStoreBanner';
import { useAuthStore } from '../../store/auth.store';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';
import { AppProfileType } from '../../types';
import {
  isEmailVerificationSuccess,
  normalizeVerifiedEmailParam,
} from '../../utils/emailVerificationLoginLink';

export default function LoginScreen({ navigation, route }: any) {
  const emailConfirmado = isEmailVerificationSuccess(route?.params);
  const emailConfirmadoParam = normalizeVerifiedEmailParam(route?.params?.email);
  const [email, setEmail] = useState(emailConfirmadoParam);
  const [senha, setSenha] = useState('');
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const { login, pendingProfiles, needsProfileSelection, selectProfile } = useAuthStore();

  useEffect(() => {
    if (emailConfirmadoParam) {
      setEmail(emailConfirmadoParam);
    }
  }, [emailConfirmadoParam]);

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

  async function handleSelectProfile(profileType: AppProfileType) {
    setCarregando(true);
    try {
      await selectProfile(profileType);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Erro ao selecionar acesso. Tente novamente.';
      Alert.alert('Erro', msg);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.scroll}>
        {/* Logo / cabeçalho */}
        <View style={styles.header}>
          <View style={styles.logoCircle}>
            <Image source={require('../../../assets/icon.png')} style={styles.logoImage} />
          </View>
          <Text style={styles.titulo}>CorePet</Text>
          <Text style={styles.subtitulo}>Faça login para continuar</Text>
        </View>

        {/* Formulário */}
        <SelectedStoreBanner />

        <View style={styles.form}>
          {emailConfirmado && (
            <View style={styles.confirmationBox}>
              <Ionicons name="checkmark-circle-outline" size={22} color="#15803d" />
              <Text style={styles.confirmationText}>
                E-mail confirmado. Agora entre com sua senha para continuar.
              </Text>
            </View>
          )}

          <Text style={styles.label}>E-mail</Text>
          <TextInput
            style={styles.input}
            placeholder="seu@email.com"
            placeholderTextColor={CORES.textoClaro}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="email"
            textContentType="username"
            importantForAutofill="yes"
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
              autoComplete="current-password"
              textContentType="password"
              importantForAutofill="yes"
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

          {needsProfileSelection && pendingProfiles.length > 1 && (
            <View style={styles.profileBox}>
              <Text style={styles.profileTitle}>Escolha como entrar</Text>
              {pendingProfiles.map((profile) => (
                <TouchableOpacity
                  key={profile.type}
                  style={styles.profileButton}
                  onPress={() => handleSelectProfile(profile.type)}
                  disabled={carregando}
                >
                  <Text style={styles.profileButtonText}>{profile.label || profile.type}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          <TouchableOpacity
            style={styles.linkSecundario}
            onPress={() => navigation.navigate('ForgotPassword')}
          >
            <Text style={styles.linkSecundarioTexto}>Esqueci minha senha</Text>
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
    </KeyboardSafeScrollView>
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
    paddingBottom: 140,
  },
  header: {
    alignItems: 'center',
    marginBottom: ESPACO.xl,
  },
  logoCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: CORES.superficie,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: ESPACO.md,
    borderWidth: 1,
    borderColor: CORES.borda,
  },
  logoImage: {
    width: 68,
    height: 68,
    borderRadius: 18,
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
  linkSecundario: {
    alignItems: 'center',
    marginTop: ESPACO.md,
  },
  linkSecundarioTexto: {
    fontSize: FONTE.normal,
    color: CORES.primario,
    fontWeight: '600',
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
  profileBox: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginTop: ESPACO.md,
    gap: ESPACO.sm,
    backgroundColor: CORES.fundo,
  },
  profileTitle: {
    fontSize: FONTE.normal,
    fontWeight: '700',
    color: CORES.texto,
  },
  profileButton: {
    borderWidth: 1,
    borderColor: CORES.primario,
    borderRadius: RAIO.md,
    paddingVertical: ESPACO.sm + 2,
    alignItems: 'center',
    backgroundColor: CORES.superficie,
  },
  profileButtonText: {
    color: CORES.primario,
    fontSize: FONTE.normal,
    fontWeight: '700',
  },
  confirmationBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
    borderWidth: 1,
    borderColor: '#BBF7D0',
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    marginBottom: ESPACO.md,
    backgroundColor: '#F0FDF4',
  },
  confirmationText: {
    flex: 1,
    color: '#166534',
    fontSize: FONTE.normal,
    fontWeight: '600',
  },
});
