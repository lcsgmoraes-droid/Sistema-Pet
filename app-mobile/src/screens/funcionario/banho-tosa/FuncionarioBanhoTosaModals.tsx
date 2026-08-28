import { Ionicons } from "@expo/vector-icons";
import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  BanhoTosaFuncionarioResumo,
  BanhoTosaPetResumo,
  BanhoTosaRecursoResumo,
  BanhoTosaServicoResumo,
  FuncionarioBanhoTosaAtendimento,
} from "../../../services/funcionarioBanhoTosa.service";
import { styles } from "./FuncionarioBanhoTosaStyles";
import { labelEtapa } from "./FuncionarioBanhoTosaUtils";

export type NovoAgendamentoForm = {
  pet_id: string;
  data: string;
  hora: string;
  servico_id: string;
  recurso_id: string;
  valor: string;
  observacoes: string;
};

type NovoAgendamentoProps = {
  visible: boolean;
  form: NovoAgendamentoForm;
  pets: BanhoTosaPetResumo[];
  servicos: BanhoTosaServicoResumo[];
  recursos: BanhoTosaRecursoResumo[];
  salvando: boolean;
  onClose: () => void;
  onChange: (campo: keyof NovoAgendamentoForm, valor: string) => void;
  onSelectServico: (servico: BanhoTosaServicoResumo) => void;
  onSalvar: () => void;
};

