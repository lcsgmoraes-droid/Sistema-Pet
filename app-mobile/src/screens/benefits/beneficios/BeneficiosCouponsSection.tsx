import { Ionicons } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";
import React, { useState } from "react";
import { Pressable, Text, TouchableOpacity, View } from "react-native";

import { CORES } from "../../../theme";
import { beneficiosStyles as styles } from "./BeneficiosStyles";
import { brl, diasRestantes, formatarDesconto, type Beneficios } from "./BeneficiosUtils";

export function BeneficiosCouponsSection({
  cupons,
  onVerTodos,
}: {
  cupons: Beneficios["cupons"];
  onVerTodos: () => void;
}) {
  const [copiado, setCopiado] = useState<string | null>(null);

  const copiar = async (codigo: string) => {
    await Clipboard.setStringAsync(codigo);
    setCopiado(codigo);
    setTimeout(() => setCopiado(null), 2000);
  };

  const ativos = cupons.filter((c) => !c.expirado);
  const expirados = cupons.filter((c) => c.expirado);
  const todos = [...ativos, ...expirados];

  return (
    <View style={styles.secao}>
      <View style={styles.secaoTitulo}>
        <Ionicons name="ticket-outline" size={20} color={CORES.primario} />
        <Text style={styles.secaoTituloTexto}>
          Cupons de Desconto
          {ativos.length > 0
            ? ` · ${ativos.length} ativo${ativos.length > 1 ? "s" : ""}`
            : ""}
        </Text>
      </View>

      {todos.length === 0 ? (
        <Text style={styles.vazioTexto}>
          Nenhum cupom disponível no momento
        </Text>
      ) : (
        todos.map((item) => {
          const prazo = diasRestantes(item.valid_until);
          return (
            <View
              key={item.id}
              style={[styles.cupomCard, item.expirado && styles.cupomExpirado]}
            >
              <View style={styles.cupomTopo}>
                <TouchableOpacity
                  onPress={() => !item.expirado && copiar(item.code)}
                  activeOpacity={item.expirado ? 1 : 0.7}
                  style={styles.cupomCodigo}
                >
                  <Text
                    style={[
                      styles.cupomCodigoTexto,
                      item.expirado && styles.textoExpirado,
                    ]}
                  >
                    {item.code}
                  </Text>
                  {!item.expirado && (
                    <Ionicons
                      name={
                        copiado === item.code ? "checkmark" : "copy-outline"
                      }
                      size={15}
                      color={
                        copiado === item.code ? CORES.sucesso : CORES.primario
                      }
                      style={{ marginLeft: 6 }}
                    />
                  )}
                </TouchableOpacity>
                <View
                  style={[
                    styles.cupomBadge,
                    item.expirado
                      ? styles.cupomBadgeExp
                      : styles.cupomBadgeAtivo,
                  ]}
                >
                  <Text
                    style={[
                      styles.cupomBadgeTexto,
                      item.expirado && styles.textoExpirado,
                    ]}
                  >
                    {item.expirado ? "Expirado" : "Ativo"}
                  </Text>
                </View>
              </View>

              <Text
                style={[
                  styles.cupomDesconto,
                  item.expirado && styles.textoExpirado,
                ]}
              >
                {formatarDesconto(item)}
              </Text>

              {item.min_purchase_value != null &&
                item.min_purchase_value > 0 && (
                  <Text style={styles.cupomInfo}>
                    Pedido mínimo: R$ {brl(item.min_purchase_value)}
                  </Text>
                )}

              {!!prazo && prazo !== "Expirado" && (
                <Text
                  style={[
                    styles.cupomInfo,
                    prazo === "Expira hoje!" && { color: CORES.erro },
                  ]}
                >
                  {prazo}
                </Text>
              )}
            </View>
          );
        })
      )}
      <Pressable onPress={onVerTodos} style={styles.verTodosBotao}>
        <Text style={styles.verTodosTexto}>Ver todos os cupons</Text>
        <Ionicons name="chevron-forward" size={14} color={CORES.primario} />
      </Pressable>
    </View>
  );
}
