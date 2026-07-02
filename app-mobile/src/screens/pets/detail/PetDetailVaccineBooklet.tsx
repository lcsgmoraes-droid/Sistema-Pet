import { Ionicons } from "@expo/vector-icons";
import React, { useState } from "react";
import { Image, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import type { Pet, VacinaCarteirinha } from "../../../types";
import { formatarData } from "../../../utils/format";
import { petDetailStyles as styles } from "./PetDetailStyles";
import { corStatusVacina, formatarIdadePet, labelStatusVacina, resumirHash } from "./PetDetailUtils";

const VACINAS_POR_PAGINA = 4;

export function PetDetailVaccineBooklet({
  pet,
  vacinas,
  onPressVacina,
}: {
  pet: Pet;
  vacinas: VacinaCarteirinha[];
  onPressVacina: (vacina: VacinaCarteirinha) => void;
}) {
  const [pagina, setPagina] = useState(0);
  const totalPaginas = Math.max(1, Math.ceil(vacinas.length / VACINAS_POR_PAGINA));
  const inicio = pagina * VACINAS_POR_PAGINA;
  const vacinasDaPagina = vacinas.slice(inicio, inicio + VACINAS_POR_PAGINA);
  const slots = Array.from({ length: VACINAS_POR_PAGINA }, (_, index) => vacinasDaPagina[index] || null);

  return (
    <View>
      <View style={styles.folhetoCarteira}>
        <View style={styles.folhetoPaws}>
          {Array.from({ length: 8 }).map((_, index) => (
            <Ionicons key={`paw_top_${index}`} name="paw-outline" size={13} color="rgba(255,255,255,0.9)" />
          ))}
        </View>

        <View style={styles.folhetoIdentidade}>
          <View style={{ flex: 1 }}>
            <Text style={styles.folhetoLabel}>Carteira digital de vacinas</Text>
            <Text style={styles.folhetoPetNome}>{pet.nome}</Text>
            <Text style={styles.folhetoPetInfo}>
              {pet.especie || 'Pet'}{pet.raca ? ` - ${pet.raca}` : ''} - {formatarIdadePet(pet)}
            </Text>
            <Text style={styles.folhetoPetInfo}>
              Tutor: dados vinculados ao cadastro do app
            </Text>
          </View>
          {pet.foto_url ? (
            <Image source={{ uri: pet.foto_url }} style={styles.folhetoFoto} />
          ) : (
            <View style={[styles.folhetoFoto, styles.folhetoFotoPlaceholder]}>
              <Ionicons name="paw" size={32} color="#16A34A" />
            </View>
          )}
        </View>

        <View style={styles.folhetoSlots}>
          {slots.map((vacina, index) => (
            <VacinaFolhetoSlot
              key={vacina?.id || `slot_${pagina}_${index}`}
              vacina={vacina}
              onPress={() => vacina && onPressVacina(vacina)}
            />
          ))}
        </View>

        <View style={styles.folhetoPaws}>
          {Array.from({ length: 8 }).map((_, index) => (
            <Ionicons key={`paw_bottom_${index}`} name="paw-outline" size={13} color="rgba(255,255,255,0.9)" />
          ))}
        </View>
      </View>

      {totalPaginas > 1 && (
        <View style={styles.folhetoPaginacao}>
          <TouchableOpacity
            style={[styles.folhetoPaginaBotao, pagina === 0 && styles.folhetoPaginaBotaoDisabled]}
            disabled={pagina === 0}
            onPress={() => setPagina((atual) => Math.max(0, atual - 1))}
          >
            <Ionicons name="chevron-back" size={16} color={pagina === 0 ? CORES.textoClaro : CORES.primario} />
            <Text style={[styles.folhetoPaginaTexto, pagina === 0 && styles.folhetoPaginaTextoDisabled]}>Anterior</Text>
          </TouchableOpacity>
          <Text style={styles.folhetoPaginaInfo}>Pagina {pagina + 1} de {totalPaginas}</Text>
          <TouchableOpacity
            style={[styles.folhetoPaginaBotao, pagina >= totalPaginas - 1 && styles.folhetoPaginaBotaoDisabled]}
            disabled={pagina >= totalPaginas - 1}
            onPress={() => setPagina((atual) => Math.min(totalPaginas - 1, atual + 1))}
          >
            <Text style={[styles.folhetoPaginaTexto, pagina >= totalPaginas - 1 && styles.folhetoPaginaTextoDisabled]}>Proxima</Text>
            <Ionicons name="chevron-forward" size={16} color={pagina >= totalPaginas - 1 ? CORES.textoClaro : CORES.primario} />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

function VacinaFolhetoSlot({
  vacina,
  onPress,
}: {
  vacina: VacinaCarteirinha | null;
  onPress: () => void;
}) {
  if (!vacina) {
    return (
      <View style={[styles.folhetoVacinaSlot, styles.folhetoVacinaSlotVazio]}>
        <Text style={styles.folhetoSlotTitulo}>Espaco livre</Text>
        <Text style={styles.folhetoSlotTexto}>Proxima vacina registrada aparece aqui.</Text>
      </View>
    );
  }

  const corStatus = corStatusVacina(vacina.status);
  return (
    <TouchableOpacity style={styles.folhetoVacinaSlot} onPress={onPress} activeOpacity={0.86}>
      <View style={styles.folhetoSlotHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.folhetoSlotLabel}>Vacina</Text>
          <Text style={styles.folhetoSlotTitulo}>{vacina.nome}</Text>
        </View>
        <View style={[styles.folhetoStatusPill, { borderColor: corStatus }]}>
          <Text style={[styles.folhetoStatusTexto, { color: corStatus }]}>
            {labelStatusVacina(vacina.status)}
          </Text>
        </View>
      </View>

      <View style={styles.folhetoSlotGrid}>
        <FolhetoInfo label="Data" valor={formatarData(vacina.data_aplicacao)} />
        <FolhetoInfo label="Repetir em" valor={formatarData(vacina.data_proxima_dose)} />
        <FolhetoInfo label="Dose" valor={vacina.numero_dose ? `${vacina.numero_dose}` : '-'} />
        <FolhetoInfo label="Lote" valor={vacina.lote || '-'} />
      </View>

      <View style={styles.folhetoAssinatura}>
        <View style={styles.folhetoQr}>
          <Ionicons name="qr-code-outline" size={24} color="#15803D" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.folhetoAssinaturaTitulo}>Assinatura digital</Text>
          <Text style={styles.folhetoAssinaturaTexto}>
            {vacina.veterinario_nome || 'Veterinario nao informado'}
          </Text>
          <Text style={styles.folhetoAssinaturaHash}>{resumirHash(vacina.hash_validacao)}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

function FolhetoInfo({ label, valor }: { label: string; valor: string }) {
  return (
    <View style={styles.folhetoInfoBox}>
      <Text style={styles.folhetoInfoLabel}>{label}</Text>
      <Text style={styles.folhetoInfoValor}>{valor}</Text>
    </View>
  );
}

