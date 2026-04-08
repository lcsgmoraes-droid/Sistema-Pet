import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as AuthService from '../../services/auth.service';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';

type Step = 'request' | 'reset';

export default function ForgotPasswordScreen({ navigation }: any) {
  const [step, setStep] = useState<Step>('request');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmarSenha, setConfirmarSenha] = useState('');
  const [mostrarNovaSenha, setMostrarNovaSenha] = useState(false);
  const [mostrarConfirmarSenha, setMostrarConfirmarSenha] = useState(false);
  const [carregando, setCarregando] = useState(false);

  async function handleSolicitarToken() {
    const emailNormalizado = email.trim().toLowerCase();
    if (!emailNormalizado) {
      Alert.alert('E-mail obrigatório', 'Informe o e-mail da conta para recuperar a senha.');
      return;
    }

    setCarregando(true);
    try {
      const data = await AuthService.requestPasswordReset(emailNormalizado);
      setEmail(emailNormalizado);
      setStep('reset');
      Alert.alert(
        'Confira seu e-mail',
        data?.expires_in_minutes
          ? `Enviamos um token de recuperação. Ele expira em ${data.expires_in_minutes} minutos.`
          : 'Enviamos um token de recuperação para o seu e-mail.',
      );
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        'Não foi possível iniciar a recuperação de senha agora. Tente novamente.';
      Alert.alert('Erro', msg);
    } finally {
      setCarregando(false);
    }
  }

  async function handleResetarSenha() {
    const emailNormalizado = email.trim().toLowerCase();
    if (!emailNormalizado || !token.trim()) {
      Alert.alert('Campos obrigatórios', 'Preencha o e-mail e o token recebido.');
      return;
    }
    if (novaSenha.length < 6) {
      Alert.alert('Senha curta', 'A nova senha deve ter pelo menos 6 caracteres.');
      return;
    }
    if (novaSenha !== confirmarSenha) {
      Alert.alert('Senhas diferentes', 'A confirmação da senha não confere.');
      return;
    }

    setCarregando(true);
    try {
      await AuthService.resetPassword(emailNormalizado, token.trim(), novaSenha);
      Alert.alert('Senha atualizada', 'Sua senha foi redefinida com sucesso.', [
        {
          text: 'Ir para login',
          onPress: () => navigation.navigate('Login'),
        },
      ]);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        'Não foi possível redefinir sua senha. Verifique o token e tente novamente.';
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
            <Text style={styles.logoEmoji}>🔐</Text>
          </View>
          <Text style={styles.titulo}>Recuperar senha</Text>
          <Text style={styles.subtitulo}>
            {step === 'request'
              ? 'Vamos enviar um token para o e-mail da sua conta.'
              : 'Digite o token recebido e escolha sua nova senha.'}
          </Text>
        </View>

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
            editable={!carregando}
          />

          {step === 'reset' && (
            <>
              <Text style={styles.label}>Token de recuperação</Text>
              <TextInput
                style={styles.input}
                placeholder="Cole o token recebido por e-mail"
                placeholderTextColor={CORES.textoClaro}
                autoCapitalize="none"
                autoCorrect={false}
                value={token}
                onChangeText={setToken}
                editable={!carregando}
              />

              <Text style={styles.label}>Nova senha</Text>
              <View style={styles.inputComIcone}>
                <TextInput
                  style={[styles.input, styles.inputSemMargem]}
                  placeholder="Mínimo 6 caracteres"
                  placeholderTextColor={CORES.textoClaro}
                  secureTextEntry={!mostrarNovaSenha}
                  value={novaSenha}
                  onChangeText={setNovaSenha}
                  editable={!carregando}
                />
                <TouchableOpacity
                  onPress={() => setMostrarNovaSenha((valor) => !valor)}
                  style={styles.iconeOlho}
                >
                  <Ionicons
                    name={mostrarNovaSenha ? 'eye-off-outline' : 'eye-outline'}
                    size={22}
                    color={CORES.textoClaro}
                  />
                </TouchableOpacity>
              </View>

              <Text style={styles.label}>Confirmar nova senha</Text>
              <View style={styles.inputComIcone}>
                <TextInput
                  style={[styles.input, styles.inputSemMargem]}
                  placeholder="Repita a nova senha"
                  placeholderTextColor={CORES.textoClaro}
                  secureTextEntry={!mostrarConfirmarSenha}
                  value={confirmarSenha}
                  onChangeText={setConfirmarSenha}
                  editable={!carregando}
                />
                <TouchableOpacity
                  onPress={() => setMostrarConfirmarSenha((valor) => !valor)}
                  style={styles.iconeOlho}
                >
                  <Ionicons
                    name={mostrarConfirmarSenha ? 'eye-off-outline' : 'eye-outline'}
                    size={22}
                    color={CORES.textoClaro}
                  />
                </TouchableOpacity>
              </View>
            </>
          )}

          <TouchableOpacity
            style={[styles.botao, carregando && styles.botaoDesativado]}
            onPress={step === 'request' ? handleSolicitarToken : handleResetarSenha}
            disabled={carregando}
          >
            {carregando ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.botaoTexto}>
                {step === 'request' ? 'Enviar token por e-mail' : 'Salvar nova senha'}
              </Text>
            )}
          </TouchableOpacity>

          {step === 'reset' && (
            <TouchableOpacity
              style={styles.linkSecundario}
              onPress={handleSolicitarToken}
              disabled={carregando}
            >
              <Text style={styles.linkSecundarioTexto}>Reenviar token</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity style={styles.linkLogin} onPress={() => navigation.navigate('Login')}>
            <Text style={styles.linkTexto}>
              Lembrou a senha? <Text style={styles.linkDestaque}>Voltar para login</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
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
    fontSize: 34,
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
    textAlign: 'center',
  },
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
  label: {
    fontSize: FONTE.normal,
    fontWeight: '600',
    color: CORES.texto,
    marginBottom: ESPACO.xs,
  },
  input: {
    flex: 1,
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
  inputSemMargem: {
    marginBottom: 0,
    borderWidth: 0,
  },
  inputComIcone: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: CORES.fundo,
    marginBottom: ESPACO.md,
  },
  iconeOlho: {
    paddingHorizontal: ESPACO.sm,
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
  linkSecundario: {
    alignItems: 'center',
    marginTop: ESPACO.md,
  },
  linkSecundarioTexto: {
    fontSize: FONTE.normal,
    color: CORES.primario,
    fontWeight: '600',
  },
  linkLogin: {
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
});
