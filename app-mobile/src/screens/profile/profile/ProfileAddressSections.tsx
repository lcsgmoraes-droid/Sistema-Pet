import { Ionicons } from "@expo/vector-icons";
import React, { type Dispatch, type SetStateAction } from "react";
import { Text, TextInput, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import type { EcommerceDeliveryAddress, EcommerceUser } from "../../../types";
import { Campo, SaveButton, SectionHeader } from "./ProfileSharedComponents";
import { profileStyles as styles } from "./ProfileStyles";

export function DefaultAddressSection({
  user,
  editandoEndereco,
  setEditandoEndereco,
  enderecoCompleto,
  cep,
  rua,
  numero,
  complemento,
  bairro,
  cidade,
  estado,
  setRua,
  setNumero,
  setComplemento,
  setBairro,
  setCidade,
  setEstado,
  buscandoCep,
  onBuscarCep,
  salvando,
  onSalvarEndereco,
}: {
  user: EcommerceUser | null;
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
  salvando: boolean;
  onSalvarEndereco: () => void;
}) {
  return (
    <View style={styles.secao}>
      <SectionHeader
        title="Endereco padrao"
        editing={editandoEndereco}
        empty={!enderecoCompleto}
        onEdit={() => setEditandoEndereco(true)}
        onCancel={() => setEditandoEndereco(false)}
      />

      {editandoEndereco ? (
        <>
          <Campo label={buscandoCep ? "CEP (buscando...)" : "CEP"}>
            <TextInput
              style={styles.input}
              value={cep}
              onChangeText={onBuscarCep}
              placeholder="00000-000"
              placeholderTextColor={CORES.textoClaro}
              keyboardType="numeric"
              maxLength={9}
            />
          </Campo>
          <Campo label="Rua / Avenida">
            <TextInput
              style={styles.input}
              value={rua}
              onChangeText={setRua}
              placeholder="Rua..."
              placeholderTextColor={CORES.textoClaro}
            />
          </Campo>
          <View style={styles.linha}>
            <View style={{ flex: 1 }}>
              <Campo label="Numero">
                <TextInput
                  style={styles.input}
                  value={numero}
                  onChangeText={setNumero}
                  placeholder="123"
                  placeholderTextColor={CORES.textoClaro}
                  keyboardType="numeric"
                />
              </Campo>
            </View>
            <View style={{ flex: 2 }}>
              <Campo label="Complemento">
                <TextInput
                  style={styles.input}
                  value={complemento}
                  onChangeText={setComplemento}
                  placeholder="Apto, bloco, casa..."
                  placeholderTextColor={CORES.textoClaro}
                />
              </Campo>
            </View>
          </View>
          <Campo label="Bairro">
            <TextInput
              style={styles.input}
              value={bairro}
              onChangeText={setBairro}
              placeholder="Bairro"
              placeholderTextColor={CORES.textoClaro}
            />
          </Campo>
          <View style={styles.linha}>
            <View style={{ flex: 2 }}>
              <Campo label="Cidade">
                <TextInput
                  style={styles.input}
                  value={cidade}
                  onChangeText={setCidade}
                  placeholder="Cidade"
                  placeholderTextColor={CORES.textoClaro}
                />
              </Campo>
            </View>
            <View style={{ flex: 1 }}>
              <Campo label="UF">
                <TextInput
                  style={styles.input}
                  value={estado}
                  onChangeText={setEstado}
                  placeholder="SP"
                  placeholderTextColor={CORES.textoClaro}
                  autoCapitalize="characters"
                  maxLength={2}
                />
              </Campo>
            </View>
          </View>
          <SaveButton label="Salvar endereco" loading={salvando} onPress={onSalvarEndereco} />
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
        <Text style={styles.textoSuporte}>
          Cadastre seu endereco para agilizar o checkout de entregas.
        </Text>
      )}
    </View>
  );
}

export function DeliveryAddressSection({
  editandoEnderecoEntrega,
  setEditandoEnderecoEntrega,
  entregaDetalhada,
  enderecoEntregaCompleto,
  usarEnderecoEntregaDiferente,
  setUsarEnderecoEntregaDiferente,
  entregaNome,
  entregaCep,
  entregaEndereco,
  entregaNumero,
  entregaComplemento,
  entregaBairro,
  entregaCidade,
  entregaEstado,
  setEntregaNome,
  setEntregaEndereco,
  setEntregaNumero,
  setEntregaComplemento,
  setEntregaBairro,
  setEntregaCidade,
  setEntregaEstado,
  buscandoCepEntrega,
  onBuscarCepEntrega,
  salvando,
  onSalvarEnderecoEntrega,
}: {
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
  salvando: boolean;
  onSalvarEnderecoEntrega: () => void;
}) {
  return (
    <View style={styles.secao}>
      <SectionHeader
        title="Endereco de entrega"
        editing={editandoEnderecoEntrega}
        empty={!enderecoEntregaCompleto}
        onEdit={() => setEditandoEnderecoEntrega(true)}
        onCancel={() => setEditandoEnderecoEntrega(false)}
      />

      {editandoEnderecoEntrega ? (
        <>
          <TouchableOpacity
            style={styles.toggleLinha}
            onPress={() => setUsarEnderecoEntregaDiferente((valor) => !valor)}
          >
            <Ionicons
              name={usarEnderecoEntregaDiferente ? "checkbox-outline" : "square-outline"}
              size={22}
              color={usarEnderecoEntregaDiferente ? CORES.primario : CORES.textoSecundario}
            />
            <Text style={styles.toggleTexto}>Usar endereco de entrega diferente</Text>
          </TouchableOpacity>

          {usarEnderecoEntregaDiferente ? (
            <DeliveryAddressForm
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
              onBuscarCepEntrega={onBuscarCepEntrega}
            />
          ) : (
            <Text style={styles.textoSuporte}>
              A entrega vai usar o endereco padrao cadastrado acima.
            </Text>
          )}

          <SaveButton
            label="Salvar endereco de entrega"
            loading={salvando}
            onPress={onSalvarEnderecoEntrega}
          />
        </>
      ) : enderecoEntregaCompleto ? (
        <View style={styles.enderecoCard}>
          <Ionicons name="cube" size={20} color={CORES.primario} />
          <View style={{ flex: 1 }}>
            <Text style={styles.enderecoTexto}>{enderecoEntregaCompleto}</Text>
            {entregaDetalhada.entrega_nome && (
              <Text style={styles.enderecoSub}>Recebe: {entregaDetalhada.entrega_nome}</Text>
            )}
            {entregaDetalhada.entrega_cep && (
              <Text style={styles.enderecoSub}>CEP: {entregaDetalhada.entrega_cep}</Text>
            )}
          </View>
        </View>
      ) : (
        <Text style={styles.textoSuporte}>
          Por enquanto, a entrega usa o endereco padrao. Cadastre outro endereco se precisar.
        </Text>
      )}
    </View>
  );
}

function DeliveryAddressForm({
  entregaNome,
  entregaCep,
  entregaEndereco,
  entregaNumero,
  entregaComplemento,
  entregaBairro,
  entregaCidade,
  entregaEstado,
  setEntregaNome,
  setEntregaEndereco,
  setEntregaNumero,
  setEntregaComplemento,
  setEntregaBairro,
  setEntregaCidade,
  setEntregaEstado,
  buscandoCepEntrega,
  onBuscarCepEntrega,
}: {
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
}) {
  return (
    <>
      <Campo label="Nome para entrega">
        <TextInput
          style={styles.input}
          value={entregaNome}
          onChangeText={setEntregaNome}
          placeholder="Nome de quem recebe"
          placeholderTextColor={CORES.textoClaro}
        />
      </Campo>
      <Campo label={buscandoCepEntrega ? "CEP da entrega (buscando...)" : "CEP da entrega"}>
        <TextInput
          style={styles.input}
          value={entregaCep}
          onChangeText={onBuscarCepEntrega}
          placeholder="00000-000"
          placeholderTextColor={CORES.textoClaro}
          keyboardType="numeric"
          maxLength={9}
        />
      </Campo>
      <Campo label="Rua / Avenida da entrega">
        <TextInput
          style={styles.input}
          value={entregaEndereco}
          onChangeText={setEntregaEndereco}
          placeholder="Rua..."
          placeholderTextColor={CORES.textoClaro}
        />
      </Campo>
      <View style={styles.linha}>
        <View style={{ flex: 1 }}>
          <Campo label="Numero da entrega">
            <TextInput
              style={styles.input}
              value={entregaNumero}
              onChangeText={setEntregaNumero}
              placeholder="123"
              placeholderTextColor={CORES.textoClaro}
              keyboardType="numeric"
            />
          </Campo>
        </View>
        <View style={{ flex: 2 }}>
          <Campo label="Complemento da entrega">
            <TextInput
              style={styles.input}
              value={entregaComplemento}
              onChangeText={setEntregaComplemento}
              placeholder="Apto, bloco, casa..."
              placeholderTextColor={CORES.textoClaro}
            />
          </Campo>
        </View>
      </View>
      <Campo label="Bairro da entrega">
        <TextInput
          style={styles.input}
          value={entregaBairro}
          onChangeText={setEntregaBairro}
          placeholder="Bairro"
          placeholderTextColor={CORES.textoClaro}
        />
      </Campo>
      <View style={styles.linha}>
        <View style={{ flex: 2 }}>
          <Campo label="Cidade da entrega">
            <TextInput
              style={styles.input}
              value={entregaCidade}
              onChangeText={setEntregaCidade}
              placeholder="Cidade"
              placeholderTextColor={CORES.textoClaro}
            />
          </Campo>
        </View>
        <View style={{ flex: 1 }}>
          <Campo label="UF">
            <TextInput
              style={styles.input}
              value={entregaEstado}
              onChangeText={setEntregaEstado}
              placeholder="SP"
              placeholderTextColor={CORES.textoClaro}
              autoCapitalize="characters"
              maxLength={2}
            />
          </Campo>
        </View>
      </View>
    </>
  );
}
