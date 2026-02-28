import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { View, Text, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { CORES } from '../theme';
import { useCartStore } from '../store/cart.store';
import { useWishlistStore } from '../store/wishlist.store';

// Screens
import HomeScreen from '../screens/HomeScreen';
import CatalogScreen from '../screens/shop/CatalogScreen';
import CartScreen from '../screens/shop/CartScreen';
import WishlistScreen from '../screens/shop/WishlistScreen';
import BarcodeScannerScreen from '../screens/shop/BarcodeScannerScreen';
import CheckoutSucessoScreen from '../screens/shop/CheckoutSucessoScreen';
import PetListScreen from '../screens/pets/PetListScreen';
import PetFormScreen from '../screens/pets/PetFormScreen';
import FoodCalculatorScreen from '../screens/pets/FoodCalculatorScreen';
import OrdersScreen from '../screens/orders/OrdersScreen';
import ProfileScreen from '../screens/profile/ProfileScreen';

const Tab = createBottomTabNavigator();
const LojaStack = createNativeStackNavigator();
const PetsStack = createNativeStackNavigator();

function LojaNavigator() {
  return (
    <LojaStack.Navigator>
      <LojaStack.Screen
        name="Catalogo"
        component={CatalogScreen}
        options={{ title: 'Produtos' }}
      />
      <LojaStack.Screen
        name="Carrinho"
        component={CartScreen}
        options={{ title: 'Meu Carrinho' }}
      />
      <LojaStack.Screen
        name="BarcodeScanner"
        component={BarcodeScannerScreen}
        options={{ title: 'Escanear Produto', headerShown: false }}
      />
      <LojaStack.Screen
        name="CheckoutSucesso"
        component={CheckoutSucessoScreen}
        options={{ title: 'Pedido Confirmado', headerLeft: () => null }}
      />
    </LojaStack.Navigator>
  );
}

function PetsNavigator() {
  return (
    <PetsStack.Navigator>
      <PetsStack.Screen
        name="ListaPets"
        component={PetListScreen}
        options={{ title: 'Meus Pets' }}
      />
      <PetsStack.Screen
        name="FormPet"
        component={PetFormScreen}
        options={({ route }: any) => ({
          title: route.params?.pet ? 'Editar Pet' : 'Novo Pet',
        })}
      />
      <PetsStack.Screen
        name="CalculadoraRacao"
        component={FoodCalculatorScreen}
        options={{ title: 'Calculadora de Ração' }}
      />
    </PetsStack.Navigator>
  );
}

// Badge do carrinho
function CartIcon({ color, size }: { color: string; size: number }) {
  const { totalItens } = useCartStore();
  const count = totalItens();
  return (
    <View>
      <Ionicons name="cart-outline" size={size} color={color} />
      {count > 0 && (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{count > 9 ? '9+' : count}</Text>
        </View>
      )}
    </View>
  );
}

// Badge dos favoritos
function HeartIcon({ color, size }: { color: string; size: number }) {
  const { ids } = useWishlistStore();
  const count = ids.length;
  return (
    <View>
      <Ionicons name={count > 0 ? 'heart' : 'heart-outline'} size={size} color={count > 0 ? CORES.secundario : color} />
      {count > 0 && (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{count > 9 ? '9+' : count}</Text>
        </View>
      )}
    </View>
  );
}

export default function MainNavigator() {
  const insets = useSafeAreaInsets();
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: CORES.primario,
        tabBarInactiveTintColor: CORES.textoClaro,
        tabBarStyle: {
          borderTopColor: CORES.borda,
          paddingBottom: insets.bottom + 4,
          height: 60 + insets.bottom,
        },
        tabBarLabelStyle: { fontSize: 11 },
        headerShown: false,
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: 'Início',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home-outline" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Loja"
        component={LojaNavigator}
        listeners={({ navigation }) => ({
          tabPress: () => {
            navigation.navigate('Loja', { screen: 'Catalogo' });
          },
        })}
        options={{
          title: 'Loja',
          tabBarIcon: ({ color, size }) => (
            <CartIcon color={color} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Favoritos"
        component={WishlistScreen}
        options={{
          title: 'Favoritos',
          tabBarIcon: ({ color, size }) => (
            <HeartIcon color={color} size={size} />
          ),
          headerShown: true,
          headerTitle: 'Meus Favoritos',
        }}
      />
      <Tab.Screen
        name="Pets"
        component={PetsNavigator}
        listeners={({ navigation }) => ({
          tabPress: () => {
            navigation.navigate('Pets', { screen: 'ListaPets' });
          },
        })}
        options={{
          title: 'Pets',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="paw-outline" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Pedidos"
        component={OrdersScreen}
        options={{
          title: 'Pedidos',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="receipt-outline" size={size} color={color} />
          ),
          headerShown: true,
          headerTitle: 'Meus Pedidos',
        }}
      />
      <Tab.Screen
        name="Perfil"
        component={ProfileScreen}
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-outline" size={size} color={color} />
          ),
          headerShown: true,
          headerTitle: 'Meu Perfil',
        }}
      />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  badge: {
    position: 'absolute',
    right: -6,
    top: -4,
    backgroundColor: CORES.secundario,
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 3,
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
});
