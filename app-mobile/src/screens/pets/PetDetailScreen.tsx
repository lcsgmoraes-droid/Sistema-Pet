import React, { useEffect, useRef, useState } from "react";
import { Alert, type LayoutChangeEvent, Linking, ScrollView } from "react-native";

import { obterCarteirinhaPet } from "../../services/pets.service";
import type { PetCarteirinha, VacinaCarteirinha, VetFocusSection } from "../../types";
import { PetDetailContent } from "./detail/PetDetailContent";

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
    <PetDetailContent
      scrollRef={scrollRef}
      petAtual={petAtual}
      dados={dados}
      loading={loading}
      vacinaSelecionada={vacinaSelecionada}
      setVacinaSelecionada={setVacinaSelecionada}
      navigation={navigation}
      registrarSection={registrarSection}
      scrollToSection={scrollToSection}
      abrirArquivo={abrirArquivo}
    />
  );
}
