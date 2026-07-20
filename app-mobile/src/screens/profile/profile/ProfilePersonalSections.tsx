import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { PONTOS } from "../../../config";
import { CORES } from "../../../theme";
import type { AppAccessProfile, AppProfileType, EcommerceUser } from "../../../types";
import { formatarMoeda } from "../../../utils/format";
import { Campo, InfoRow, SaveButton, SectionHeader } from "./ProfileSharedComponents";
import { profileStyles as styles } from "./ProfileStyles";

export function ProfileAvatarSection({ user }: { user: EcommerceUser | null }) {
  return (
    <View style={styles.avatarSection}>
      <View style={styles.avatar}>
        <Text style={styles.avatarLetter}>{user?.nome ? user.nome[0].toUpperCase() : "U"}</Text>
      </View>
      <Text style={styles.nomeUsuario}>{user?.nome || "Meu perfil"}</Text>
      <Text style={styles.emailUsuario}>{user?.email}</Text>
    </View>
  );
}

export function ProfilePointsCard({
  pontos,
  valorPontos,
}: {
  pontos: number;
  valorPontos: number;
}) {
  return (
    <View style={styles.pontosCard}>
      <View style={styles.pontosLeft}>
        <Ionicons name="trophy" size={28} color={CORES.pontos} />
        <View style={styles.pontosResumo}>
          <Text style={styles.pontosValor}>{pontos} pontos</Text>
          <Text style={styles.pontosLabel}>~ {formatarMoeda(valorPontos)} em desconto</Text>
        </View>
      </View>
      <View style={styles.pontosInfoSpacer} />
      <View style={styles.pontosInfo}>
        <Text style={styles.pontosInfoTextoLinha}>R$1 gasto = 1 ponto</Text>
        <Text style={styles.pontosInfoTextoLinha}>
          100 pts = R${PONTOS.REAIS_POR_100_PONTOS} desconto
        </Text>
      </View>
    </View>
  );
}

