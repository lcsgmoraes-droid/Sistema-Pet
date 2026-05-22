# App Mobile Funcionario MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first employee mobile flow with operational login routing, product lookup by scanner/search, and a local POS cart that does not finalize sales.

**Architecture:** The backend profile serializer exposes `funcionario` as an operational profile when the linked `Cliente` has `tipo_cadastro == "funcionario"` and is active. The app extends its auth cache and root navigator to route employees into a dedicated stack. Employee POS state stays in a separate local Zustand store so it does not mix with the e-commerce customer cart.

**Tech Stack:** FastAPI/Python backend, Expo React Native, React Navigation native stack, Zustand, TypeScript, pytest source/contract tests, `npm run typecheck`.

---

## File Structure

- Modify `backend/app/routes/ecommerce_auth.py`: add employee profile detection and serialization.
- Modify `backend/tests/unit/test_ecommerce_mobile_tenant_context.py`: add backend profile contract tests for `funcionario`.
- Create `backend/tests/unit/test_app_mobile_funcionario_contract.py`: add source contracts for app navigation, auth cache, local POS store, and employee screens.
- Modify `app-mobile/src/types/index.ts`: add employee fields to `EcommerceUser`.
- Modify `app-mobile/src/store/auth.store.ts`: cache and restore `funcionario` operational role.
- Modify `app-mobile/src/navigation/AppNavigator.tsx`: route employees to the new navigator.
- Create `app-mobile/src/types/funcionarioNavigation.ts`: typed routes for the employee stack.
- Create `app-mobile/src/services/funcionario.service.ts`: wrapper around existing product lookup endpoints.
- Create `app-mobile/src/store/funcionarioPdv.store.ts`: local cart store for the employee POS.
- Create `app-mobile/src/navigation/FuncionarioNavigator.tsx`: employee stack navigator with logout action.
- Create `app-mobile/src/screens/funcionario/FuncionarioConsultaScreen.tsx`: search/manual lookup and add-to-cart flow.
- Create `app-mobile/src/screens/funcionario/FuncionarioScannerScreen.tsx`: camera barcode lookup for employee POS.
- Create `app-mobile/src/screens/funcionario/FuncionarioCarrinhoScreen.tsx`: local cart review and quantity adjustment.

---

### Task 1: Backend and App Contract Tests

**Files:**
- Modify: `backend/tests/unit/test_ecommerce_mobile_tenant_context.py`
- Create: `backend/tests/unit/test_app_mobile_funcionario_contract.py`

- [ ] **Step 1: Add backend profile tests before changing backend code**

Append this to `backend/tests/unit/test_ecommerce_mobile_tenant_context.py`:

```python
def test_serialize_profile_marks_funcionario_as_mobile_operational_profile():
    user = SimpleNamespace(
        id=123,
        email="funcionario@example.com",
        email_verified=True,
        nome="Funcionario Teste",
        telefone=None,
        cpf_cnpj=None,
    )
    cliente = SimpleNamespace(
        id=456,
        tipo_cadastro="funcionario",
        ativo=True,
        is_entregador=False,
        telefone=None,
        cpf=None,
        cep=None,
        endereco=None,
        numero=None,
        complemento=None,
        bairro=None,
        cidade=None,
        estado=None,
        endereco_entrega=None,
        enderecos_adicionais=None,
    )

    profile = _serialize_profile(user, cliente)

    assert profile["is_funcionario"] is True
    assert profile["funcionario_id"] == cliente.id
    assert profile["perfil_operacional"] == "funcionario"


def test_serialize_profile_keeps_delivery_priority_over_funcionario():
    user = SimpleNamespace(
        id=123,
        email="entregador@example.com",
        email_verified=True,
        nome="Entregador Teste",
        telefone=None,
        cpf_cnpj=None,
    )
    cliente = SimpleNamespace(
        id=456,
        tipo_cadastro="funcionario",
        ativo=True,
        is_entregador=True,
        telefone=None,
        cpf=None,
        cep=None,
        endereco=None,
        numero=None,
        complemento=None,
        bairro=None,
        cidade=None,
        estado=None,
        endereco_entrega=None,
        enderecos_adicionais=None,
    )

    profile = _serialize_profile(user, cliente)

    assert profile["is_funcionario"] is True
    assert profile["is_entregador"] is True
    assert profile["funcionario_id"] == cliente.id
    assert profile["perfil_operacional"] == "entregador"
```

