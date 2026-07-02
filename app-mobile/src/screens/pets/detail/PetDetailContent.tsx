import { Ionicons } from "@expo/vector-icons";
import React, { type Dispatch, type SetStateAction } from "react";
import { ActivityIndicator, Image, type LayoutChangeEvent, ScrollView, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import type { Pet, PetCarteirinha, VacinaCarteirinha, VetFocusSection } from "../../../types";
import { formatarData } from "../../../utils/format";
import {
  PetDetailQuickNavButton as QuickNavButton,
  PetDetailResumoCard as ResumoCard,
  PetDetailSection as Section,
} from "./PetDetailSharedComponents";
import { petDetailStyles as styles } from "./PetDetailStyles";
import { formatarIdadePet } from "./PetDetailUtils";
import { PetDetailVaccineBooklet as CarteirinhaVacinasFolheto } from "./PetDetailVaccineBooklet";
import { PetDetailVaccineModal as CarteiraVacinaModal } from "./PetDetailVaccineModal";

export type PetDetailContentProps = {
  scrollRef: React.RefObject<ScrollView | null>;
  petAtual: Pet;
  dados: PetCarteirinha | null;
  loading: boolean;
  vacinaSelecionada: VacinaCarteirinha | null;
  setVacinaSelecionada: Dispatch<SetStateAction<VacinaCarteirinha | null>>;
  navigation: any;
  registrarSection: (section: VetFocusSection) => (event: LayoutChangeEvent) => void;
  scrollToSection: (section: VetFocusSection) => void;
  abrirArquivo: (url?: string | null) => void | Promise<void>;
};

export function PetDetailContent({
  scrollRef,
  petAtual,
  dados,
  loading,
  vacinaSelecionada,
  setVacinaSelecionada,
  navigation,
  registrarSection,
  scrollToSection,
  abrirArquivo,
}: PetDetailContentProps) {
  return (
    <ScrollView ref={scrollRef} style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.headerCard}>
        {petAtual.foto_url ? (
          <Image source={{ uri: petAtual.foto_url }} style={styles.foto} />
        ) : (
          <View style={[styles.foto, styles.fotoPlaceholder]}>
            <Text style={styles.fotoEmoji}>{petAtual.especie === 'gato' ? '🐱' : '🐶'}</Text>
          </View>
        )}

        <View style={{ flex: 1 }}>
          <Text style={styles.nome}>{petAtual.nome}</Text>
          <Text style={styles.subtitulo}>
            {petAtual.especie}
            {petAtual.raca ? ` · ${petAtual.raca}` : ''}
          </Text>
          <Text style={styles.subtitulo}>{formatarIdadePet(petAtual)}</Text>
          {!!petAtual.tipo_sanguineo && (
            <Text style={styles.subtitulo}>Tipo sanguineo: {petAtual.tipo_sanguineo}</Text>
          )}
        </View>

        <TouchableOpacity
          style={styles.botaoEditar}
          onPress={() => navigation.navigate('FormPet', { pet: petAtual })}
        >
          <Ionicons name="create-outline" size={18} color={CORES.primario} />
        </TouchableOpacity>
      </View>

      <View style={styles.quickNavRow}>
        <QuickNavButton
          icon="medkit-outline"
          label="Vacinas"
          onPress={() => scrollToSection('vacinas')}
        />
        <QuickNavButton
          icon="document-text-outline"
          label="Exames"
          onPress={() => scrollToSection('exames')}
        />
        <QuickNavButton
          icon="calendar-outline"
          label="Consultas"
          onPress={() => scrollToSection('consultas')}
        />
      </View>

      {loading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={CORES.primario} />
          <Text style={styles.loadingText}>Carregando saude veterinaria...</Text>
        </View>
      ) : (
        <>
          <View style={styles.resumoGrid}>
            <ResumoCard
              titulo="Vacinas"
              valor={String(dados?.status_vacinal?.resumo?.total_aplicadas ?? 0)}
              cor={CORES.primario}
            />
            <ResumoCard
              titulo="Pendentes"
              valor={String(dados?.status_vacinal?.resumo?.total_pendentes ?? 0)}
              cor="#B7791F"
            />
            <ResumoCard
              titulo="Atrasadas"
              valor={String(dados?.status_vacinal?.resumo?.total_vencidas ?? 0)}
              cor={CORES.erro}
            />
          </View>

          {!!dados?.alertas?.length && (
            <Section titulo="Alertas importantes">
              {dados.alertas.map((alerta, idx) => (
                <View key={`alerta_${idx}`} style={styles.alertaItem}>
                  <Ionicons name="warning-outline" size={16} color={CORES.erro} />
                  <Text style={styles.alertaTexto}>{alerta.mensagem}</Text>
                </View>
              ))}
            </Section>
          )}

          <View onLayout={registrarSection('vacinas')}>
            <Section titulo="Carteirinha de vacinas">
              {(dados?.status_vacinal?.carteira || []).length === 0 ? (
                <Text style={styles.vazioTexto}>Nenhuma vacina registrada ainda.</Text>
              ) : (
                <CarteirinhaVacinasFolheto
                  pet={petAtual}
                  vacinas={dados?.status_vacinal?.carteira || []}
                  onPressVacina={setVacinaSelecionada}
                />
              )}
            </Section>
          </View>

          {!!dados?.status_vacinal?.pendentes?.length && (
            <Section titulo="Protocolos pendentes">
              {dados.status_vacinal.pendentes.map((item) => (
                <View key={item.nome} style={styles.pendenteChip}>
                  <Text style={styles.pendenteTexto}>{item.nome}</Text>
                </View>
              ))}
            </Section>
          )}

          <View onLayout={registrarSection('exames')}>
            <Section titulo="Exames recentes">
              {(dados?.exames || []).length === 0 ? (
                <Text style={styles.vazioTexto}>Nenhum exame encontrado.</Text>
              ) : (
                dados?.exames.map((exame) => (
                  <View key={exame.id} style={styles.itemCard}>
                    <Text style={styles.itemTitulo}>{exame.nome}</Text>
                    <Text style={styles.itemMeta}>Status: {exame.status || '-'}</Text>
                    <Text style={styles.itemMeta}>
                      Resultado: {formatarData(exame.data_resultado)}
                    </Text>
                    {!!exame.interpretacao_ia_resumo && (
                      <Text style={styles.itemResumo}>{exame.interpretacao_ia_resumo}</Text>
                    )}
                    {!!exame.arquivo_url && (
                      <TouchableOpacity onPress={() => abrirArquivo(exame.arquivo_url)}>
                        <Text style={styles.linkTexto}>Abrir arquivo do exame</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                ))
              )}
            </Section>
          </View>

          <View onLayout={registrarSection('consultas')}>
            <Section titulo="Consultas recentes">
              {(dados?.consultas || []).length === 0 ? (
                <Text style={styles.vazioTexto}>Nenhuma consulta encontrada.</Text>
              ) : (
                dados?.consultas.map((consulta) => (
                  <View key={consulta.id} style={styles.itemCard}>
                    <Text style={styles.itemTitulo}>{consulta.tipo || 'Consulta'}</Text>
                    <Text style={styles.itemMeta}>Data: {formatarData(consulta.data)}</Text>
                    <Text style={styles.itemMeta}>Status: {consulta.status || '-'}</Text>
                    {!!consulta.diagnostico && (
                      <Text style={styles.itemResumo}>{consulta.diagnostico}</Text>
                    )}
                  </View>
                ))
              )}
            </Section>
          </View>
        </>
      )}

      <CarteiraVacinaModal
        vacina={vacinaSelecionada}
        pet={petAtual}
        onClose={() => setVacinaSelecionada(null)}
      />
    </ScrollView>
  );
}
