import { Ionicons } from "@expo/vector-icons";
import React from "react";
import {
  Modal,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { VetConsultorio, VetPetResumo } from "../../../services/vet.service";
import { CORES } from "../../../theme";
import { vetAgendaStyles as styles } from "./VetAgendaStyles";
import {
  DIAS_SEMANA,
  formatarDataIsoParaBr,
  isoDate,
  mesAnoCalendario,
  MIN_CARACTERES_BUSCA_PET,
  VetAgendaCalendarDay,
  VetAgendaField,
  VetAgendaForm,
} from "./VetAgendaUtils";

type VetAgendaAppointmentModalProps = {
  visible: boolean;
  buscaPet: string;
  form: VetAgendaForm;
  consultorios: VetConsultorio[];
  petsFiltrados: VetPetResumo[];
  carregandoApoios: boolean;
  calendarioAberto: boolean;
  calendarioReferencia: string;
  calendarioDias: VetAgendaCalendarDay[];
  horariosBase: string[];
  horariosOcupados: Set<string>;
  salvandoNovo: boolean;
  onClose: () => void;
  onBuscaPetChange: (value: string) => void;
  onAtualizarCampo: (campo: VetAgendaField, valor: string) => void;
  onAbrirCalendario: () => void;
  onNavegarMesCalendario: (delta: number) => void;
  onSelecionarDataCalendario: (data: string) => void;
  onSalvar: () => void;
};

export function VetAgendaAppointmentModal({
  visible,
  buscaPet,
  form,
  consultorios,
  petsFiltrados,
  carregandoApoios,
  calendarioAberto,
  calendarioReferencia,
  calendarioDias,
  horariosBase,
  horariosOcupados,
  salvandoNovo,
  onClose,
  onBuscaPetChange,
  onAtualizarCampo,
  onAbrirCalendario,
  onNavegarMesCalendario,
  onSelecionarDataCalendario,
  onSalvar,
}: VetAgendaAppointmentModalProps) {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalCard}>
          <ScrollView contentContainerStyle={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Agendar consulta</Text>
              <TouchableOpacity onPress={onClose}>
                <Text style={styles.closeText}>Fechar</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>Buscar pet</Text>
            <TextInput
              value={buscaPet}
              onChangeText={onBuscaPetChange}
              placeholder="Digite nome, codigo, tutor ou telefone"
              placeholderTextColor={CORES.textoSecundario}
              style={styles.input}
            />

            <View style={styles.petList}>
              {carregandoApoios && (
                <Text style={styles.emptyInline}>Carregando pets...</Text>
              )}
              {!carregandoApoios &&
                buscaPet.trim().length < MIN_CARACTERES_BUSCA_PET && (
                  <Text style={styles.emptyInline}>
                    Digite pelo menos 2 caracteres para buscar o pet.
                  </Text>
                )}
              {!carregandoApoios &&
                petsFiltrados.map((pet) => {
                  const ativo = String(pet.id) === form.pet_id;
                  return (
                    <TouchableOpacity
                      key={pet.id}
                      style={[
                        styles.petOption,
                        ativo && styles.petOptionActive,
                      ]}
                      onPress={() => onAtualizarCampo("pet_id", String(pet.id))}
                    >
                      <Text
                        style={[
                          styles.petOptionTitle,
                          ativo && styles.petOptionTitleActive,
                        ]}
                      >
                        {pet.nome || `Pet #${pet.id}`}
                      </Text>
                      <Text style={styles.petOptionText}>
                        {[pet.cliente_nome, pet.raca || pet.especie, pet.codigo]
                          .filter(Boolean)
                          .join(" | ") || "Sem detalhes"}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              {!carregandoApoios &&
                buscaPet.trim().length >= MIN_CARACTERES_BUSCA_PET &&
                !petsFiltrados.length && (
                  <Text style={styles.emptyInline}>Nenhum pet encontrado.</Text>
                )}
            </View>

            <Text style={styles.label}>Consultorio</Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.chipsRow}
            >
              <TouchableOpacity
                style={[styles.chip, !form.consultorio_id && styles.chipActive]}
                onPress={() => onAtualizarCampo("consultorio_id", "")}
              >
                <Text
                  style={[
                    styles.chipText,
                    !form.consultorio_id && styles.chipTextActive,
                  ]}
                >
                  Sem sala
                </Text>
              </TouchableOpacity>
              {consultorios.map((consultorio) => {
                const ativo = String(consultorio.id) === form.consultorio_id;
                return (
                  <TouchableOpacity
                    key={consultorio.id}
                    style={[styles.chip, ativo && styles.chipActive]}
                    onPress={() =>
                      onAtualizarCampo("consultorio_id", String(consultorio.id))
                    }
                  >
                    <Text
                      style={[styles.chipText, ativo && styles.chipTextActive]}
                    >
                      {consultorio.nome}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>

            <Text style={styles.label}>Data</Text>
            <TouchableOpacity
              style={styles.dateInputWrap}
              onPress={onAbrirCalendario}
              activeOpacity={0.85}
            >
              <TextInput
                value={formatarDataIsoParaBr(form.data)}
                placeholder="dd/mm/aaaa"
                placeholderTextColor={CORES.textoSecundario}
                style={styles.dateInputText}
                editable={false}
                pointerEvents="none"
              />
              <Ionicons
                name="calendar-outline"
                size={20}
                color={CORES.primario}
              />
            </TouchableOpacity>

            {calendarioAberto && (
              <View style={styles.calendarCard}>
                <View style={styles.calendarHeader}>
                  <TouchableOpacity
                    style={styles.calendarNavButton}
                    onPress={() => onNavegarMesCalendario(-1)}
                  >
                    <Ionicons
                      name="chevron-back"
                      size={20}
                      color={CORES.primario}
                    />
                  </TouchableOpacity>
                  <Text style={styles.calendarTitle}>
                    {mesAnoCalendario(calendarioReferencia)}
                  </Text>
                  <TouchableOpacity
                    style={styles.calendarNavButton}
                    onPress={() => onNavegarMesCalendario(1)}
                  >
                    <Ionicons
                      name="chevron-forward"
                      size={20}
                      color={CORES.primario}
                    />
                  </TouchableOpacity>
                </View>

                <View style={styles.calendarWeekRow}>
                  {DIAS_SEMANA.map((dia, index) => (
                    <Text
                      key={`${dia}-${index}`}
                      style={styles.calendarWeekText}
                    >
                      {dia}
                    </Text>
                  ))}
                </View>

                <View style={styles.calendarGrid}>
                  {calendarioDias.map((dia) => (
                    <TouchableOpacity
                      key={dia.key}
                      style={[
                        styles.calendarDay,
                        dia.foraMes && styles.calendarDayOutside,
                        dia.hoje && styles.calendarDayToday,
                        dia.selecionado && styles.calendarDaySelected,
                      ]}
                      onPress={() => onSelecionarDataCalendario(dia.data)}
                    >
                      <Text
                        style={[
                          styles.calendarDayText,
                          dia.foraMes && styles.calendarDayOutsideText,
                          dia.selecionado && styles.calendarDaySelectedText,
                        ]}
                      >
                        {dia.dia}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <TouchableOpacity
                  style={styles.calendarTodayButton}
                  onPress={() =>
                    onSelecionarDataCalendario(isoDate(new Date()))
                  }
                >
                  <Text style={styles.calendarTodayText}>Hoje</Text>
                </TouchableOpacity>
              </View>
            )}

            <Text style={styles.label}>Horario</Text>
            <View style={styles.slotsGrid}>
              {horariosBase.map((horario) => {
                const ocupado = horariosOcupados.has(horario);
                const selecionado = form.hora === horario;
                return (
                  <TouchableOpacity
                    key={horario}
                    style={[
                      styles.slot,
                      ocupado ? styles.slotOcupado : styles.slotLivre,
                      selecionado && styles.slotSelecionado,
                    ]}
                    onPress={() => onAtualizarCampo("hora", horario)}
                  >
                    <Text style={styles.slotText}>{horario}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <View style={styles.legendRow}>
              <Text style={styles.legendLivre}>Livre</Text>
              <Text style={styles.legendOcupado}>Marcado</Text>
            </View>

            <View style={styles.twoColumns}>
              <View style={styles.flexField}>
                <Text style={styles.label}>Duracao</Text>
                <TextInput
                  value={form.duracao_minutos}
                  onChangeText={(value) =>
                    onAtualizarCampo("duracao_minutos", value)
                  }
                  keyboardType="number-pad"
                  placeholder="30"
                  placeholderTextColor={CORES.textoSecundario}
                  style={styles.input}
                />
              </View>
              <View style={styles.flexField}>
                <Text style={styles.label}>Tipo</Text>
                <View style={styles.readonlyField}>
                  <Text style={styles.readonlyText}>Consulta</Text>
                </View>
              </View>
            </View>

            <Text style={styles.label}>Motivo</Text>
            <TextInput
              value={form.motivo}
              onChangeText={(value) => onAtualizarCampo("motivo", value)}
              placeholder="Ex: retorno, avaliacao, vacina..."
              placeholderTextColor={CORES.textoSecundario}
              style={[styles.input, styles.textArea]}
              multiline
            />

            <TouchableOpacity
              style={[
                styles.saveButton,
                (salvandoNovo || carregandoApoios) && styles.disabledButton,
              ]}
              onPress={onSalvar}
              disabled={salvandoNovo || carregandoApoios}
            >
              <Text style={styles.saveButtonText}>
                {salvandoNovo ? "Salvando..." : "Agendar consulta"}
              </Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