- [ ] **Step 2: Add app source contract tests before changing app code**

Create `backend/tests/unit/test_app_mobile_funcionario_contract.py` with:

```python
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "app-mobile/src"


def _source(path: str) -> str:
    return (APP_ROOT / path).read_text(encoding="utf-8")


def test_mobile_routes_funcionario_to_dedicated_navigator():
    source = _source("navigation/AppNavigator.tsx")

    assert "FuncionarioNavigator" in source
    assert 'perfil_operacional === "funcionario"' in source
    assert "user?.is_funcionario" in source


def test_mobile_auth_cache_preserves_funcionario_role():
    source = _source("store/auth.store.ts")

    assert "is_funcionario" in source
    assert '"funcionario"' in source
    assert "cached?.is_veterinario || cached?.is_entregador || cached?.is_funcionario" in source


def test_mobile_user_type_accepts_funcionario_profile():
    source = _source("types/index.ts")

    assert "is_funcionario?: boolean" in source
    assert '"cliente" | "entregador" | "veterinario" | "funcionario"' in source


def test_funcionario_mobile_files_define_local_pdv_flow():
    assert (APP_ROOT / "navigation/FuncionarioNavigator.tsx").exists()
    assert (APP_ROOT / "types/funcionarioNavigation.ts").exists()
    assert (APP_ROOT / "services/funcionario.service.ts").exists()
    assert (APP_ROOT / "store/funcionarioPdv.store.ts").exists()
    assert (APP_ROOT / "screens/funcionario/FuncionarioConsultaScreen.tsx").exists()
    assert (APP_ROOT / "screens/funcionario/FuncionarioScannerScreen.tsx").exists()
    assert (APP_ROOT / "screens/funcionario/FuncionarioCarrinhoScreen.tsx").exists()


def test_funcionario_pdv_store_does_not_use_ecommerce_cart_endpoints():
    source = _source("store/funcionarioPdv.store.ts")

    assert "ShopService" not in source
    assert "/carrinho" not in source
    assert "adicionarProduto" in source
    assert "atualizarQuantidade" in source
    assert "limpar" in source
```

- [ ] **Step 3: Run the tests and confirm they fail for the missing behavior**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ecommerce_mobile_tenant_context.py::test_serialize_profile_marks_funcionario_as_mobile_operational_profile backend/tests/unit/test_ecommerce_mobile_tenant_context.py::test_serialize_profile_keeps_delivery_priority_over_funcionario backend/tests/unit/test_app_mobile_funcionario_contract.py -q
```

Expected: failures mentioning missing `is_funcionario` and missing app files or strings.

- [ ] **Step 4: Commit the failing contracts**

Run:

```powershell
git add -- backend/tests/unit/test_ecommerce_mobile_tenant_context.py backend/tests/unit/test_app_mobile_funcionario_contract.py
git commit -m "test: contratar app mobile funcionario"
```

---

### Task 2: Backend Employee Profile Serialization

**Files:**
- Modify: `backend/app/routes/ecommerce_auth.py`
- Test: `backend/tests/unit/test_ecommerce_mobile_tenant_context.py`

- [ ] **Step 1: Add employee detection inside `_serialize_profile`**

Replace the current `perfil_operacional` assignment block in `backend/app/routes/ecommerce_auth.py` with:

```python
    is_funcionario = bool(
        cliente
        and getattr(cliente, "tipo_cadastro", None) == "funcionario"
        and getattr(cliente, "ativo", True) is not False
    )
    if is_veterinario:
        perfil_operacional = "veterinario"
    elif is_entregador:
        perfil_operacional = "entregador"
    elif is_funcionario:
        perfil_operacional = "funcionario"
    else:
        perfil_operacional = "cliente"
