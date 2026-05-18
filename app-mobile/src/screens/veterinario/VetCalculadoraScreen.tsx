import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { listarMedicamentosVet, VetMedicamento } from "../../services/vet.service";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";

function parseNumber(value: string): number {
  const normalizado = value.replace(",", ".").replace(/[^0-9.]/g, "");
  const parsed = Number(normalizado);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function VetCalculadoraScreen() {
  const [busca, setBusca] = useState("");
  const [peso, setPeso] = useState("");
  const [dose, setDose] = useState("");
  const [medicamentos, setMedicamentos] = useState<VetMedicamento[]>([]);
  const [selecionado, setSelecionado] = useState<VetMedicamento | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function carregar() {
      try {
        const data = await listarMedicamentosVet(busca || undefined);
        if (!mounted) return;
        setMedicamentos(data);
        if (!selecionado && data[0]) {
          selecionar(data[0]);
        }
      } catch {
        Alert.alert("Erro", "Nao foi possivel carregar medicamentos.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    const timeout = setTimeout(carregar, 250);
    return () => {
      mounted = false;
      clearTimeout(timeout);
    };
  }, [busca]);

  function selecionar(medicamento: VetMedicamento) {
    setSelecionado(medicamento);
    const doseMin = medicamento.dose_min_mgkg;
    const doseMax = medicamento.dose_max_mgkg;
    if (doseMin && doseMax) {
      setDose(String((doseMin + doseMax) / 2));
    } else if (doseMin || doseMax) {
      setDose(String(doseMin || doseMax));
    }
  }

  const calculo = useMemo(() => {
    const pesoKg = parseNumber(peso);
    const doseMgKg = parseNumber(dose);
    return {
      mgPorDose: pesoKg * doseMgKg,
      doseMgKg,
      pesoKg,
    };
  }, [peso, dose]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Calculadora de dose</Text>
      <View style={styles.card}>
        <Text style={styles.label}>Peso do pet (kg)</Text>
        <TextInput
          value={peso}
          onChangeText={setPeso}
          keyboardType="decimal-pad"
          placeholder="Ex: 15"
          style={styles.input}
        />

        <Text style={styles.label}>Buscar medicamento</Text>
        <TextInput
          value={busca}
          onChangeText={setBusca}
          placeholder="Digite para buscar"
          style={styles.input}
        />

        {loading ? (
          <ActivityIndicator color={CORES.primario} />
        ) : (
          <View style={styles.list}>
            {medicamentos.slice(0, 8).map((item) => (
              <TouchableOpacity
                key={item.id}
                style={[styles.medItem, selecionado?.id === item.id && styles.medItemActive]}
                onPress={() => selecionar(item)}
              >
                <Text style={styles.medName}>{item.nome}</Text>
                <Text style={styles.medHint}>
                  {item.posologia_referencia || "Sem referencia de posologia"}
                </Text>
              </TouchableOpacity>
            ))}
            {!medicamentos.length && <Text style={styles.empty}>Nenhum medicamento encontrado.</Text>}
          </View>
        )}

        <Text style={styles.label}>Dose escolhida (mg/kg)</Text>
        <TextInput
          value={dose}
          onChangeText={setDose}
          keyboardType="decimal-pad"
          placeholder="Ex: 25"
          style={styles.input}
        />
      </View>

      <View style={styles.result}>
        <Text style={styles.resultLabel}>Resultado</Text>
        <Text style={styles.resultValue}>{calculo.mgPorDose.toFixed(2)} mg por dose</Text>
        <Text style={styles.resultText}>
          {calculo.pesoKg.toFixed(2)} kg x {calculo.doseMgKg.toFixed(2)} mg/kg
        </Text>
        {!!selecionado?.posologia_referencia && (
          <Text style={styles.resultText}>Referencia: {selecionado.posologia_referencia}</Text>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CORES.fundo },
  content: { padding: ESPACO.md, gap: ESPACO.md },
  title: { fontSize: FONTE.titulo, color: CORES.texto, fontWeight: "800" },
  card: {
    backgroundColor: CORES.superficie,
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    ...SOMBRA,
  },
  label: { color: CORES.texto, fontSize: FONTE.pequena, fontWeight: "800", marginBottom: ESPACO.xs, marginTop: ESPACO.sm },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    paddingHorizontal: ESPACO.md,
    paddingVertical: ESPACO.sm,
    fontSize: FONTE.media,
    color: CORES.texto,
  },
  list: { gap: ESPACO.sm, marginTop: ESPACO.sm },
  medItem: {
    borderWidth: 1,
    borderColor: CORES.borda,
    borderRadius: RAIO.sm,
    padding: ESPACO.sm,
  },
  medItemActive: { borderColor: CORES.primario, backgroundColor: CORES.primarioClaro },
  medName: { color: CORES.texto, fontWeight: "800" },
  medHint: { color: CORES.textoSecundario, fontSize: FONTE.pequena, marginTop: 2 },
  empty: { color: CORES.textoSecundario, textAlign: "center", padding: ESPACO.md },
  result: {
    backgroundColor: "#ecfeff",
    borderRadius: RAIO.md,
    padding: ESPACO.md,
    borderWidth: 1,
    borderColor: "#a5f3fc",
  },
  resultLabel: { color: "#0e7490", fontWeight: "800", fontSize: FONTE.pequena, textTransform: "uppercase" },
  resultValue: { color: "#164e63", fontSize: FONTE.titulo, fontWeight: "900", marginTop: ESPACO.xs },
  resultText: { color: "#155e75", marginTop: ESPACO.xs },
});