export function NovoAgendamentoBanhoTosaModal({
  visible,
  form,
  pets,
  servicos,
  recursos,
  salvando,
  onClose,
  onChange,
  onSelectServico,
  onSalvar,
}: NovoAgendamentoProps) {
  const [buscaPet, setBuscaPet] = useState("");
  const petsFiltrados = useMemo(() => {
    const termo = buscaPet.trim().toLowerCase();
    if (termo.length < 2) return [];
    return pets
      .filter((pet) =>
        [pet.nome, pet.codigo, pet.raca, pet.cliente_nome, pet.cliente_telefone]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(termo),
      )
      .slice(0, 30);
  }, [buscaPet, pets]);
  const petSelecionado = pets.find((pet) => String(pet.id) === form.pet_id);
  const servicoSelecionado = servicos.find((item) => String(item.id) === form.servico_id);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={styles.modalBackdrop}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.modalCard}>
          <View style={styles.modalHeader}>
            <View style={{ flex: 1 }}>
              <Text style={styles.modalTitle}>Novo horario</Text>
              <Text style={styles.modalSubtitle}>Escolha o pet, o servico e o horario.</Text>
            </View>
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Ionicons name="close" size={22} color="#475569" />
            </TouchableOpacity>
          </View>

          <ScrollView keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            <Text style={styles.label}>Pet ou tutor</Text>
            <TextInput
              style={styles.input}
              placeholder="Digite pelo menos 2 letras"
              value={buscaPet}
              onChangeText={setBuscaPet}
            />
            {petSelecionado ? (
              <TouchableOpacity style={[styles.option, styles.optionActive]} onPress={() => onChange("pet_id", "")}>
                <Text style={styles.optionTitle}>{petSelecionado.nome}</Text>
                <Text style={styles.optionText}>{petSelecionado.cliente_nome} · toque para trocar</Text>
              </TouchableOpacity>
            ) : petsFiltrados.length ? (
              <View style={styles.optionList}>
                {petsFiltrados.map((pet) => (
                  <TouchableOpacity
                    key={pet.id}
                    style={styles.option}
                    onPress={() => {
                      onChange("pet_id", String(pet.id));
                      setBuscaPet("");
                    }}
                  >
                    <Text style={styles.optionTitle}>{pet.nome} · {pet.cliente_nome || "Tutor"}</Text>
                    <Text style={styles.optionText}>{pet.raca || pet.especie || "Pet"} · {pet.cliente_telefone || "sem telefone"}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            ) : null}

            <View style={styles.inlineFields}>
              <View style={styles.field}>
                <Text style={styles.label}>Data</Text>
                <TextInput style={styles.input} value={form.data} onChangeText={(value) => onChange("data", value)} placeholder="AAAA-MM-DD" />
              </View>
              <View style={styles.field}>
                <Text style={styles.label}>Hora</Text>
                <TextInput style={styles.input} value={form.hora} onChangeText={(value) => onChange("hora", value)} placeholder="08:00" />
              </View>
            </View>

            <Text style={styles.label}>Servico</Text>
            <View style={styles.optionList}>
              {servicos.map((servico) => {
                const ativo = String(servico.id) === form.servico_id;
                return (
                  <TouchableOpacity
                    key={servico.id}
                    style={[styles.option, ativo && styles.optionActive]}
                    onPress={() => onSelectServico(servico)}
                  >
                    <Text style={styles.optionTitle}>{servico.nome}</Text>
                    <Text style={styles.optionText}>{servico.duracao_padrao_minutos} min · R$ {Number(servico.preco_base || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            {!servicoSelecionado ? <Text style={styles.meta}>Selecione um servico cadastrado no ERP.</Text> : null}

            <Text style={styles.label}>Box ou recurso</Text>
            <View style={styles.optionList}>
              <TouchableOpacity
                style={[styles.option, !form.recurso_id && styles.optionActive]}
                onPress={() => onChange("recurso_id", "")}
              >
                <Text style={styles.optionTitle}>Definir depois</Text>
              </TouchableOpacity>
              {recursos.map((recurso) => (
                <TouchableOpacity
                  key={recurso.id}
                  style={[styles.option, String(recurso.id) === form.recurso_id && styles.optionActive]}
                  onPress={() => onChange("recurso_id", String(recurso.id))}
                >
                  <Text style={styles.optionTitle}>{recurso.nome}</Text>
                  <Text style={styles.optionText}>{recurso.tipo} · capacidade {recurso.capacidade_simultanea}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>Valor previsto</Text>
            <TextInput
              style={styles.input}
              keyboardType="decimal-pad"
              value={form.valor}
              onChangeText={(value) => onChange("valor", value)}
              placeholder="0,00"
            />

            <Text style={styles.label}>Observacoes</Text>
            <TextInput
              style={[styles.input, styles.multiline]}
              multiline
              value={form.observacoes}
              onChangeText={(value) => onChange("observacoes", value)}
              placeholder="Alergias, comportamento ou pedido do tutor"
            />

            <View style={styles.modalFooter}>
              <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
                <Text style={styles.cancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                disabled={salvando}
                style={[styles.saveButton, salvando && styles.primaryButtonDisabled]}
                onPress={onSalvar}
              >
                {salvando ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.saveText}>Criar agendamento</Text>}
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

export type TransicaoBanhoTosaForm = {
  responsavel_id: string;
  recurso_id: string;
  observacoes: string;
};

type TransicaoProps = {
  atendimento: FuncionarioBanhoTosaAtendimento | null;
  form: TransicaoBanhoTosaForm;
  funcionarios: BanhoTosaFuncionarioResumo[];
  recursos: BanhoTosaRecursoResumo[];
  salvando: boolean;
  onClose: () => void;
  onChange: (campo: keyof TransicaoBanhoTosaForm, valor: string) => void;
  onConfirmar: () => void;
};

export function TransicaoBanhoTosaModal({
  atendimento,
  form,
  funcionarios,
  recursos,
  salvando,
  onClose,
  onChange,
  onConfirmar,
}: TransicaoProps) {
  if (!atendimento?.proxima_etapa_codigo) return null;
  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalCard}>
          <View style={styles.modalHeader}>
            <View style={{ flex: 1 }}>
              <Text style={styles.modalTitle}>
                {atendimento.pet_nome} → {labelEtapa(atendimento.proxima_etapa_codigo)}
              </Text>
              <Text style={styles.modalSubtitle}>Confirme quem assume e onde o pet ficara.</Text>
            </View>
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Ionicons name="close" size={22} color="#475569" />
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false}>
            <Text style={styles.label}>Responsavel</Text>
            <View style={styles.optionList}>
              {funcionarios.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={[styles.option, String(item.id) === form.responsavel_id && styles.optionActive]}
                  onPress={() => onChange("responsavel_id", String(item.id))}
                >
                  <Text style={styles.optionTitle}>{item.nome}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>Box ou recurso</Text>
            <View style={styles.optionList}>
              <TouchableOpacity style={[styles.option, !form.recurso_id && styles.optionActive]} onPress={() => onChange("recurso_id", "")}>
                <Text style={styles.optionTitle}>Sem recurso definido</Text>
              </TouchableOpacity>
              {recursos.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={[styles.option, String(item.id) === form.recurso_id && styles.optionActive]}
                  onPress={() => onChange("recurso_id", String(item.id))}
                >
                  <Text style={styles.optionTitle}>{item.nome}</Text>
                  <Text style={styles.optionText}>{item.tipo}</Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.label}>Observacao da etapa</Text>
            <TextInput
              style={[styles.input, styles.multiline]}
              multiline
              value={form.observacoes}
              onChangeText={(value) => onChange("observacoes", value)}
              placeholder="Ex.: usar shampoo hipoalergenico"
            />

            <View style={styles.modalFooter}>
              <TouchableOpacity style={styles.cancelButton} onPress={onClose}>
                <Text style={styles.cancelText}>Voltar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                disabled={salvando}
                style={[styles.saveButton, salvando && styles.primaryButtonDisabled]}
                onPress={onConfirmar}
              >
                {salvando ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.saveText}>Iniciar etapa</Text>}
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