```

- [ ] **Step 2: Serialize employee flags in the return dict**

In the return dict in `backend/app/routes/ecommerce_auth.py`, keep `funcionario_id` compatible with delivery and add `is_funcionario`:

```python
        "is_entregador": is_entregador,
        "funcionario_id": cliente.id if (cliente and (is_entregador or is_funcionario)) else None,
        "is_funcionario": is_funcionario,
        "is_veterinario": is_veterinario,
        "veterinario_id": cliente.id if (cliente and is_veterinario) else None,
        "perfil_operacional": perfil_operacional,
```

- [ ] **Step 3: Run backend profile tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ecommerce_mobile_tenant_context.py::test_serialize_profile_marks_veterinario_as_mobile_operational_profile backend/tests/unit/test_ecommerce_mobile_tenant_context.py::test_serialize_profile_marks_funcionario_as_mobile_operational_profile backend/tests/unit/test_ecommerce_mobile_tenant_context.py::test_serialize_profile_keeps_delivery_priority_over_funcionario -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Commit backend profile support**

Run:

```powershell
git add -- backend/app/routes/ecommerce_auth.py backend/tests/unit/test_ecommerce_mobile_tenant_context.py
git commit -m "feat: identificar funcionario no app mobile"
```

---

### Task 3: App Auth Types and Root Routing

**Files:**
- Modify: `app-mobile/src/types/index.ts`
- Modify: `app-mobile/src/store/auth.store.ts`
- Modify: `app-mobile/src/navigation/AppNavigator.tsx`
- Test: `backend/tests/unit/test_app_mobile_funcionario_contract.py`

- [ ] **Step 1: Extend `EcommerceUser`**

In `app-mobile/src/types/index.ts`, change the profile block to:

```ts
  // perfil entregador
  is_entregador?: boolean;
  funcionario_id?: number | null;
  // perfil operacional funcionario
  is_funcionario?: boolean;
  // perfil operacional veterinario
  is_veterinario?: boolean;
  veterinario_id?: number | null;
  perfil_operacional?: "cliente" | "entregador" | "veterinario" | "funcionario";
```

- [ ] **Step 2: Cache the employee role in `auth.store.ts`**

Update `cacheOperationalRole` so the guard and saved payload include `is_funcionario`:

```ts
  if (!user.is_veterinario && !user.is_entregador && !user.is_funcionario) {
    await clearOperationalRoleCache(user);
    return;
  }
```

```ts
      is_entregador: user.is_entregador ?? false,
      is_funcionario: user.is_funcionario ?? false,
      funcionario_id: user.funcionario_id ?? null,
      perfil_operacional: user.is_veterinario
        ? "veterinario"
        : user.is_entregador
          ? "entregador"
          : user.is_funcionario
            ? "funcionario"
            : user.perfil_operacional ?? "cliente",
```

- [ ] **Step 3: Restore the employee role from cache**

In `applyCachedOperationalRole`, include `is_funcionario` in the early return, parsed type, condition, and returned user:

```ts
  if (!user?.id || user.is_veterinario || user.is_entregador || user.is_funcionario) return user;
```

```ts
      is_funcionario?: boolean;
      funcionario_id?: number | null;
      perfil_operacional?: "cliente" | "entregador" | "veterinario" | "funcionario";
```

```ts
    if (cached?.is_veterinario || cached?.is_entregador || cached?.is_funcionario) {
      return {
        ...user,
        is_veterinario: cached.is_veterinario ?? user.is_veterinario ?? false,
        veterinario_id: cached.veterinario_id ?? user.veterinario_id ?? null,
        is_entregador: cached.is_entregador ?? user.is_entregador ?? false,
        is_funcionario: cached.is_funcionario ?? user.is_funcionario ?? false,
        funcionario_id: cached.funcionario_id ?? user.funcionario_id ?? null,
        perfil_operacional: cached.perfil_operacional ?? user.perfil_operacional,
      };
    }