export function ProfileSwitcherSection({
  availableProfiles,
  perfilAtual,
  trocandoPerfil,
  onTrocarPerfil,
  onAbrirTrocaPerfil,
}: {
  availableProfiles: AppAccessProfile[];
  perfilAtual: AppProfileType;
  trocandoPerfil: boolean;
  onTrocarPerfil: (profileType: AppProfileType) => void;
  onAbrirTrocaPerfil: () => void;
}) {
  if (availableProfiles.length <= 1) return null;

  return (
    <View style={styles.secao}>
      <Text style={styles.secaoTitulo}>Trocar perfil</Text>
      <Text style={styles.textoSuporte}>Acesso atual: {perfilAtual}</Text>
      <View style={styles.perfisGrid}>
        {availableProfiles.map((profile) => {
          const selecionado = profile.type === perfilAtual;
          return (
            <TouchableOpacity
              key={profile.type}
              style={[styles.perfilBotao, selecionado && styles.perfilBotaoAtivo]}
              onPress={() => onTrocarPerfil(profile.type)}
              disabled={selecionado || trocandoPerfil}
            >
              <Text style={[styles.perfilBotaoTexto, selecionado && styles.perfilBotaoTextoAtivo]}>
                {profile.label || profile.type}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
      <TouchableOpacity
        style={[styles.botaoPerfilAtualizar, trocandoPerfil && { opacity: 0.7 }]}
        onPress={onAbrirTrocaPerfil}
        disabled={trocandoPerfil}
      >
        {trocandoPerfil ? (
          <ActivityIndicator color={CORES.primario} />
        ) : (
          <>
            <Ionicons name="swap-horizontal-outline" size={18} color={CORES.primario} />
            <Text style={styles.botaoPerfilAtualizarTexto}>Ver acessos disponiveis</Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
}

export function PersonalDataSection({
  user,
  editando,
  setEditando,
  nome,
  setNome,
  telefone,
  setTelefone,
  cpf,
  setCpf,
  salvando,
  onSalvarPerfil,
}: {
  user: EcommerceUser | null;
  editando: boolean;
  setEditando: (value: boolean) => void;
  nome: string;
  setNome: (value: string) => void;
  telefone: string;
  setTelefone: (value: string) => void;
  cpf: string;
  setCpf: (value: string) => void;
  salvando: boolean;
  onSalvarPerfil: () => void;
}) {
  return (
    <View style={styles.secao}>
      <SectionHeader
        title="Dados pessoais"
        editing={editando}
        onEdit={() => setEditando(true)}
        onCancel={() => setEditando(false)}
      />

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
          <SaveButton label="Salvar alteracoes" loading={salvando} onPress={onSalvarPerfil} />
        </>
      ) : (
        <>
          <InfoRow label="E-mail" valor={user?.email} />
          <InfoRow label="Nome" valor={user?.nome || "-"} />
          <InfoRow label="Telefone" valor={user?.telefone || "-"} />
          <InfoRow label="CPF" valor={user?.cpf || "-"} />
        </>
      )}
    </View>
  );
}

export function NotificationsSection({
  statusNotificacoes,
  ativandoNotificacoes,
  onAtivarNotificacoes,
}: {
  statusNotificacoes: string | null;
  ativandoNotificacoes: boolean;
  onAtivarNotificacoes: () => void;
}) {
  return (
    <View style={styles.secao}>
      <View style={styles.secaoHeader}>
        <Text style={styles.secaoTitulo}>Notificacoes de pedidos</Text>
      </View>
      {statusNotificacoes && <Text style={styles.textoSuporte}>{statusNotificacoes}</Text>}
      <TouchableOpacity
        style={[styles.botaoNotificacoes, ativandoNotificacoes && { opacity: 0.7 }]}
        onPress={onAtivarNotificacoes}
        disabled={ativandoNotificacoes}
      >
        {ativandoNotificacoes ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <Ionicons name="notifications-outline" size={20} color="#fff" />
            <Text style={styles.botaoNotificacoesTexto}>Ativar notificacoes</Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
}

export function LogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <TouchableOpacity style={styles.botaoSair} onPress={onLogout}>
      <Ionicons name="log-out-outline" size={20} color={CORES.erro} />
      <Text style={styles.botaoSairTexto}>Sair da conta</Text>
    </TouchableOpacity>
  );
}

export function AccountDeletionSection({
  excluindo,
  onExcluirConta,
}: {
  excluindo: boolean;
  onExcluirConta: (password: string) => Promise<void>;
}) {
  const [aberto, setAberto] = useState(false);
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const confirmado = confirmacao.trim().toUpperCase() === "EXCLUIR";
  const podeExcluir = senha.length > 0 && confirmado && !excluindo;

  function fechar() {
    if (excluindo) return;
    setAberto(false);
    setSenha("");
    setConfirmacao("");
  }

  async function confirmarExclusao() {
    if (!podeExcluir) return;
    try {
      await onExcluirConta(senha);
      fechar();
    } catch {
      // A tela principal apresenta a mensagem retornada pelo servidor.
    }
  }

  return (
    <>
      <View style={styles.exclusaoSecao}>
        <Text style={styles.exclusaoTitulo}>Excluir conta</Text>
        <Text style={styles.exclusaoTexto}>
          Exclui definitivamente sua conta, dados pessoais e pets. Registros que a loja
          precise manter por obrigacao legal permanecem anonimizados.
        </Text>
        <TouchableOpacity style={styles.botaoExcluirConta} onPress={() => setAberto(true)}>
          <Ionicons name="trash-outline" size={20} color={CORES.erro} />
          <Text style={styles.botaoExcluirContaTexto}>Excluir minha conta</Text>
        </TouchableOpacity>
      </View>

      <Modal
        visible={aberto}
        transparent
        animationType="fade"
        statusBarTranslucent
        onRequestClose={fechar}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <View style={styles.modalExclusao}>
            <View style={styles.modalExclusaoIcone}>
              <Ionicons name="warning-outline" size={28} color={CORES.erro} />
            </View>
            <Text style={styles.modalExclusaoTitulo}>Excluir conta definitivamente?</Text>
            <Text style={styles.modalExclusaoTexto}>
              Esta acao nao pode ser desfeita. Confirme sua senha e digite EXCLUIR.
            </Text>

            <Text style={styles.modalCampoLabel}>Senha atual</Text>
            <TextInput
              style={styles.input}
              value={senha}
              onChangeText={setSenha}
              placeholder="Digite sua senha"
              placeholderTextColor={CORES.textoClaro}
              secureTextEntry
              editable={!excluindo}
            />

            <Text style={styles.modalCampoLabel}>Confirmacao</Text>
            <TextInput
              style={styles.input}
              value={confirmacao}
              onChangeText={setConfirmacao}
              placeholder="Digite EXCLUIR"
              placeholderTextColor={CORES.textoClaro}
              autoCapitalize="characters"
              autoCorrect={false}
              editable={!excluindo}
            />

            <TouchableOpacity
              style={[
                styles.botaoExcluirDefinitivo,
                !podeExcluir && styles.botaoExcluirDefinitivoDesativado,
              ]}
              onPress={confirmarExclusao}
              disabled={!podeExcluir}
            >
              {excluindo ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.botaoExcluirDefinitivoTexto}>
                  Excluir conta definitivamente
                </Text>
              )}
            </TouchableOpacity>
            <TouchableOpacity style={styles.botaoCancelarExclusao} onPress={fechar} disabled={excluindo}>
              <Text style={styles.botaoCancelarExclusaoTexto}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}
