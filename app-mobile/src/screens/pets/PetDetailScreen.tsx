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
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { obterCarteirinhaPet } from '../../services/pets.service';
import { Pet, PetCarteirinha, VacinaCarteirinha, VetFocusSection } from '../../types';
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from '../../theme';
import { calcularIdade, formatarData } from '../../utils/format';

const AUTO_SCROLL_DELAY_MS = 260;

export default function PetDetailScreen({ route, navigation }: any) {
  const pet = route.params.pet;
  const focusSection = route.params?.focusSection;
  const [dados, setDados] = useState<PetCarteirinha | null>(null);
  const [loading, setLoading] = useState(true);
  const [vacinaSelecionada, setVacinaSelecionada] = useState<VacinaCarteirinha | null>(null);
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

function formatarIdadePet(pet: Pet): string {
  if (pet.data_nascimento) return calcularIdade(pet.data_nascimento);
  if (typeof pet.idade_aproximada === 'number' && pet.idade_aproximada >= 0) {
    return formatarIdadeMeses(pet.idade_aproximada);
  }
  return 'Idade nao informada';
}

function formatarIdadeMeses(meses: number): string {
  if (meses < 12) return `${meses} ${meses === 1 ? 'mes' : 'meses'}`;
  const anos = Math.floor(meses / 12);
  const mesesRestantes = meses % 12;
  if (!mesesRestantes) return `${anos} ${anos === 1 ? 'ano' : 'anos'}`;
  return `${anos}a ${mesesRestantes}m`;
}

function labelStatusVacina(status?: string | null): string {
  const mapa: Record<string, string> = {
    em_dia: 'Em dia',
    vence_breve: 'Vence breve',
    atrasada: 'Atrasada',
  };
  return status ? mapa[status] ?? status : 'Registrada';
}

function corStatusVacina(status?: string | null): string {
  if (status === 'atrasada') return CORES.erro;
  if (status === 'vence_breve') return '#B7791F';
  return '#047857';
}

function resumirHash(hash?: string | null): string {
  if (!hash) return 'Sem codigo';
  return `${hash.slice(0, 8).toUpperCase()}...${hash.slice(-6).toUpperCase()}`;
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

const VACINAS_POR_PAGINA = 4;

function CarteirinhaVacinasFolheto({
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

function CarteiraVacinaModal({
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
  folhetoCarteira: {
    borderRadius: RAIO.lg,
    backgroundColor: '#74D391',
    padding: ESPACO.md,
    gap: ESPACO.sm,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  folhetoPaws: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    opacity: 0.9,
  },
  folhetoIdentidade: {
    flexDirection: 'row',
    gap: ESPACO.md,
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.22)',
    borderRadius: RAIO.lg,
    padding: ESPACO.sm,
  },
  folhetoLabel: {
    fontSize: 10,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: '#064E3B',
    fontWeight: '900',
  },
  folhetoPetNome: {
    marginTop: 4,
    fontSize: 22,
    color: '#064E3B',
    fontWeight: '900',
  },
  folhetoPetInfo: {
    marginTop: 2,
    fontSize: FONTE.pequena,
    color: '#065F46',
    fontWeight: '700',
  },
  folhetoFoto: {
    width: 88,
    height: 88,
    borderRadius: RAIO.md,
    borderWidth: 3,
    borderColor: '#FFFFFF',
    transform: [{ rotate: '5deg' }],
  },
  folhetoFotoPlaceholder: {
    backgroundColor: '#DCFCE7',
    alignItems: 'center',
    justifyContent: 'center',
  },
  folhetoSlots: { gap: ESPACO.sm },
  folhetoVacinaSlot: {
    borderRadius: RAIO.lg,
    backgroundColor: '#FFFFFF',
    padding: ESPACO.sm,
    borderWidth: 1,
    borderColor: 'rgba(6, 78, 59, 0.12)',
  },
  folhetoVacinaSlotVazio: {
    minHeight: 92,
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.72)',
    borderStyle: 'dashed',
  },
  folhetoSlotHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: ESPACO.sm,
  },
  folhetoSlotLabel: {
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 1,
    color: '#15803D',
    fontWeight: '900',
  },
  folhetoSlotTitulo: {
    marginTop: 2,
    fontSize: FONTE.normal,
    color: CORES.texto,
    fontWeight: '900',
  },
  folhetoSlotTexto: {
    marginTop: 4,
    color: '#166534',
    fontSize: FONTE.pequena,
  },
  folhetoStatusPill: {
    borderRadius: RAIO.circulo,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: '#F8FAFC',
  },
  folhetoStatusTexto: {
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  folhetoSlotGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: ESPACO.sm,
  },
  folhetoInfoBox: {
    width: '48%',
    borderRadius: RAIO.md,
    backgroundColor: '#F8FAFC',
    padding: 8,
  },
  folhetoInfoLabel: {
    fontSize: 9,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: CORES.textoClaro,
    fontWeight: '900',
  },
  folhetoInfoValor: {
    marginTop: 3,
    fontSize: FONTE.pequena,
    color: CORES.texto,
    fontWeight: '800',
  },
  folhetoAssinatura: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
    marginTop: ESPACO.sm,
    borderRadius: RAIO.md,
    backgroundColor: '#ECFDF5',
    padding: 8,
  },
  folhetoQr: {
    width: 42,
    height: 42,
    borderRadius: RAIO.md,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  folhetoAssinaturaTitulo: {
    fontSize: 10,
    color: '#166534',
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  folhetoAssinaturaTexto: {
    marginTop: 2,
    color: '#064E3B',
    fontWeight: '800',
  },
  folhetoAssinaturaHash: {
    marginTop: 2,
    fontSize: 10,
    color: '#15803D',
    fontWeight: '700',
  },
  folhetoPaginacao: {
    marginTop: ESPACO.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: ESPACO.sm,
  },
  folhetoPaginaBotao: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderColor: '#BFDBFE',
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 8,
    backgroundColor: '#EFF6FF',
  },
  folhetoPaginaBotaoDisabled: {
    borderColor: CORES.borda,
    backgroundColor: CORES.fundo,
  },
  folhetoPaginaTexto: {
    color: CORES.primario,
    fontWeight: '800',
    fontSize: FONTE.pequena,
  },
  folhetoPaginaTextoDisabled: { color: CORES.textoClaro },
  folhetoPaginaInfo: {
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    fontWeight: '800',
  },
  vacinaCard: {
    borderWidth: 1,
    borderColor: '#BFDBFE',
    borderRadius: RAIO.lg,
    padding: ESPACO.md,
    marginBottom: ESPACO.sm,
    backgroundColor: '#F8FBFF',
  },
  vacinaCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
  },
  vacinaIconBox: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: CORES.primarioClaro,
    alignItems: 'center',
    justifyContent: 'center',
  },
  vacinaNome: { fontSize: FONTE.normal, fontWeight: '800', color: CORES.texto },
  vacinaStatusPill: {
    borderRadius: RAIO.circulo,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  vacinaStatusTexto: { fontSize: FONTE.pequena, fontWeight: '800' },
  vacinaGrid: {
    flexDirection: 'row',
    gap: ESPACO.sm,
    marginTop: ESPACO.md,
  },
  vacinaCampo: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
  },
  vacinaCampoLabel: {
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: CORES.textoClaro,
    fontWeight: '800',
  },
  vacinaCampoValor: {
    marginTop: 3,
    fontSize: FONTE.pequena,
    color: CORES.texto,
    fontWeight: '700',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.58)',
    justifyContent: 'center',
    padding: ESPACO.lg,
  },
  modalCard: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.lg,
    padding: ESPACO.md,
    ...SOMBRA,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: ESPACO.md,
  },
  modalTitulo: { fontSize: FONTE.grande, fontWeight: '800', color: CORES.texto },
  modalSubtitulo: { marginTop: 2, fontSize: FONTE.pequena, color: CORES.textoSecundario },
  modalCloseButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: CORES.fundo,
  },
  carteiraVirtual: {
    borderRadius: RAIO.lg,
    borderWidth: 1,
    borderColor: '#F6AD55',
    backgroundColor: '#FFFBEB',
    padding: ESPACO.md,
  },
  carteiraTopLine: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: ESPACO.sm,
  },
  carteiraPetNome: { fontSize: FONTE.grande, fontWeight: '900', color: CORES.texto },
  carteiraStamp: {
    minWidth: 82,
    minHeight: 82,
    borderRadius: 41,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ rotate: '-8deg' }],
    backgroundColor: 'rgba(255,255,255,0.6)',
  },
  carteiraStampTexto: {
    fontSize: 11,
    fontWeight: '900',
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  carteiraVacinaNome: {
    marginTop: ESPACO.md,
    fontSize: 22,
    fontWeight: '900',
    color: CORES.texto,
  },
  carteiraInfoGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ESPACO.sm,
    marginTop: ESPACO.md,
  },
  carteiraInfoBox: {
    width: '48%',
    backgroundColor: '#FFFFFF',
    borderRadius: RAIO.md,
    padding: ESPACO.sm,
  },
  carteiraInfoLabel: {
    fontSize: 10,
    letterSpacing: 0.8,
    color: CORES.textoClaro,
    textTransform: 'uppercase',
    fontWeight: '800',
  },
  carteiraInfoValor: {
    marginTop: 4,
    fontSize: FONTE.pequena,
    color: CORES.texto,
    fontWeight: '800',
  },
  assinaturaBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: ESPACO.sm,
    marginTop: ESPACO.md,
    padding: ESPACO.sm,
    borderRadius: RAIO.md,
    backgroundColor: '#EEF2FF',
  },
  assinaturaTitulo: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  assinaturaNome: { marginTop: 2, fontSize: FONTE.normal, fontWeight: '800', color: CORES.texto },
  assinaturaCodigo: { marginTop: 2, fontSize: FONTE.pequena, color: CORES.primario },
  hashTexto: {
    marginTop: ESPACO.sm,
    fontSize: 10,
    color: CORES.textoClaro,
    textAlign: 'center',
  },
  fecharModal: {
    marginTop: ESPACO.md,
    borderRadius: RAIO.md,
    backgroundColor: CORES.primario,
    paddingVertical: ESPACO.sm + 2,
    alignItems: 'center',
  },
  fecharModalTexto: { color: '#FFFFFF', fontWeight: '800' },
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