```

- [ ] **Step 4: Clear cache only when no operational role is present**

In `loadUser`, change the customer-role cleanup condition to:

```ts
        if (
          freshUser.perfil_operacional === "cliente" &&
          !freshUser.is_veterinario &&
          !freshUser.is_entregador &&
          !freshUser.is_funcionario
        ) {
          await clearOperationalRoleCache(freshUser);
        }
```

- [ ] **Step 5: Route employees to `FuncionarioNavigator`**

In `app-mobile/src/navigation/AppNavigator.tsx`, add:

```ts
import FuncionarioNavigator from './FuncionarioNavigator';
```

Then extend the routing chain after delivery:

```tsx
  } else if (user?.is_entregador) {
    activeNav = <EntregadorNavigator />;
  } else if (user?.is_funcionario || user?.perfil_operacional === "funcionario") {
    activeNav = <FuncionarioNavigator />;
  } else {
    activeNav = <MainNavigator />;
  }
```

- [ ] **Step 6: Run source contract tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_app_mobile_funcionario_contract.py::test_mobile_routes_funcionario_to_dedicated_navigator backend/tests/unit/test_app_mobile_funcionario_contract.py::test_mobile_auth_cache_preserves_funcionario_role backend/tests/unit/test_app_mobile_funcionario_contract.py::test_mobile_user_type_accepts_funcionario_profile -q
```

Expected: tests still fail only because `FuncionarioNavigator` does not exist yet.

---

### Task 4: Local Employee POS Store and Service

**Files:**
- Create: `app-mobile/src/services/funcionario.service.ts`
- Create: `app-mobile/src/store/funcionarioPdv.store.ts`
- Test: `backend/tests/unit/test_app_mobile_funcionario_contract.py`

- [ ] **Step 1: Create the employee product service**

Create `app-mobile/src/services/funcionario.service.ts`:

```ts
import { buscarProdutoPorBarcode, listarProdutos } from "./shop.service";
import { Produto } from "../types";

export async function buscarProdutosFuncionario(busca: string): Promise<Produto[]> {
  const termo = busca.trim();
  if (termo.length > 0 && termo.length < 2) return [];
  const { produtos } = await listarProdutos({
    busca: termo || undefined,
    somenteComEstoque: false,
    ordenacao: "nome",
    cacheBust: Date.now(),
  });
  return produtos;
}

export async function buscarProdutoPorBarcodeFuncionario(barcode: string): Promise<Produto | null> {
  return buscarProdutoPorBarcode(barcode);
}
```

- [ ] **Step 2: Create the local POS store**

Create `app-mobile/src/store/funcionarioPdv.store.ts`:

