import { Ionicons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import React from "react";
import { Alert, Text, TouchableOpacity } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import VetAgendaScreen from "../screens/veterinario/VetAgendaScreen";
import VetCalculadoraScreen from "../screens/veterinario/VetCalculadoraScreen";
import VetInternacoesScreen from "../screens/veterinario/VetInternacoesScreen";
import VetProcedimentosScreen from "../screens/veterinario/VetProcedimentosScreen";
import VetResumoScreen from "../screens/veterinario/VetResumoScreen";
import { useAuthStore } from "../store/auth.store";
import { CORES } from "../theme";
import { VeterinarioTabParamList } from "../types/veterinarioNavigation";

const Tab = createBottomTabNavigator<VeterinarioTabParamList>();

function HeaderLogoutAction() {
  const { logout } = useAuthStore();

  const confirmarLogout = () => {
    Alert.alert("Sair da conta", "Deseja sair da conta veterinaria?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Sair",
        style: "destructive",
        onPress: () => {
          logout().catch(() => {
            Alert.alert("Erro", "Nao foi possivel sair agora.");
          });
        },
      },
    ]);
  };

  return (
    <TouchableOpacity onPress={confirmarLogout}>
      <Text style={{ color: CORES.primario, fontWeight: "800" }}>Sair</Text>
    </TouchableOpacity>
  );
}

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
        headerRight: HeaderLogoutAction,
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

