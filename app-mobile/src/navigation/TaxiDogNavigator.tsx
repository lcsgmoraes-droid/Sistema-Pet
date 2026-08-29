import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import HeaderProfileActions from "../components/HeaderProfileActions";
import { TaxiDogEntregador } from "../screens/entregador/TaxiDogEntregador";

export type TaxiDogStackParamList = {
  TaxiDogRotas: undefined;
};

const Stack = createNativeStackNavigator<TaxiDogStackParamList>();

export default function TaxiDogNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#0F766E" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
        headerRight: () => (
          <HeaderProfileActions logoutContextLabel="taxi dog" />
        ),
      }}
    >
      <Stack.Screen
        name="TaxiDogRotas"
        component={TaxiDogEntregador}
        options={{ title: "Taxi Dog" }}
      />
    </Stack.Navigator>
  );
}