```ts
import { create } from "zustand";
import { Produto } from "../types";

export interface FuncionarioPdvItem {
  produto_id: number;
  nome: string;
  preco_unitario: number;
  quantidade: number;
  subtotal: number;
  foto_url?: string | null;
  codigo?: string | null;
  codigo_barras?: string | null;
  estoque?: number | null;
}

interface FuncionarioPdvState {
  itens: FuncionarioPdvItem[];
  subtotal: number;
  adicionarProduto: (produto: Produto, quantidade?: number) => void;
  atualizarQuantidade: (produtoId: number, quantidade: number) => void;
  removerProduto: (produtoId: number) => void;
  limpar: () => void;
  totalItens: () => number;
}

function precoAtual(produto: Produto): number {
  return Number(produto.promocao_ativa && produto.preco_promocional ? produto.preco_promocional : produto.preco) || 0;
}

function estoqueDisponivel(produto: Produto | FuncionarioPdvItem): number | null {
  const estoque = Number(produto.estoque);
  return Number.isFinite(estoque) ? estoque : null;
}

function recalcular(itens: FuncionarioPdvItem[]): { itens: FuncionarioPdvItem[]; subtotal: number } {
  const normalizados = itens.map((item) => ({
    ...item,
    subtotal: item.preco_unitario * item.quantidade,
  }));
  return {
    itens: normalizados,
    subtotal: normalizados.reduce((acc, item) => acc + item.subtotal, 0),
  };
}

export const useFuncionarioPdvStore = create<FuncionarioPdvState>()((set, get) => ({
  itens: [],
  subtotal: 0,

  adicionarProduto: (produto, quantidade = 1) => {
    const qtd = Math.max(1, Math.floor(Number(quantidade) || 1));
    const estoque = estoqueDisponivel(produto);
    const { itens } = get();
    const existente = itens.find((item) => item.produto_id === produto.id);
    const quantidadeAtual = existente?.quantidade ?? 0;
    const novaQuantidade = quantidadeAtual + qtd;

    if (estoque !== null && novaQuantidade > estoque) {
      throw new Error("Quantidade maior que o estoque disponivel.");
    }

    const novosItens = existente
      ? itens.map((item) =>
          item.produto_id === produto.id
            ? { ...item, quantidade: novaQuantidade, estoque }
            : item,
        )
      : [
          ...itens,
          {
            produto_id: produto.id,
            nome: produto.nome,
            preco_unitario: precoAtual(produto),
            quantidade: qtd,
            subtotal: precoAtual(produto) * qtd,
            foto_url: produto.foto_url,
            codigo: produto.codigo,
            codigo_barras: produto.codigo_barras,
            estoque,
          },
        ];

    set(recalcular(novosItens));
  },

  atualizarQuantidade: (produtoId, quantidade) => {
    const qtd = Math.max(0, Math.floor(Number(quantidade) || 0));
    const { itens } = get();
    if (qtd === 0) {
      const novosItens = itens.filter((item) => item.produto_id !== produtoId);
      set(recalcular(novosItens));
      return;
    }

    const itemAtual = itens.find((item) => item.produto_id === produtoId);
    if (itemAtual?.estoque !== null && itemAtual?.estoque !== undefined && qtd > itemAtual.estoque) {
      throw new Error("Quantidade maior que o estoque disponivel.");
    }

    set(recalcular(itens.map((item) => (item.produto_id === produtoId ? { ...item, quantidade: qtd } : item))));
  },

  removerProduto: (produtoId) => {
    set(recalcular(get().itens.filter((item) => item.produto_id !== produtoId)));
  },

  limpar: () => set({ itens: [], subtotal: 0 }),

  totalItens: () => get().itens.reduce((acc, item) => acc + item.quantidade, 0),
}));
```

- [ ] **Step 3: Run store source contract**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_app_mobile_funcionario_contract.py::test_funcionario_pdv_store_does_not_use_ecommerce_cart_endpoints -q
```

Expected: selected test passes.

---

### Task 5: Employee Navigation and Screens

**Files:**
- Create: `app-mobile/src/types/funcionarioNavigation.ts`
- Create: `app-mobile/src/navigation/FuncionarioNavigator.tsx`
- Create: `app-mobile/src/screens/funcionario/FuncionarioConsultaScreen.tsx`
- Create: `app-mobile/src/screens/funcionario/FuncionarioScannerScreen.tsx`
- Create: `app-mobile/src/screens/funcionario/FuncionarioCarrinhoScreen.tsx`
- Modify: `app-mobile/src/navigation/AppNavigator.tsx`
- Test: `backend/tests/unit/test_app_mobile_funcionario_contract.py`

- [ ] **Step 1: Add employee route types**

Create `app-mobile/src/types/funcionarioNavigation.ts`:

```ts
export type FuncionarioStackParamList = {
  FuncionarioConsulta: undefined;
  FuncionarioScanner: undefined;
  FuncionarioCarrinho: undefined;
};
```

- [ ] **Step 2: Create `FuncionarioNavigator`**

Create `app-mobile/src/navigation/FuncionarioNavigator.tsx`:

```tsx
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import React from "react";
import { Alert, Text, TouchableOpacity } from "react-native";
import FuncionarioCarrinhoScreen from "../screens/funcionario/FuncionarioCarrinhoScreen";
import FuncionarioConsultaScreen from "../screens/funcionario/FuncionarioConsultaScreen";
import FuncionarioScannerScreen from "../screens/funcionario/FuncionarioScannerScreen";
import { useAuthStore } from "../store/auth.store";
import { CORES } from "../theme";
import { FuncionarioStackParamList } from "../types/funcionarioNavigation";

