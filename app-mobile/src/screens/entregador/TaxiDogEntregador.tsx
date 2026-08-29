import { Ionicons } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Linking,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  avancarTaxiDogDoEntregador,
  listarTaxiDogDoEntregador,
  TaxiDogEntregadorItem,
} from "../../services/taxiDogEntregador.service";
import { resolveTenantAssetUrl } from "../../store/tenant.store";
import { limparEnderecoParaMaps } from "../../utils/mapsAddress";

const STATUS_ACTIONS: Record<string, string> = {
  motorista_a_caminho: "Estou a caminho",
  pet_coletado: "Pet coletado",
  entregue_na_clinica: "Entreguei na loja",
  aguardando_retorno: "Aguardar retorno",
  retornando: "Iniciar retorno",
  entregue_ao_tutor: "Entreguei ao tutor",
};

function dataIso(date: Date) {
  const ano = date.getFullYear();
  const mes = String(date.getMonth() + 1).padStart(2, "0");
  const dia = String(date.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function TaxiDogEntregador() {
  const [data, setData] = useState(() => new Date());
  const [itens, setItens] = useState<TaxiDogEntregadorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [salvandoId, setSalvandoId] = useState<number | null>(null);

  const carregar = useCallback(
    async (mostrarErro = true) => {
      try {
        setItens(await listarTaxiDogDoEntregador(dataIso(data)));
      } catch (error: any) {
        if (mostrarErro) {
          Alert.alert(
            "Erro",
            error?.response?.data?.detail ||
              "Nao foi possivel carregar os pets do Taxi Dog.",
          );
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [data],
  );

  useEffect(() => {
    setLoading(true);
    void carregar(false);
    const timer = setInterval(() => void carregar(false), 30000);
    return () => clearInterval(timer);
  }, [carregar]);

  function navegarDia(delta: number) {
    setData((atual) => {
      const proxima = new Date(atual);
      proxima.setDate(proxima.getDate() + delta);
      return proxima;
    });
  }

  async function avancar(item: TaxiDogEntregadorItem) {
    if (!item.proximo_status) return;
    setSalvandoId(item.id);
    try {
      await avancarTaxiDogDoEntregador(item.id, item.proximo_status);
      await carregar();
    } catch (error: any) {
      Alert.alert(
        "Erro",
        error?.response?.data?.detail ||
          "Nao foi possivel atualizar o Taxi Dog.",
      );
    } finally {
      setSalvandoId(null);
    }
  }

  function abrirRota(item: TaxiDogEntregadorItem) {
    const origem = limparEnderecoParaMaps(item.endereco_origem);
    const destino = limparEnderecoParaMaps(item.endereco_destino);
    if (!origem && !destino) {
      Alert.alert(
        "Endereco",
        "Origem e destino ainda nao foram informados no ERP.",
      );
      return;
    }
    const url = destino
      ? `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origem)}&destination=${encodeURIComponent(destino)}`
      : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(origem)}`;
    Linking.openURL(url).catch(() =>
      Alert.alert("Mapa", "Nao foi possivel abrir o mapa."),
    );
  }

  if (loading) {
    return (
      <View style={taxiStyles.center}>
        <ActivityIndicator size="large" color="#0F766E" />
        <Text style={taxiStyles.muted}>Carregando Taxi Dog...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={taxiStyles.container}
      contentContainerStyle={taxiStyles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            void carregar();
          }}
        />
      }
    >
      <View style={taxiStyles.hero}>
        <Text style={taxiStyles.heroTitle}>Pets da minha rota</Text>
        <Text style={taxiStyles.heroText}>
          Cada mudanca atualiza o ERP. Ao entregar na loja, o pet entra
          automaticamente na fila.
        </Text>
      </View>

      <View style={taxiStyles.dayNav}>
        <TouchableOpacity
          style={taxiStyles.dayButton}
          onPress={() => navegarDia(-1)}
        >
          <Ionicons name="chevron-back" size={18} color="#1D4ED8" />
        </TouchableOpacity>
        <Text style={taxiStyles.dayTitle}>
          {data.toLocaleDateString("pt-BR", {
            weekday: "long",
            day: "2-digit",
            month: "long",
          })}
        </Text>
        <TouchableOpacity
          style={taxiStyles.dayButton}
          onPress={() => navegarDia(1)}
        >
          <Ionicons name="chevron-forward" size={18} color="#1D4ED8" />
        </TouchableOpacity>
      </View>

      {itens.map((item) => (
        <View key={item.id} style={taxiStyles.card}>
          <View style={taxiStyles.cardTop}>
            <PetPhoto name={item.pet_nome} url={item.pet_foto_url} />
            <View style={{ flex: 1 }}>
              <Text style={taxiStyles.pet}>
                {item.pet_nome || `Pet #${item.pet_id}`}
              </Text>
              <Text style={taxiStyles.tutor}>
                {item.cliente_nome || "Tutor nao informado"}
              </Text>
            </View>
            <View style={taxiStyles.badge}>
              <Text style={taxiStyles.badgeText}>{item.status_label}</Text>
            </View>
          </View>

          <Text style={taxiStyles.window}>
            Janela {hora(item.janela_inicio)} - {hora(item.janela_fim)} ·{" "}
            {labelTipo(item.tipo)}
          </Text>
          <Endereco label="Origem" value={item.endereco_origem} />
          <Endereco label="Destino" value={item.endereco_destino} />

          <View style={taxiStyles.actions}>
            <TouchableOpacity
              style={taxiStyles.mapButton}
              onPress={() => abrirRota(item)}
            >
              <Ionicons name="navigate-outline" size={18} color="#1D4ED8" />
              <Text style={taxiStyles.mapButtonText}>Abrir rota</Text>
            </TouchableOpacity>
            {item.proximo_status ? (
              <TouchableOpacity
                disabled={salvandoId === item.id}
                style={[
                  taxiStyles.nextButton,
                  salvandoId === item.id && taxiStyles.disabled,
                ]}
                onPress={() => avancar(item)}
              >
                <Text style={taxiStyles.nextButtonText}>
                  {salvandoId === item.id
                    ? "Atualizando..."
                    : STATUS_ACTIONS[item.proximo_status] || "Avancar"}
                </Text>
              </TouchableOpacity>
            ) : (
              <Text style={taxiStyles.done}>Rota concluida</Text>
            )}
          </View>
        </View>
      ))}

      {!itens.length && (
        <View style={taxiStyles.empty}>
          <Ionicons name="paw-outline" size={38} color="#94A3B8" />
          <Text style={taxiStyles.emptyTitle}>Nenhum pet atribuido</Text>
          <Text style={taxiStyles.muted}>
            O responsavel precisa escolher este motorista no Taxi Dog do ERP.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

function PetPhoto({
  name,
  url,
}: {
  name?: string | null;
  url?: string | null;
}) {
  const imageUrl = resolveTenantAssetUrl(url);
  return (
    <View
      style={taxiStyles.petPhotoFrame}
      accessibilityLabel={`Foto de ${name || "pet"}`}
    >
      {imageUrl ? (
        <Image
          source={{ uri: imageUrl }}
          style={taxiStyles.petPhoto}
          resizeMode="cover"
        />
      ) : (
        <Ionicons name="paw" size={24} color="#64748B" />
      )}
    </View>
  );
}

function Endereco({ label, value }: { label: string; value?: string | null }) {
  return (
    <View style={taxiStyles.addressRow}>
      <Text style={taxiStyles.addressLabel}>{label}</Text>
      <Text style={taxiStyles.address} numberOfLines={2}>
        {value || "Nao informado"}
      </Text>
    </View>
  );
}

function hora(value?: string | null) {
  if (!value) return "--:--";
  return new Date(value).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function labelTipo(tipo: string) {
  return { ida: "ida", volta: "volta", ida_volta: "ida e volta" }[tipo] || tipo;
}

const taxiStyles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  content: { padding: 14, gap: 12, paddingBottom: 32 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 8 },
  hero: { borderRadius: 14, backgroundColor: "#0F766E", padding: 16 },
  heroTitle: { color: "#FFFFFF", fontSize: 20, fontWeight: "900" },
  heroText: { color: "#CCFBF1", marginTop: 5, lineHeight: 19 },
  dayNav: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 8,
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },
  dayButton: {
    width: 38,
    height: 38,
    borderRadius: 10,
    backgroundColor: "#EFF6FF",
    alignItems: "center",
    justifyContent: "center",
  },
  dayTitle: {
    flex: 1,
    textAlign: "center",
    textTransform: "capitalize",
    color: "#0F172A",
    fontWeight: "800",
  },
  card: {
    borderRadius: 14,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E2E8F0",
    padding: 15,
  },
  cardTop: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  petPhotoFrame: {
    width: 58,
    height: 58,
    borderRadius: 14,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#E2E8F0",
  },
  petPhoto: { width: "100%", height: "100%" },
  pet: { color: "#0F172A", fontSize: 18, fontWeight: "900" },
  tutor: { color: "#64748B", marginTop: 2 },
  badge: {
    borderRadius: 999,
    backgroundColor: "#DBEAFE",
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  badgeText: { color: "#1D4ED8", fontSize: 11, fontWeight: "900" },
  window: { color: "#334155", fontWeight: "700", marginTop: 12 },
  addressRow: { marginTop: 9 },
  addressLabel: {
    color: "#64748B",
    fontSize: 11,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  address: { color: "#0F172A", marginTop: 2, lineHeight: 18 },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 8,
    marginTop: 14,
  },
  mapButton: {
    minHeight: 42,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#BFDBFE",
    paddingHorizontal: 12,
  },
  mapButtonText: { color: "#1D4ED8", fontWeight: "800" },
  nextButton: {
    minHeight: 42,
    borderRadius: 10,
    backgroundColor: "#0F766E",
    paddingHorizontal: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  nextButtonText: { color: "#FFFFFF", fontWeight: "900" },
  disabled: { opacity: 0.55 },
  done: { color: "#047857", fontWeight: "900" },
  empty: {
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: "#CBD5E1",
    padding: 28,
  },
  emptyTitle: { color: "#0F172A", fontWeight: "900", marginTop: 8 },
  muted: { color: "#64748B", textAlign: "center", marginTop: 3 },
});
