import React, { useEffect, useState } from "react";
import { Alert } from "react-native";

import * as AuthService from "../../services/auth.service";
import { PONTOS } from "../../config";
import { updateProfile } from "../../services/auth.service";
import { ensurePushNotificationsRegistered } from "../../services/pushNotifications.service";
import { useAuthStore } from "../../store/auth.store";
import type { AppProfileType } from "../../types";
import { ProfileContent } from "./profile/ProfileContent";
import {
  buildDefaultAddress,
  buildDeliveryAddress,
  formatCepInput,
  getCurrentProfile,
  hasRequiredDeliveryAddress,
} from "./profile/ProfileUtils";

export default function ProfileScreen() {
  const { user, logout, updateUser, selectProfile } = useAuthStore();
  const entregaDetalhada = user?.endereco_entrega_detalhado ?? {};
  const [editando, setEditando] = useState(false);
  const [editandoEndereco, setEditandoEndereco] = useState(false);
  const [editandoEnderecoEntrega, setEditandoEnderecoEntrega] = useState(false);
  const [nome, setNome] = useState(user?.nome ?? "");
  const [telefone, setTelefone] = useState(user?.telefone ?? "");
  const [cpf, setCpf] = useState(user?.cpf ?? "");
  const [cep, setCep] = useState(user?.cep ?? "");
  const [rua, setRua] = useState(user?.endereco ?? "");
  const [numero, setNumero] = useState(user?.numero ?? "");
  const [complemento, setComplemento] = useState(user?.complemento ?? "");
  const [bairro, setBairro] = useState(user?.bairro ?? "");
  const [cidade, setCidade] = useState(user?.cidade ?? "");
  const [estado, setEstado] = useState(user?.estado ?? "");
  const [usarEnderecoEntregaDiferente, setUsarEnderecoEntregaDiferente] = useState(
    Boolean(user?.usar_endereco_entrega_diferente),
  );
  const [entregaNome, setEntregaNome] = useState(entregaDetalhada.entrega_nome ?? "");
  const [entregaCep, setEntregaCep] = useState(entregaDetalhada.entrega_cep ?? "");
  const [entregaEndereco, setEntregaEndereco] = useState(entregaDetalhada.entrega_endereco ?? "");
  const [entregaNumero, setEntregaNumero] = useState(entregaDetalhada.entrega_numero ?? "");
  const [entregaComplemento, setEntregaComplemento] = useState(entregaDetalhada.entrega_complemento ?? "");
  const [entregaBairro, setEntregaBairro] = useState(entregaDetalhada.entrega_bairro ?? "");
  const [entregaCidade, setEntregaCidade] = useState(entregaDetalhada.entrega_cidade ?? "");
  const [entregaEstado, setEntregaEstado] = useState(entregaDetalhada.entrega_estado ?? "");
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [buscandoCepEntrega, setBuscandoCepEntrega] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [trocandoPerfil, setTrocandoPerfil] = useState(false);
  const [ativandoNotificacoes, setAtivandoNotificacoes] = useState(false);
  const [statusNotificacoes, setStatusNotificacoes] = useState<string | null>(null);

  useEffect(() => {
    setNome(user?.nome ?? "");
    setTelefone(user?.telefone ?? "");
    setCpf(user?.cpf ?? "");
    setCep(user?.cep ?? "");
    setRua(user?.endereco ?? "");
    setNumero(user?.numero ?? "");
    setComplemento(user?.complemento ?? "");
    setBairro(user?.bairro ?? "");
    setCidade(user?.cidade ?? "");
    setEstado(user?.estado ?? "");
    const entregaAtual = user?.endereco_entrega_detalhado ?? {};
    setUsarEnderecoEntregaDiferente(Boolean(user?.usar_endereco_entrega_diferente));
    setEntregaNome(entregaAtual.entrega_nome ?? "");
    setEntregaCep(entregaAtual.entrega_cep ?? "");
    setEntregaEndereco(entregaAtual.entrega_endereco ?? "");
    setEntregaNumero(entregaAtual.entrega_numero ?? "");
    setEntregaComplemento(entregaAtual.entrega_complemento ?? "");
    setEntregaBairro(entregaAtual.entrega_bairro ?? "");
    setEntregaCidade(entregaAtual.entrega_cidade ?? "");
    setEntregaEstado(entregaAtual.entrega_estado ?? "");
  }, [user]);

  const pontos = user?.pontos ?? 0;
  const valorPontos = (pontos / 100) * PONTOS.REAIS_POR_100_PONTOS;
  const enderecoCompleto = buildDefaultAddress(user);
  const enderecoEntregaCompleto = buildDeliveryAddress(user, entregaDetalhada);
  const availableProfiles = user?.available_profiles ?? [];
  const perfilAtual = getCurrentProfile(user);

  async function buscarCep(value: string) {
    const numeros = value.replace(/\D/g, "");
    setCep(formatCepInput(value));

    if (numeros.length !== 8) return;

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
    } catch {
      // Mantem os dados atuais quando o CEP falhar.
    } finally {
      setBuscandoCep(false);
    }
  }

  async function buscarCepEntrega(value: string) {
    const numeros = value.replace(/\D/g, "");
    setEntregaCep(formatCepInput(value));

    if (numeros.length !== 8) return;

    setBuscandoCepEntrega(true);
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${numeros}/json/`);
      const data = await resp.json();
      if (!data.erro) {
        setEntregaEndereco(data.logradouro ?? entregaEndereco);
        setEntregaBairro(data.bairro ?? entregaBairro);
        setEntregaCidade(data.localidade ?? entregaCidade);
        setEntregaEstado(data.uf ?? entregaEstado);
      }
    } catch {
      // Mantem os dados atuais quando o CEP falhar.
    } finally {
      setBuscandoCepEntrega(false);
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
      Alert.alert("Salvo", "Seus dados foram atualizados.");
    } catch (err: any) {
      const mensagem = err?.response?.data?.detail || err?.message || "Nao foi possivel salvar seus dados.";
      Alert.alert("Erro", String(mensagem));
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
        complemento: complemento.trim() || undefined,
        bairro: bairro.trim() || undefined,
        cidade: cidade.trim() || undefined,
        estado: estado.trim() || undefined,
      });
      updateUser(updated);
      setEditandoEndereco(false);
      Alert.alert("Salvo", "Endereco atualizado com sucesso.");
    } catch (err: any) {
      const mensagem = err?.response?.data?.detail || err?.message || "Nao foi possivel salvar o endereco.";
      Alert.alert("Erro", String(mensagem));
    } finally {
      setSalvando(false);
    }
  }

  async function salvarEnderecoEntrega() {
    if (
      usarEnderecoEntregaDiferente &&
      !hasRequiredDeliveryAddress({
        entregaNome,
        entregaEndereco,
        entregaNumero,
        entregaBairro,
        entregaCidade,
        entregaEstado,
      })
    ) {
      Alert.alert("Endereco incompleto", "Preencha nome, rua, numero, bairro, cidade e UF da entrega.");
      return;
    }

    setSalvando(true);
    try {
      const updated = await updateProfile({
        usar_endereco_entrega_diferente: usarEnderecoEntregaDiferente,
        entrega_nome: entregaNome.trim() || undefined,
        entrega_cep: entregaCep.trim() || undefined,
        entrega_endereco: entregaEndereco.trim() || undefined,
        entrega_numero: entregaNumero.trim() || undefined,
        entrega_complemento: entregaComplemento.trim() || undefined,
        entrega_bairro: entregaBairro.trim() || undefined,
        entrega_cidade: entregaCidade.trim() || undefined,
        entrega_estado: entregaEstado.trim() || undefined,
      });
      updateUser(updated);
      setEditandoEnderecoEntrega(false);
      Alert.alert("Salvo", "Endereco de entrega atualizado com sucesso.");
    } catch (err: any) {
      const mensagem =
        err?.response?.data?.detail ||
        err?.message ||
        "Nao foi possivel salvar o endereco de entrega.";
      Alert.alert("Erro", String(mensagem));
    } finally {
      setSalvando(false);
    }
  }

  async function trocarPerfil(profileType: AppProfileType) {
    if (profileType === perfilAtual) return;

    setTrocandoPerfil(true);
    try {
      await selectProfile(profileType);
      Alert.alert("Pronto", "Acesso alterado com sucesso.");
    } catch (err: any) {
      const mensagem = err?.response?.data?.detail || err?.message || "Nao foi possivel trocar o acesso.";
      Alert.alert("Erro", String(mensagem));
    } finally {
      setTrocandoPerfil(false);
    }
  }

  async function abrirTrocaPerfil() {
    setTrocandoPerfil(true);
    try {
      const freshUser = await AuthService.getProfile();
      updateUser(freshUser);
      const freshProfiles = freshUser.available_profiles ?? [];
      const freshCurrentProfile = freshUser.selected_profile ?? freshUser.perfil_operacional ?? perfilAtual;
      const profileOptions = freshProfiles
        .filter((profile) => profile.type !== freshCurrentProfile)
        .map((profile) => ({
          text: profile.label || profile.type,
          onPress: () => {
            trocarPerfil(profile.type).catch(() => undefined);
          },
        }));

      if (profileOptions.length === 0) {
        Alert.alert("Trocar perfil", "Sem outros acessos liberados para esta conta.");
        return;
      }

      Alert.alert("Trocar perfil", "Escolha como entrar no app.", [
        ...profileOptions,
        { text: "Cancelar", style: "cancel" },
      ]);
    } catch (err: any) {
      const mensagem =
        err?.response?.data?.detail ||
        err?.message ||
        "Nao foi possivel carregar os acessos agora.";
      Alert.alert("Erro", String(mensagem));
    } finally {
      setTrocandoPerfil(false);
    }
  }

  function handleLogout() {
    Alert.alert("Sair", "Deseja sair da sua conta?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Sair", style: "destructive", onPress: logout },
    ]);
  }

  async function ativarNotificacoes() {
    setAtivandoNotificacoes(true);
    try {
      const result = await ensurePushNotificationsRegistered();
      setStatusNotificacoes(result.message);
      Alert.alert("Notificacoes", result.message);
    } catch (err: any) {
      const mensagem = err?.message || "Nao foi possivel ativar notificacoes.";
      setStatusNotificacoes(mensagem);
      Alert.alert("Notificacoes", mensagem);
    } finally {
      setAtivandoNotificacoes(false);
    }
  }

  return (
    <ProfileContent
      user={user}
      pontos={pontos}
      valorPontos={valorPontos}
      availableProfiles={availableProfiles}
      perfilAtual={perfilAtual}
      trocandoPerfil={trocandoPerfil}
      onTrocarPerfil={trocarPerfil}
      onAbrirTrocaPerfil={abrirTrocaPerfil}
      editando={editando}
      setEditando={setEditando}
      nome={nome}
      setNome={setNome}
      telefone={telefone}
      setTelefone={setTelefone}
      cpf={cpf}
      setCpf={setCpf}
      salvando={salvando}
      onSalvarPerfil={salvarPerfil}
      editandoEndereco={editandoEndereco}
      setEditandoEndereco={setEditandoEndereco}
      enderecoCompleto={enderecoCompleto}
      cep={cep}
      rua={rua}
      numero={numero}
      complemento={complemento}
      bairro={bairro}
      cidade={cidade}
      estado={estado}
      setRua={setRua}
      setNumero={setNumero}
      setComplemento={setComplemento}
      setBairro={setBairro}
      setCidade={setCidade}
      setEstado={setEstado}
      buscandoCep={buscandoCep}
      onBuscarCep={buscarCep}
      onSalvarEndereco={salvarEndereco}
      editandoEnderecoEntrega={editandoEnderecoEntrega}
      setEditandoEnderecoEntrega={setEditandoEnderecoEntrega}
      entregaDetalhada={entregaDetalhada}
      enderecoEntregaCompleto={enderecoEntregaCompleto}
      usarEnderecoEntregaDiferente={usarEnderecoEntregaDiferente}
      setUsarEnderecoEntregaDiferente={setUsarEnderecoEntregaDiferente}
      entregaNome={entregaNome}
      entregaCep={entregaCep}
      entregaEndereco={entregaEndereco}
      entregaNumero={entregaNumero}
      entregaComplemento={entregaComplemento}
      entregaBairro={entregaBairro}
      entregaCidade={entregaCidade}
      entregaEstado={entregaEstado}
      setEntregaNome={setEntregaNome}
      setEntregaEndereco={setEntregaEndereco}
      setEntregaNumero={setEntregaNumero}
      setEntregaComplemento={setEntregaComplemento}
      setEntregaBairro={setEntregaBairro}
      setEntregaCidade={setEntregaCidade}
      setEntregaEstado={setEntregaEstado}
      buscandoCepEntrega={buscandoCepEntrega}
      onBuscarCepEntrega={buscarCepEntrega}
      onSalvarEnderecoEntrega={salvarEnderecoEntrega}
      statusNotificacoes={statusNotificacoes}
      ativandoNotificacoes={ativandoNotificacoes}
      onAtivarNotificacoes={ativarNotificacoes}
      onLogout={handleLogout}
    />
  );
}
