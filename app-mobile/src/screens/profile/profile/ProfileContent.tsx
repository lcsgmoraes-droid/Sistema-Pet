import React, { type Dispatch, type SetStateAction } from "react";
import { Text, View } from "react-native";

import KeyboardSafeScrollView from "../../../components/KeyboardSafeScrollView";
import { ESPACO } from "../../../theme";
import type { AppAccessProfile, AppProfileType, EcommerceDeliveryAddress, EcommerceUser } from "../../../types";
import { DefaultAddressSection, DeliveryAddressSection } from "./ProfileAddressSections";
import {
  AccountDeletionSection,
  LogoutButton,
  NotificationsSection,
  PersonalDataSection,
  ProfileAvatarSection,
  ProfilePointsCard,
  ProfileSwitcherSection,
} from "./ProfilePersonalSections";
import { profileStyles as styles } from "./ProfileStyles";

interface ProfileContentProps {
  user: EcommerceUser | null;
  pontos: number;
  valorPontos: number;
  availableProfiles: AppAccessProfile[];
  perfilAtual: AppProfileType;
  trocandoPerfil: boolean;
  onTrocarPerfil: (profileType: AppProfileType) => void;
  onAbrirTrocaPerfil: () => void;
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
  editandoEndereco: boolean;
  setEditandoEndereco: (value: boolean) => void;
  enderecoCompleto: string | null;
  cep: string;
  rua: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
  setRua: (value: string) => void;
  setNumero: (value: string) => void;
  setComplemento: (value: string) => void;
  setBairro: (value: string) => void;
  setCidade: (value: string) => void;
  setEstado: (value: string) => void;
  buscandoCep: boolean;
  onBuscarCep: (value: string) => void;
  onSalvarEndereco: () => void;
  editandoEnderecoEntrega: boolean;
  setEditandoEnderecoEntrega: (value: boolean) => void;
  entregaDetalhada: EcommerceDeliveryAddress;
  enderecoEntregaCompleto: string | null;
  usarEnderecoEntregaDiferente: boolean;
  setUsarEnderecoEntregaDiferente: Dispatch<SetStateAction<boolean>>;
  entregaNome: string;
  entregaCep: string;
  entregaEndereco: string;
  entregaNumero: string;
  entregaComplemento: string;
  entregaBairro: string;
  entregaCidade: string;
  entregaEstado: string;
  setEntregaNome: (value: string) => void;
  setEntregaEndereco: (value: string) => void;
  setEntregaNumero: (value: string) => void;
  setEntregaComplemento: (value: string) => void;
  setEntregaBairro: (value: string) => void;
  setEntregaCidade: (value: string) => void;
  setEntregaEstado: (value: string) => void;
  buscandoCepEntrega: boolean;
  onBuscarCepEntrega: (value: string) => void;
  onSalvarEnderecoEntrega: () => void;
  statusNotificacoes: string | null;
  ativandoNotificacoes: boolean;
  onAtivarNotificacoes: () => void;
  onLogout: () => void;
  excluindoConta: boolean;
  onExcluirConta: (password: string) => Promise<void>;
}

export function ProfileContent(props: ProfileContentProps) {
  return (
    <KeyboardSafeScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ProfileAvatarSection user={props.user} />
      <ProfilePointsCard pontos={props.pontos} valorPontos={props.valorPontos} />
      <ProfileSwitcherSection
        availableProfiles={props.availableProfiles}
        perfilAtual={props.perfilAtual}
        trocandoPerfil={props.trocandoPerfil}
        onTrocarPerfil={props.onTrocarPerfil}
        onAbrirTrocaPerfil={props.onAbrirTrocaPerfil}
      />
      <PersonalDataSection
        user={props.user}
        editando={props.editando}
        setEditando={props.setEditando}
        nome={props.nome}
        setNome={props.setNome}
        telefone={props.telefone}
        setTelefone={props.setTelefone}
        cpf={props.cpf}
        setCpf={props.setCpf}
        salvando={props.salvando}
        onSalvarPerfil={props.onSalvarPerfil}
      />
      <DefaultAddressSection
        user={props.user}
        editandoEndereco={props.editandoEndereco}
        setEditandoEndereco={props.setEditandoEndereco}
        enderecoCompleto={props.enderecoCompleto}
        cep={props.cep}
        rua={props.rua}
        numero={props.numero}
        complemento={props.complemento}
        bairro={props.bairro}
        cidade={props.cidade}
        estado={props.estado}
        setRua={props.setRua}
        setNumero={props.setNumero}
        setComplemento={props.setComplemento}
        setBairro={props.setBairro}
        setCidade={props.setCidade}
        setEstado={props.setEstado}
        buscandoCep={props.buscandoCep}
        onBuscarCep={props.onBuscarCep}
        salvando={props.salvando}
        onSalvarEndereco={props.onSalvarEndereco}
      />
      <DeliveryAddressSection
        editandoEnderecoEntrega={props.editandoEnderecoEntrega}
        setEditandoEnderecoEntrega={props.setEditandoEnderecoEntrega}
        entregaDetalhada={props.entregaDetalhada}
        enderecoEntregaCompleto={props.enderecoEntregaCompleto}
        usarEnderecoEntregaDiferente={props.usarEnderecoEntregaDiferente}
        setUsarEnderecoEntregaDiferente={props.setUsarEnderecoEntregaDiferente}
        entregaNome={props.entregaNome}
        entregaCep={props.entregaCep}
        entregaEndereco={props.entregaEndereco}
        entregaNumero={props.entregaNumero}
        entregaComplemento={props.entregaComplemento}
        entregaBairro={props.entregaBairro}
        entregaCidade={props.entregaCidade}
        entregaEstado={props.entregaEstado}
        setEntregaNome={props.setEntregaNome}
        setEntregaEndereco={props.setEntregaEndereco}
        setEntregaNumero={props.setEntregaNumero}
        setEntregaComplemento={props.setEntregaComplemento}
        setEntregaBairro={props.setEntregaBairro}
        setEntregaCidade={props.setEntregaCidade}
        setEntregaEstado={props.setEntregaEstado}
        buscandoCepEntrega={props.buscandoCepEntrega}
        onBuscarCepEntrega={props.onBuscarCepEntrega}
        salvando={props.salvando}
        onSalvarEnderecoEntrega={props.onSalvarEnderecoEntrega}
      />
      <NotificationsSection
        statusNotificacoes={props.statusNotificacoes}
        ativandoNotificacoes={props.ativandoNotificacoes}
        onAtivarNotificacoes={props.onAtivarNotificacoes}
      />
      <LogoutButton onLogout={props.onLogout} />
      <AccountDeletionSection
        excluindo={props.excluindoConta}
        onExcluirConta={props.onExcluirConta}
      />
      <Text style={styles.versao}>CorePet v1.0.1</Text>
      <View style={{ height: ESPACO.xxl }} />
    </KeyboardSafeScrollView>
  );
}
