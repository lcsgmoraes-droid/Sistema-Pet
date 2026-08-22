import { Ionicons } from '@expo/vector-icons';
import React, { useMemo, useState } from 'react';
import {
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import {
  EvolucaoCorePetItem,
  EvolucaoStatus,
} from '../../services/evolucaoCorePet.service';
import { CORES, ESPACO, FONTE, RAIO } from '../../theme';

type EvolucaoAba = 'novidades' | 'andamento' | 'estudo';

const ABAS: Array<{
  id: EvolucaoAba;
  label: string;
  status: EvolucaoStatus[];
}> = [
  { id: 'novidades', label: 'Disponível', status: ['disponivel'] },
  {
    id: 'andamento',
    label: 'Em andamento',
    status: ['em_desenvolvimento', 'em_testes'],
  },
  { id: 'estudo', label: 'Em estudo', status: ['em_estudo', 'planejado'] },
];

const STATUS: Record<
  EvolucaoStatus,
  { label: string; cor: string; fundo: string }
> = {
  disponivel: { label: 'Disponível', cor: CORES.sucesso, fundo: '#DCFCE7' },
  em_testes: { label: 'Em testes', cor: '#7C3AED', fundo: '#EDE9FE' },
  em_desenvolvimento: {
    label: 'Em desenvolvimento',
    cor: '#2563EB',
    fundo: '#DBEAFE',
  },
  planejado: { label: 'Planejado', cor: CORES.aviso, fundo: '#FEF3C7' },
  em_estudo: {
    label: 'Em estudo',
    cor: CORES.textoSecundario,
    fundo: '#F3F4F6',
  },
};

type Props = {
  itens: EvolucaoCorePetItem[];
  refreshing: boolean;
  onRefresh: () => void;
};

export default function EvolucaoCorePetList({
  itens,
  refreshing,
  onRefresh,
}: Props) {
  const [aba, setAba] = useState<EvolucaoAba>('novidades');
  const abaAtual = ABAS.find((item) => item.id === aba) ?? ABAS[0];
  const filtrados = useMemo(
    () => itens.filter((item) => abaAtual.status.includes(item.status)),
    [abaAtual.status, itens],
  );

  return (
    <View style={styles.container}>
      <View style={styles.abas}>
        {ABAS.map((item) => {
          const ativa = aba === item.id;
          const quantidade = itens.filter((registro) =>
            item.status.includes(registro.status),
          ).length;
          return (
            <TouchableOpacity
              key={item.id}
              style={[styles.aba, ativa && styles.abaAtiva]}
              onPress={() => setAba(item.id)}
            >
              <Text style={[styles.abaTexto, ativa && styles.abaTextoAtiva]}>
                {item.label}
              </Text>
              <View style={[styles.contador, ativa && styles.contadorAtivo]}>
                <Text
                  style={[
                    styles.contadorTexto,
                    ativa && styles.contadorTextoAtivo,
                  ]}
                >
                  {quantidade}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {aba === 'estudo' ? (
        <View style={styles.avisoEstudo}>
          <Ionicons
            name="information-circle-outline"
            size={18}
            color={CORES.aviso}
          />
          <Text style={styles.avisoEstudoTexto}>
            Projetos nesta etapa podem mudar conforme os testes e as
            prioridades.
          </Text>
        </View>
      ) : null}

      <FlatList
        data={filtrados}
        keyExtractor={(item) => item.id}
        contentContainerStyle={
          filtrados.length ? styles.lista : styles.listaVazia
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={CORES.primario}
          />
        }
        ListEmptyComponent={
          <View style={styles.vazio}>
            <Ionicons
              name="checkmark-circle-outline"
              size={36}
              color={CORES.primario}
            />
            <Text style={styles.vazioTitulo}>Nenhum item nesta etapa</Text>
          </View>
        }
        renderItem={({ item }) => {
          const status = STATUS[item.status];
          return (
            <View style={[styles.card, item.destaque && styles.cardDestaque]}>
              <View style={styles.cardTopo}>
                <View
                  style={[styles.status, { backgroundColor: status.fundo }]}
                >
                  <Text style={[styles.statusTexto, { color: status.cor }]}>
                    {status.label}
                  </Text>
                </View>
                <Text style={styles.modulo}>{item.modulo}</Text>
              </View>
              <Text style={styles.titulo}>{item.titulo}</Text>
              <Text style={styles.resumo}>{item.resumo}</Text>
              <View style={styles.plataformas}>
                {(item.plataformas ?? []).map((plataforma) => (
                  <View key={plataforma} style={styles.plataforma}>
                    <Text style={styles.plataformaTexto}>{plataforma}</Text>
                  </View>
                ))}
              </View>
              <Text style={styles.data}>
                {item.status === 'disponivel' ? 'Publicado' : 'Atualizado'} em{' '}
                {formatarData(
                  item.status === 'disponivel'
                    ? item.publicado_em
                    : item.atualizado_em,
                )}
              </Text>
            </View>
          );
        }}
      />
    </View>
  );
}

function formatarData(value?: string | null): string {
  if (!value) return '';
  const [ano, mes, dia] = value.split('-').map(Number);
  if (!ano || !mes || !dia) return '';
  return new Date(ano, mes - 1, dia).toLocaleDateString('pt-BR');
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  abas: {
    flexDirection: 'row',
    padding: ESPACO.sm,
    gap: ESPACO.xs,
    backgroundColor: CORES.superficie,
    borderBottomWidth: 1,
    borderBottomColor: CORES.borda,
  },
  aba: {
    flex: 1,
    minHeight: 42,
    borderRadius: RAIO.md,
    paddingHorizontal: ESPACO.xs,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 4,
  },
  abaAtiva: { backgroundColor: CORES.primarioClaro },
  abaTexto: { fontSize: 11, fontWeight: '700', color: CORES.textoSecundario },
  abaTextoAtiva: { color: CORES.primario },
  contador: {
    minWidth: 18,
    height: 18,
    paddingHorizontal: 4,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F3F4F6',
  },
  contadorAtivo: { backgroundColor: CORES.superficie },
  contadorTexto: { fontSize: 10, fontWeight: '800', color: CORES.textoClaro },
  contadorTextoAtivo: { color: CORES.primario },
  avisoEstudo: {
    marginHorizontal: ESPACO.md,
    marginTop: ESPACO.md,
    padding: ESPACO.sm,
    borderRadius: RAIO.md,
    backgroundColor: '#FFFBEB',
    flexDirection: 'row',
    gap: ESPACO.xs,
  },
  avisoEstudoTexto: {
    flex: 1,
    fontSize: FONTE.pequena,
    lineHeight: 17,
    color: '#92400E',
  },
  lista: { padding: ESPACO.md, gap: ESPACO.sm },
  listaVazia: { flexGrow: 1, padding: ESPACO.lg },
  card: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.md,
    backgroundColor: CORES.superficie,
    padding: ESPACO.md,
  },
  cardDestaque: { borderColor: CORES.primario },
  cardTopo: { flexDirection: 'row', alignItems: 'center', gap: ESPACO.xs },
  status: {
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 4,
  },
  statusTexto: { fontSize: FONTE.pequena, fontWeight: '800' },
  modulo: {
    flex: 1,
    textAlign: 'right',
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
  },
  titulo: {
    marginTop: ESPACO.sm,
    fontSize: FONTE.grande,
    fontWeight: '800',
    color: CORES.texto,
  },
  resumo: {
    marginTop: ESPACO.xs,
    fontSize: FONTE.normal,
    lineHeight: 20,
    color: CORES.textoSecundario,
  },
  plataformas: {
    marginTop: ESPACO.sm,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ESPACO.xs,
  },
  plataforma: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: 4,
  },
  plataformaTexto: { fontSize: FONTE.pequena, color: CORES.textoSecundario },
  data: {
    marginTop: ESPACO.md,
    fontSize: FONTE.pequena,
    color: CORES.textoClaro,
  },
  vazio: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  vazioTitulo: { marginTop: ESPACO.sm, fontWeight: '800', color: CORES.texto },
});
