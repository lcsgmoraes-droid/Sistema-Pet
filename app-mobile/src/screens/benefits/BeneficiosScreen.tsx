import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { BeneficiosCashbackSection } from "./beneficios/BeneficiosCashbackSection";
import { BeneficiosCouponsSection } from "./beneficios/BeneficiosCouponsSection";
import { BeneficiosRankingSection } from "./beneficios/BeneficiosRankingSection";
import { beneficiosStyles as styles } from "./beneficios/BeneficiosStyles";
import {
  BeneficiosNextLevelsSection,
  BeneficiosStampSection,
} from "./beneficios/BeneficiosStampAndLevelsSections";
import { normalizarBeneficios, type Beneficios } from "./beneficios/BeneficiosUtils";
import api from "../../services/api";
import { CORES } from "../../theme";

export default function BeneficiosScreen() {
  const navigation = useNavigation<any>();
  const [dados, setDados] = useState<Beneficios | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [erro, setErro] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setErro(false);
      const { data } = await api.get<Beneficios>(
        "/ecommerce/auth/meus-beneficios",
      );
      setDados(normalizarBeneficios(data));
    } catch {
      setErro(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const onRefresh = () => {
    setRefreshing(true);
    carregar();
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={CORES.primario} />
      </View>
    );
  }

  if (erro || !dados) {
    return (
      <View style={styles.center}>
        <Ionicons name="alert-circle-outline" size={56} color={CORES.erro} />
        <Text style={styles.erroTexto}>
          Não foi possível carregar seus benefícios
        </Text>
        <TouchableOpacity style={styles.btnRetentar} onPress={carregar}>
          <Text style={styles.btnRetentarTexto}>Tentar novamente</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.conteudo}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          colors={[CORES.primario]}
          tintColor={CORES.primario}
        />
      }
    >
      <BeneficiosRankingSection ranking={dados.ranking} />
      <BeneficiosStampSection carimbos={dados.carimbos} />
      <BeneficiosCashbackSection saldo={dados.cashback.saldo} />
      <BeneficiosCouponsSection
        cupons={dados.cupons}
        onVerTodos={() => navigation.navigate("MeusCupons")}
      />
      <BeneficiosNextLevelsSection ranking={dados.ranking} />
    </ScrollView>
  );
}