const Stack = createNativeStackNavigator<FuncionarioStackParamList>();

function HeaderLogoutAction() {
  const { logout } = useAuthStore();

  const confirmarLogout = () => {
    Alert.alert("Sair da conta", "Deseja sair da conta de funcionario?", [
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

export default function FuncionarioNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerRight: HeaderLogoutAction,
        headerTitleStyle: { fontWeight: "800" },
      }}
    >
      <Stack.Screen name="FuncionarioConsulta" component={FuncionarioConsultaScreen} options={{ title: "PDV Funcionario" }} />
      <Stack.Screen name="FuncionarioScanner" component={FuncionarioScannerScreen} options={{ title: "Escanear", headerShown: false }} />
      <Stack.Screen name="FuncionarioCarrinho" component={FuncionarioCarrinhoScreen} options={{ title: "Carrinho PDV" }} />
    </Stack.Navigator>
  );
}
```

- [ ] **Step 3: Create the manual lookup screen**

Create `app-mobile/src/screens/funcionario/FuncionarioConsultaScreen.tsx` with a search input, scanner button, cart summary, and product list. The screen must call `buscarProdutosFuncionario`, use `useFuncionarioPdvStore`, block zero-stock additions, and navigate to `FuncionarioScanner` and `FuncionarioCarrinho`.

Use these imports and component signature:

```tsx
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { buscarProdutosFuncionario } from "../../services/funcionario.service";
import { useFuncionarioPdvStore } from "../../store/funcionarioPdv.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { Produto } from "../../types";
import { formatarMoeda } from "../../utils/format";

export default function FuncionarioConsultaScreen() {
  const navigation = useNavigation<any>();
  const { adicionarProduto, subtotal, totalItens } = useFuncionarioPdvStore();
```

The product add handler must be:

```tsx
  function adicionar(item: Produto) {
    const estoque = Number(item.estoque ?? 0);
    if (Number.isFinite(estoque) && estoque <= 0) {
      Alert.alert("Sem estoque", "Produto sem estoque disponivel.");
      return;
    }

    try {
      adicionarProduto(item, 1);
    } catch (error: any) {
      Alert.alert("Estoque", error?.message || "Nao foi possivel adicionar o produto.");
    }
  }
```

- [ ] **Step 4: Create the employee scanner screen**

Create `app-mobile/src/screens/funcionario/FuncionarioScannerScreen.tsx` by adapting `app-mobile/src/screens/shop/BarcodeScannerScreen.tsx` with these employee-specific changes:

```tsx
import { buscarProdutoPorBarcodeFuncionario } from "../../services/funcionario.service";
import { useFuncionarioPdvStore } from "../../store/funcionarioPdv.store";
```

Use local store action:

```tsx
  const { adicionarProduto } = useFuncionarioPdvStore();
```

Use this add action:

```tsx
  function adicionarAoCarrinho() {
    if (!produtoEncontrado) return;
    if (Number(produtoEncontrado.estoque ?? 0) <= 0) {
      Alert.alert("Sem estoque", "Este produto esta sem estoque disponivel.");
      return;
    }
    try {
      adicionarProduto(produtoEncontrado, 1);
      Alert.alert("Adicionado", `${produtoEncontrado.nome} foi ao carrinho PDV.`, [
        { text: "Escanear mais", onPress: () => { setProdutoEncontrado(null); ultimoScan.current = ""; setScanAtivo(true); } },
        { text: "Ver carrinho", onPress: () => navigation.navigate("FuncionarioCarrinho") },
      ]);
    } catch (error: any) {
      Alert.alert("Estoque", error?.message || "Nao foi possivel adicionar ao carrinho.");
    }
  }
```

- [ ] **Step 5: Create the local cart screen**

Create `app-mobile/src/screens/funcionario/FuncionarioCarrinhoScreen.tsx` with:

```tsx
import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useFuncionarioPdvStore } from "../../store/funcionarioPdv.store";
import { CORES, ESPACO, FONTE, RAIO, SOMBRA } from "../../theme";
import { formatarMoeda } from "../../utils/format";

