import React from "react";
import { Text, View } from "react-native";

import { formatarMoeda } from "../../../utils/format";
import { foodCalculatorStyles as styles } from "./FoodCalculatorStyles";

export function FoodCalculatorField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.campo}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

export function FoodCalculatorResultCard({
  resultado,
  titulo,
  compact = false,
}: {
  resultado: any;
  titulo?: string | null;
  compact?: boolean;
}) {
  return (
    <View style={[styles.resultadoCard, compact && styles.resultadoCardCompact]}>
      {titulo && (
        <Text style={styles.resultadoNome} numberOfLines={2}>{titulo}</Text>
      )}
      <Text style={styles.resultadoTitulo}>Resultado</Text>

      <ItemResultado
        emoji="🥣"
        titulo="Qtd Diária"
        valor={`${resultado.quantidade_diaria_g}g`}
        destaque
      />

      {Number(resultado.duracao_dias) > 0 && (
        <ItemResultado
          emoji="📅"
          titulo="Duração"
          valor={`${resultado.duracao_dias} dias`}
        />
      )}

      {Number(resultado.custo_por_dia) > 0 && (
        <ItemResultado
          emoji="💸"
          titulo="Custo/dia"
          valor={formatarMoeda(resultado.custo_por_dia)}
        />
      )}

      {Number(resultado.custo_mensal) > 0 && (
        <ItemResultado
          emoji="📆"
          titulo="Custo/mês"
          valor={formatarMoeda(resultado.custo_mensal)}
        />
      )}

      {resultado.alerta && (
        <View style={styles.alerta}>
          <Text style={styles.alertaTexto}>⚠️ {resultado.alerta}</Text>
        </View>
      )}
    </View>
  );
}

function ItemResultado({
  emoji,
  titulo,
  valor,
  destaque = false,
  compact = false,
}: {
  emoji: string;
  titulo: string;
  valor: string;
  destaque?: boolean;
  compact?: boolean;
}) {
  return (
    <View style={[styles.itemResultado, destaque && styles.itemDestaque, compact && styles.itemResultadoCompact]}>
      <Text style={[styles.itemEmoji, compact && styles.itemEmojiCompact]}>{emoji}</Text>
      <View style={{ flex: 1 }}>
        <Text style={[styles.itemTitulo, compact && styles.itemTituloCompact]}>{titulo}</Text>
        <Text style={[styles.itemValor, destaque && styles.itemValorDestaque, compact && styles.itemValorCompact]}>{valor}</Text>
      </View>
    </View>
  );
}

