import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
  Linking,
  Image,
  LayoutChangeEvent,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { obterCarteirinhaPet } from '../../services/pets.service';
import { Pet, PetCarteirinha, VetFocusSection } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { calcularIdade, formatarData } from '../../utils/format';

const AUTO_SCROLL_DELAY_MS = 260;

export default function PetDetailScreen({ route, navigation }: any) {
  const pet = route.params.pet;
  const focusSection = route.params?.focusSection;
  const [dados, setDados] = useState<PetCarteirinha | null>(null);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<ScrollView | null>(null);
  const sectionPositionsRef = useRef<Record<VetFocusSection, number>>({
    vacinas: 0,
    exames: 0,
    consultas: 0,
  });

  useEffect(() => {
    carregar();
  }, [pet.id]);

  useEffect(() => {
    if (loading || !focusSection) return;

    const timer = setTimeout(() => {
      scrollToSection(focusSection);
    }, AUTO_SCROLL_DELAY_MS);

    return () => clearTimeout(timer);
  }, [loading, focusSection, pet.id]);

  async function carregar() {
    setLoading(true);
    try {
      const resposta = await obterCarteirinhaPet(pet.id);
      setDados(resposta);
    } catch {
      Alert.alert('Erro', 'Nao foi possivel carregar a carteirinha do pet.');
    } finally {
      setLoading(false);
    }
  }

  async function abrirArquivo(url?: string | null) {
    if (!url) return;
    const supported = await Linking.canOpenURL(url);
    if (!supported) {
      Alert.alert('Arquivo indisponivel', 'Nao foi possivel abrir o arquivo deste exame.');
      return;
    }
    await Linking.openURL(url);
  }

  function registrarSection(section: VetFocusSection) {
    return (event: LayoutChangeEvent) => {
      sectionPositionsRef.current[section] = event.nativeEvent.layout.y;
    };
  }

  function scrollToSection(section: VetFocusSection) {
    const y = sectionPositionsRef.current[section] ?? 0;
    scrollRef.current?.scrollTo({ y: Math.max(y - 12, 0), animated: true });
  }

  const petAtual = dados?.pet || pet;

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
          <Text style={styles.subtitulo}>
            {petAtual.data_nascimento
              ? calcularIdade(petAtual.data_nascimento)
              : 'Idade nao informada'}
          </Text>
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
                dados?.status_vacinal?.carteira.map((vacina) => (
                  <View key={vacina.id} style={styles.itemCard}>
                    <Text style={styles.itemTitulo}>{vacina.nome}</Text>
                    <Text style={styles.itemMeta}>
                      Aplicacao: {formatarData(vacina.data_aplicacao)}
                    </Text>
                    <Text style={styles.itemMeta}>
                      Proxima dose: {formatarData(vacina.data_proxima_dose)}
                    </Text>
                    {!!vacina.status && (
                      <Text style={styles.itemMeta}>Status: {vacina.status}</Text>
                    )}
                  </View>
                ))
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
    </ScrollView>
  );
}

function Section({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitulo}>{titulo}</Text>
      {children}
    </View>
  );
}

function ResumoCard({ titulo, valor, cor }: { titulo: string; valor: string; cor: string }) {
  return (
    <View style={[styles.resumoCard, { borderColor: cor }]}>
      <Text style={[styles.resumoValor, { color: cor }]}>{valor}</Text>
      <Text style={styles.resumoTitulo}>{titulo}</Text>
    </View>
  );
}

function QuickNavButton({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.quickNavButton} onPress={onPress}>
      <Ionicons name={icon} size={16} color={CORES.primario} />
      <Text style={styles.quickNavLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.lg, gap: ESPACO.md },
  headerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    gap: ESPACO.md,
    ...SOMBRA,
  },
  foto: { width: 72, height: 72, borderRadius: 36 },
  fotoPlaceholder: {
    backgroundColor: CORES.primarioClaro,
    justifyContent: 'center',
    alignItems: 'center',
  },
  fotoEmoji: { fontSize: 32 },
  nome: { fontSize: FONTE.grande, fontWeight: '700', color: CORES.texto },
  subtitulo: { fontSize: FONTE.normal, color: CORES.textoSecundario, marginTop: 2 },
  botaoEditar: {
    padding: 8,
    borderRadius: RAIO.circulo,
    backgroundColor: CORES.primarioClaro,
  },
  quickNavRow: {
    flexDirection: 'row',
    gap: ESPACO.sm,
  },
  quickNavButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: RAIO.md,
    borderWidth: 1,
    borderColor: '#BFDBFE',
    backgroundColor: '#EFF6FF',
  },
  quickNavLabel: {
    fontSize: FONTE.pequena,
    fontWeight: '700',
    color: CORES.primario,
  },
  loadingBox: { paddingVertical: ESPACO.xl, alignItems: 'center' },
  loadingText: { marginTop: ESPACO.sm, color: CORES.textoSecundario },
  resumoGrid: { flexDirection: 'row', gap: ESPACO.sm },
  resumoCard: {
    flex: 1,
    backgroundColor: CORES.superficie,
    borderWidth: 1,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    alignItems: 'center',
  },
  resumoValor: { fontSize: 26, fontWeight: '700' },
  resumoTitulo: {
    marginTop: 4,
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
  },
  section: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    ...SOMBRA,
  },
  sectionTitulo: {
    fontSize: FONTE.grande,
    fontWeight: '700',
    color: CORES.texto,
    marginBottom: ESPACO.sm,
  },
  alertaItem: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  alertaTexto: { flex: 1, color: CORES.texto },
  itemCard: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
    marginBottom: ESPACO.sm,
  },
  itemTitulo: { fontSize: FONTE.normal, fontWeight: '700', color: CORES.texto },
  itemMeta: { marginTop: 2, fontSize: FONTE.pequena, color: CORES.textoSecundario },
  itemResumo: { marginTop: 8, fontSize: FONTE.pequena, color: CORES.texto },
  linkTexto: { marginTop: 8, color: CORES.primario, fontWeight: '600' },
  vazioTexto: { color: CORES.textoSecundario },
  pendenteChip: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: '#F6AD55',
    backgroundColor: '#FFF7ED',
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.md,
    paddingVertical: 8,
    marginBottom: ESPACO.xs,
  },
  pendenteTexto: { color: '#9C4221', fontWeight: '600' },
});
