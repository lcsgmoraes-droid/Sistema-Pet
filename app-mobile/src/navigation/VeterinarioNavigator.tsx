import { Ionicons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import React from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import HeaderProfileActions from "../components/HeaderProfileActions";
import VetAgendaScreen from "../screens/veterinario/VetAgendaScreen";
import VetCalculadoraScreen from "../screens/veterinario/VetCalculadoraScreen";
import VetInternacoesScreen from "../screens/veterinario/VetInternacoesScreen";
import VetProcedimentosScreen from "../screens/veterinario/VetProcedimentosScreen";
import VetResumoScreen from "../screens/veterinario/VetResumoScreen";
import { CORES } from "../theme";
import { VeterinarioTabParamList } from "../types/veterinarioNavigation";

const Tab = createBottomTabNavigator<VeterinarioTabParamList>();

export default function VeterinarioNavigator() {
  const insets = useSafeAreaInsets();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarActiveTintColor: CORES.primario,
        tabBarInactiveTintColor: CORES.textoClaro,
        tabBarStyle: {
          borderTopColor: CORES.borda,
          paddingBottom: insets.bottom + 4,
          height: 60 + insets.bottom,
        },
        tabBarLabelStyle: { fontSize: 11 },
        headerRight: () => (
          <HeaderProfileActions
            color={CORES.primario}
            logoutContextLabel="veterinaria"
          />
        ),
        headerTitleStyle: { fontWeight: "800" },
        tabBarIcon: ({ color, size }) => {
          const icons: Record<keyof VeterinarioTabParamList, keyof typeof Ionicons.glyphMap> = {
            VetResumo: "pulse-outline",
            VetAgenda: "calendar-outline",
            VetInternacoes: "bed-outline",
            VetProcedimentos: "alarm-outline",
            VetCalculadora: "calculator-outline",
          };
          return <Ionicons name={icons[route.name as keyof VeterinarioTabParamList]} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="VetResumo" component={VetResumoScreen} options={{ title: "Resumo" }} />
      <Tab.Screen name="VetAgenda" component={VetAgendaScreen} options={{ title: "Agenda" }} />
      <Tab.Screen name="VetInternacoes" component={VetInternacoesScreen} options={{ title: "Internados" }} />
      <Tab.Screen name="VetProcedimentos" component={VetProcedimentosScreen} options={{ title: "Cuidados" }} />
      <Tab.Screen name="VetCalculadora" component={VetCalculadoraScreen} options={{ title: "Dose" }} />
    </Tab.Navigator>
  );
}