export default function FuncionarioCarrinhoScreen() {
  const { itens, subtotal, atualizarQuantidade, removerProduto, limpar } = useFuncionarioPdvStore();
```

Quantity buttons must call:

```tsx
  function alterarQuantidade(produtoId: number, quantidade: number) {
    try {
      atualizarQuantidade(produtoId, quantidade);
    } catch (error: any) {
      Alert.alert("Estoque", error?.message || "Nao foi possivel alterar a quantidade.");
    }
  }
```

The clear action must ask confirmation:

```tsx
  function confirmarLimpar() {
    if (itens.length === 0) return;
    Alert.alert("Limpar carrinho", "Deseja remover todos os itens?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Limpar", style: "destructive", onPress: limpar },
    ]);
  }
```

- [ ] **Step 6: Run app source contracts**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_app_mobile_funcionario_contract.py -q
```

Expected: all source contract tests pass.

- [ ] **Step 7: Commit app navigation, store, and screens**

Run:

```powershell
git add -- app-mobile/src/types/index.ts app-mobile/src/store/auth.store.ts app-mobile/src/navigation/AppNavigator.tsx app-mobile/src/types/funcionarioNavigation.ts app-mobile/src/services/funcionario.service.ts app-mobile/src/store/funcionarioPdv.store.ts app-mobile/src/navigation/FuncionarioNavigator.tsx app-mobile/src/screens/funcionario/FuncionarioConsultaScreen.tsx app-mobile/src/screens/funcionario/FuncionarioScannerScreen.tsx app-mobile/src/screens/funcionario/FuncionarioCarrinhoScreen.tsx backend/tests/unit/test_app_mobile_funcionario_contract.py
git commit -m "feat: adicionar fluxo mobile de funcionario"
```

---

### Task 6: Full Verification and Finish

**Files:**
- Verify: backend tests and app TypeScript.

- [ ] **Step 1: Run backend mobile contract tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ecommerce_mobile_tenant_context.py backend/tests/unit/test_app_mobile_barcode_contract.py backend/tests/unit/test_app_mobile_funcionario_contract.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run app mobile typecheck**

Run:

```powershell
Push-Location app-mobile; npm run typecheck; Pop-Location
```

Expected: TypeScript exits with code 0.

- [ ] **Step 3: Inspect final diff**

Run:

```powershell
git status --short --branch
git diff --stat HEAD
```

Expected: branch is `feat/20260522-1243-app-mobile-funcionario-mvp`; no uncommitted changes if all task commits were made.

- [ ] **Step 4: Finish the task branch**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: adicionar app mobile funcionario mvp" -Push
```

Expected: script creates the final task commit if needed and pushes the feature branch for PR flow.

---

## Self-Review

- Spec coverage: profile detection is covered in Tasks 1-2; app routing and cache are covered in Task 3; search/scanner/cart local are covered in Tasks 4-5; non-finalization is protected by the separate local store and source contract that forbids e-commerce cart endpoints.
- Placeholder scan: the plan contains concrete paths, commands, and code snippets for each change step.
- Type consistency: the profile name is `funcionario` across backend serializer, `EcommerceUser`, auth cache, root navigator, and employee route tests.
