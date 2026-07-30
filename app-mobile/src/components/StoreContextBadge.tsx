import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Image, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useStoreSwitch } from "../hooks/useStoreSwitch";
import {
  resolveTenantAssetUrl,
  useTenantStore,
} from "../store/tenant.store";
import { CORES, RAIO } from "../theme";

type StoreContextBadgeProps = {
  compact?: boolean;
};

export default function StoreContextBadge({
  compact = false,
}: StoreContextBadgeProps) {
  const tenant = useTenantStore((state) => state.tenant);
  const requestStoreSwitch = useStoreSwitch();

  if (!tenant) return null;
  const logoUrl = resolveTenantAssetUrl(tenant.logo_url);
  const location = [tenant.cidade, tenant.uf].filter(Boolean).join("/");

  return (
    <TouchableOpacity
      style={[styles.container, compact && styles.compact]}
      onPress={requestStoreSwitch}
      activeOpacity={0.75}
      accessibilityLabel={`Loja atual: ${tenant.nome}. Toque para trocar.`}
    >
      <View style={styles.iconBox}>
        {logoUrl ? (
          <Image source={{ uri: logoUrl }} style={styles.logo} resizeMode="contain" />
        ) : (
          <Ionicons name="storefront-outline" size={17} color={CORES.primario} />
        )}
      </View>
      <View style={styles.textBox}>
        {!compact ? <Text style={styles.label}>Comprando em</Text> : null}
        <Text style={styles.name} numberOfLines={1}>
          {tenant.nome}
        </Text>
        {!compact && location ? (
          <Text style={styles.location} numberOfLines={1}>
            {location}
          </Text>
        ) : null}
      </View>
      {!compact ? (
        <Ionicons name="swap-horizontal-outline" size={18} color={CORES.primario} />
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#ECF8F7",
    borderWidth: 1,
    borderColor: "#B9E1DD",
    borderRadius: RAIO.md,
    paddingHorizontal: 10,
    paddingVertical: 7,
    gap: 8,
  },
  compact: {
    maxWidth: 150,
    minHeight: 38,
    paddingHorizontal: 7,
    paddingVertical: 4,
    marginRight: 8,
  },
  iconBox: {
    width: 30,
    height: 30,
    borderRadius: 7,
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    flexShrink: 0,
  },
  logo: {
    width: 27,
    height: 27,
  },
  textBox: {
    flex: 1,
    minWidth: 0,
  },
  label: {
    color: CORES.textoSecundario,
    fontSize: 10,
    fontWeight: "600",
    textTransform: "uppercase",
  },
  name: {
    color: CORES.texto,
    fontSize: 12,
    fontWeight: "700",
  },
  location: {
    color: CORES.textoSecundario,
    fontSize: 10,
  },
});
