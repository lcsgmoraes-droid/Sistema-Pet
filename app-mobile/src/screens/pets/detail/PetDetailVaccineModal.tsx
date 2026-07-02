import { Ionicons } from "@expo/vector-icons";
import { Modal, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import type { Pet, VacinaCarteirinha } from "../../../types";
import { formatarData } from "../../../utils/format";
import { petDetailStyles as styles } from "./PetDetailStyles";
import { corStatusVacina, formatarIdadePet, labelStatusVacina, resumirHash } from "./PetDetailUtils";

export function PetDetailVaccineModal({
  vacina,
  pet,
  onClose,
}: {
  vacina: VacinaCarteirinha | null;
  pet: Pet;
  onClose: () => void;
}) {
  if (!vacina) return null;
  const corStatus = corStatusVacina(vacina.status);

  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <View style={styles.modalCard}>
          <View style={styles.modalHeader}>
            <View>
              <Text style={styles.modalTitulo}>Carteira de vacina</Text>
              <Text style={styles.modalSubtitulo}>{pet.nome} - {formatarIdadePet(pet)}</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.modalCloseButton}>
              <Ionicons name="close" size={22} color={CORES.texto} />
            </TouchableOpacity>
          </View>

          <View style={styles.carteiraVirtual}>
            <View style={styles.carteiraTopLine}>
              <View>
                <Text style={styles.carteiraPetNome}>{pet.nome}</Text>
                <Text style={styles.itemMeta}>{pet.especie}{pet.raca ? ` - ${pet.raca}` : ''}</Text>
              </View>
              <View style={[styles.carteiraStamp, { borderColor: corStatus }]}>
                <Text style={[styles.carteiraStampTexto, { color: corStatus }]}>
                  {labelStatusVacina(vacina.status)}
                </Text>
              </View>
            </View>

            <Text style={styles.carteiraVacinaNome}>{vacina.nome}</Text>

            <View style={styles.carteiraInfoGrid}>
              <InfoLinha label="Data" valor={formatarData(vacina.data_aplicacao)} />
              <InfoLinha label="Proxima dose" valor={formatarData(vacina.data_proxima_dose)} />
              <InfoLinha label="Dose" valor={vacina.numero_dose ? `${vacina.numero_dose}` : '-'} />
              <InfoLinha label="Lote" valor={vacina.lote || '-'} />
              <InfoLinha label="Fabricante" valor={vacina.fabricante || '-'} />
              <InfoLinha label="Validacao" valor={vacina.assinatura_digital || resumirHash(vacina.hash_validacao)} />
            </View>

            <View style={styles.assinaturaBox}>
              <Ionicons name="pencil-outline" size={18} color={CORES.primario} />
              <View style={{ flex: 1 }}>
                <Text style={styles.assinaturaTitulo}>Assinatura digital</Text>
                <Text style={styles.assinaturaNome}>
                  {vacina.veterinario_nome || 'Veterinario nao informado'}
                </Text>
                <Text style={styles.assinaturaCodigo}>
                  {vacina.assinatura_valida ? 'Registro validado' : 'Assinatura pendente'}
                </Text>
              </View>
            </View>

            {!!vacina.hash_validacao && (
              <Text style={styles.hashTexto}>Hash: {resumirHash(vacina.hash_validacao)}</Text>
            )}
          </View>

          <TouchableOpacity style={styles.fecharModal} onPress={onClose}>
            <Text style={styles.fecharModalTexto}>Fechar carteira</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

function InfoLinha({ label, valor }: { label: string; valor: string }) {
  return (
    <View style={styles.carteiraInfoBox}>
      <Text style={styles.carteiraInfoLabel}>{label}</Text>
      <Text style={styles.carteiraInfoValor}>{valor}</Text>
    </View>
  );
}

