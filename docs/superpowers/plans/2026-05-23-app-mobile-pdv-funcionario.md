# App Mobile PDV Funcionario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mobile employee PDV flow to pass sales from the app while reusing ERP sale, stock, finance, caixa and commission rules.

**Architecture:** Add mobile-only `/app/funcionario/pdv/<recurso>` endpoints as a thin layer over existing ERP models and `VendaService`. The React Native app gets a small employee home screen, a focused PDV screen, and a service module that talks only to the mobile endpoints.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, React Native, Expo Camera, TypeScript, Axios.

---

## File Structure

- Modify `backend/app/routes/app_mobile_routes.py`: add PDV response/request schemas, product/client/caixa search helpers, and finalization endpoint.
- Create `backend/tests/unit/test_app_mobile_funcionario_pdv_contract.py`: source-level contract tests for endpoints, schemas, and service delegation.
- Modify `app-mobile/src/types/funcionarioNavigation.ts`: add employee home and PDV route names.
- Modify `app-mobile/src/types/index.ts`: add PDV mobile TypeScript types.
- Create `app-mobile/src/services/funcionarioPdv.service.ts`: API wrapper and normalizers for PDV mobile.
- Create `app-mobile/src/screens/funcionario/FuncionarioHomeScreen.tsx`: entry screen with actions.
- Create `app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx`: mobile sale UI.
- Modify `app-mobile/src/navigation/FuncionarioNavigator.tsx`: make home the first screen and register PDV/balance.

---

### Task 1: Backend Contract Tests

**Files:**
- Create: `backend/tests/unit/test_app_mobile_funcionario_pdv_contract.py`
- Read: `backend/app/routes/app_mobile_routes.py`

- [ ] **Step 1: Write source contract tests**

```python
from pathlib import Path

SOURCE = Path("backend/app/routes/app_mobile_routes.py").read_text(encoding="utf-8")


def test_funcionario_pdv_endpoints_exist():
    assert '@router.get("/funcionario/pdv/produtos/buscar"' in SOURCE
    assert '@router.get("/funcionario/pdv/produtos/barcode/{barcode}"' in SOURCE
    assert '@router.get("/funcionario/pdv/clientes/buscar"' in SOURCE
    assert '@router.get("/funcionario/pdv/caixa/aberto"' in SOURCE
    assert '@router.post("/funcionario/pdv/vendas/finalizar"' in SOURCE


def test_funcionario_pdv_delegates_to_venda_service():
    assert "VendaService.criar_venda" in SOURCE
    assert "VendaService.finalizar_venda" in SOURCE
    assert "processar_comissoes_venda" in SOURCE


def test_funcionario_pdv_does_not_open_or_close_cash_register():
    assert '"/funcionario/pdv/caixa/abrir"' not in SOURCE
    assert '"/funcionario/pdv/caixa/fechar"' not in SOURCE
    assert "AbrirCaixaSchema" not in SOURCE
    assert "FecharCaixaSchema" not in SOURCE


def test_funcionario_pdv_uses_logged_employee_as_commission_person():
    assert '"funcionario_id": funcionario.id' in SOURCE
    assert '"vendedor_id": current_user.id' in SOURCE


def test_funcionario_pdv_uses_sellable_erp_products_not_ecommerce_catalog():
    assert "Produto.tipo_produto.in_(['SIMPLES', 'VARIACAO', 'KIT'])" in SOURCE
    assert "Produto.anunciar_app" not in SOURCE
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
$env:DATABASE_URL='sqlite:///./test.db'; .\backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_app_mobile_funcionario_pdv_contract.py -q
```

Expected: fail because the new PDV endpoints are not implemented yet.

---

### Task 2: Backend Mobile PDV Endpoints

**Files:**
- Modify: `backend/app/routes/app_mobile_routes.py`
- Test: `backend/tests/unit/test_app_mobile_funcionario_pdv_contract.py`

- [ ] **Step 1: Add schemas near the employee stock schemas**

```python
class FuncionarioPdvProdutoResponse(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    unidade: str = "UN"
    preco_venda: float = 0
    estoque_atual: float = 0
    imagem_url: Optional[str] = None
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None
    vendavel: bool = True
    aviso: Optional[str] = None


class FuncionarioPdvClienteResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    nome: str
    telefone: Optional[str] = None
    celular: Optional[str] = None
    documento: Optional[str] = None


class FuncionarioPdvCaixaResponse(BaseModel):
    aberto: bool
    caixa_id: Optional[int] = None
    numero_caixa: Optional[int] = None
    mensagem: str


class FuncionarioPdvItemRequest(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    preco_unitario: float = Field(ge=0)


class FuncionarioPdvPagamentoRequest(BaseModel):
    forma_pagamento: str
    valor: float = Field(gt=0)
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None


class FuncionarioPdvFinalizarRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    pagamento: FuncionarioPdvPagamentoRequest
    observacoes: Optional[str] = None


class FuncionarioPdvFinalizarResponse(BaseModel):
    status: str
    venda_id: int
    numero_venda: str
    total: float
    total_pago: float
    forma_pagamento: str
    mensagem: str
```

- [ ] **Step 2: Add serializers and query helpers**

```python
def _serialize_funcionario_pdv_produto(produto: Produto) -> dict:
    vendavel = (
        bool(produto.ativo)
        and produto.situacao is not False
        and produto.tipo_produto in ["SIMPLES", "VARIACAO", "KIT"]
    )
    aviso = None if vendavel else "Produto nao vendavel no PDV."
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": produto.codigo,
        "codigo_barras": produto.codigo_barras,
        "unidade": produto.unidade or "UN",
        "preco_venda": float(produto.preco_venda or 0),
        "estoque_atual": float(produto.estoque_atual or 0),
        "imagem_url": produto.imagem_principal,
        "tipo_produto": produto.tipo_produto,
        "tipo_kit": produto.tipo_kit,
        "vendavel": vendavel,
        "aviso": aviso,
    }


def _query_produtos_pdv_base(db: Session, tenant_id: str):
    return db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.situacao.is_not(False),
        Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
    )
```

- [ ] **Step 3: Add product, client and caixa endpoints**

```python
@router.get("/funcionario/pdv/produtos/buscar", response_model=list[FuncionarioPdvProdutoResponse])
def buscar_produtos_funcionario_pdv(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []
    query = _query_produtos_pdv_base(db, tenant_id)
    for palavra in [p for p in termo.split() if p.strip()]:
        like = f"%{palavra}%"
        query = query.filter(or_(Produto.nome.ilike(like), Produto.codigo.ilike(like), Produto.codigo_barras.ilike(like)))
    return [_serialize_funcionario_pdv_produto(produto) for produto in query.order_by(Produto.nome.asc()).limit(20).all()]


@router.get("/funcionario/pdv/produtos/barcode/{barcode}", response_model=FuncionarioPdvProdutoResponse)
def buscar_produto_funcionario_pdv_barcode(
    barcode: str,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    produto = _query_produtos_pdv_base(db, tenant_id).filter(or_(*_barcode_filters_for_produto(barcode))).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto ERP nao encontrado para este codigo.")
    return _serialize_funcionario_pdv_produto(produto)


@router.get("/funcionario/pdv/clientes/buscar", response_model=list[FuncionarioPdvClienteResponse])
def buscar_clientes_funcionario_pdv(
    q: str = "",
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    termo = (q or "").strip()
    if len(termo) < 2:
        return []
    like = f"%{termo}%"
    clientes = db.query(Cliente).filter(Cliente.tenant_id == tenant_id, Cliente.tipo_cadastro == "cliente", Cliente.ativo == True, or_(Cliente.nome.ilike(like), Cliente.codigo.ilike(like), Cliente.cpf.ilike(like), Cliente.telefone.ilike(like), Cliente.celular.ilike(like))).order_by(Cliente.nome.asc()).limit(20).all()
    return [_serialize_funcionario_pdv_cliente(cliente) for cliente in clientes]


@router.get("/funcionario/pdv/caixa/aberto", response_model=FuncionarioPdvCaixaResponse)
def obter_caixa_aberto_funcionario_pdv(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    caixa = db.query(Caixa).filter(Caixa.usuario_id == current_user.id, Caixa.tenant_id == tenant_id, Caixa.status == "aberto").first()
    if not caixa:
        return {"aberto": False, "caixa_id": None, "numero_caixa": None, "mensagem": "Abra um caixa no ERP web antes de vender pelo app."}
    return {"aberto": True, "caixa_id": caixa.id, "numero_caixa": caixa.numero_caixa, "mensagem": "Caixa aberto."}
```

- [ ] **Step 4: Add finalization endpoint**

```python
@router.post("/funcionario/pdv/vendas/finalizar", response_model=FuncionarioPdvFinalizarResponse)
def finalizar_venda_funcionario_pdv(
    dados: FuncionarioPdvFinalizarRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    itens = [
        {
            "tipo": "produto",
            "produto_id": item.produto_id,
            "quantidade": float(item.quantidade),
            "preco_unitario": float(item.preco_unitario),
            "desconto_item": 0,
            "subtotal": round(float(item.quantidade) * float(item.preco_unitario), 2),
        }
        for item in dados.itens
    ]
    criar_payload = {
        "cliente_id": dados.cliente_id,
        "vendedor_id": current_user.id,
        "funcionario_id": funcionario.id,
        "itens": itens,
        "tenant_id": tenant_id,
        "observacoes": dados.observacoes,
        "tem_entrega": False,
        "taxa_entrega": 0,
    }
    venda_criada = VendaService.criar_venda(payload=criar_payload, user_id=current_user.id, db=db)
    resultado = VendaService.finalizar_venda(
        venda_id=venda_criada["id"],
        pagamentos=[dados.pagamento.dict()],
        user_id=current_user.id,
        user_nome=current_user.nome or current_user.email or "Funcionario",
        tenant_id=tenant_id,
        db=db,
    )
    processar_comissoes_venda(venda_criada["id"], funcionario.id, dados.pagamento.valor, current_user.id, db)
    return {
        "status": resultado["venda"]["status"],
        "venda_id": venda_criada["id"],
        "numero_venda": resultado["venda"]["numero_venda"],
        "total": resultado["venda"]["total"],
        "total_pago": resultado["venda"]["total_pago"],
        "forma_pagamento": dados.pagamento.forma_pagamento,
        "mensagem": "Venda registrada pelo app.",
    }
```

- [ ] **Step 5: Run backend tests**

Run:

```powershell
$env:DATABASE_URL='sqlite:///./test.db'; .\backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_app_mobile_funcionario_pdv_contract.py -q
```

Expected: pass.

---

### Task 3: App Mobile Types and Service

**Files:**
- Modify: `app-mobile/src/types/index.ts`
- Create: `app-mobile/src/services/funcionarioPdv.service.ts`

- [ ] **Step 1: Add TypeScript types**

```ts
export interface FuncionarioPdvProduto {
  id: number;
  nome: string;
  codigo?: string | null;
  codigo_barras?: string | null;
  unidade?: string;
  preco_venda: number;
  estoque_atual: number;
  imagem_url?: string | null;
  tipo_produto?: string | null;
  tipo_kit?: string | null;
  vendavel: boolean;
  aviso?: string | null;
}
```

- [ ] **Step 2: Add service methods**

```ts
export async function buscarProdutoPdvPorBarcode(barcode: string): Promise<FuncionarioPdvProduto | null> {
  try {
    const response = await api.get(`/app/funcionario/pdv/produtos/barcode/${encodeURIComponent(barcode)}`);
    return normalizarProdutoPdv(response.data);
  } catch (error: any) {
    if (error?.response?.status === 404) return null;
    throw error;
  }
}

export async function buscarProdutosPdv(termo: string): Promise<FuncionarioPdvProduto[]> {
  const response = await api.get("/app/funcionario/pdv/produtos/buscar", { params: { q: termo.trim() } });
  return Array.isArray(response.data) ? response.data.map(normalizarProdutoPdv) : [];
}

export async function buscarClientesPdv(termo: string): Promise<FuncionarioPdvCliente[]> {
  const response = await api.get("/app/funcionario/pdv/clientes/buscar", { params: { q: termo.trim() } });
  return Array.isArray(response.data) ? response.data.map(normalizarClientePdv) : [];
}

export async function obterCaixaAbertoPdv(): Promise<FuncionarioPdvCaixa> {
  const response = await api.get("/app/funcionario/pdv/caixa/aberto");
  return response.data;
}

export async function finalizarVendaPdv(payload: FuncionarioPdvFinalizarPayload): Promise<FuncionarioPdvFinalizarResponse> {
  const response = await api.post("/app/funcionario/pdv/vendas/finalizar", payload);
  return response.data;
}
```

- [ ] **Step 3: Run typecheck**

Run:

```powershell
npm run typecheck
```

Expected: pass after UI task is complete.

---

### Task 4: App Mobile Navigation and Screens

**Files:**
- Modify: `app-mobile/src/types/funcionarioNavigation.ts`
- Modify: `app-mobile/src/navigation/FuncionarioNavigator.tsx`
- Create: `app-mobile/src/screens/funcionario/FuncionarioHomeScreen.tsx`
- Create: `app-mobile/src/screens/funcionario/FuncionarioPdvScreen.tsx`

- [ ] **Step 1: Add navigation routes**

```ts
export type FuncionarioStackParamList = {
  FuncionarioHome: undefined;
  FuncionarioBalanco: undefined;
  FuncionarioPdv: undefined;
};
```

- [ ] **Step 2: Create home screen**

```tsx
export default function FuncionarioHomeScreen({ navigation }) {
  return (
    <View>
      <TouchableOpacity onPress={() => navigation.navigate("FuncionarioBalanco")} />
      <TouchableOpacity onPress={() => navigation.navigate("FuncionarioPdv")} />
    </View>
  );
}
```

- [ ] **Step 3: Create PDV screen**

```tsx
export default function FuncionarioPdvScreen() {
  // camera/search -> cart -> client optional -> payment -> finalizar
}
```

- [ ] **Step 4: Register screens**

```tsx
<Stack.Screen name="FuncionarioHome" component={FuncionarioHomeScreen} options={{ title: "Funcionario" }} />
<Stack.Screen name="FuncionarioBalanco" component={FuncionarioBalancoScreen} options={{ title: "Balanco de Estoque" }} />
<Stack.Screen name="FuncionarioPdv" component={FuncionarioPdvScreen} options={{ title: "PDV Rapido" }} />
```

---

### Task 5: Verification and Commit

**Files:**
- All files modified in previous tasks.

- [ ] **Step 1: Run backend contract tests**

```powershell
$env:DATABASE_URL='sqlite:///./test.db'; .\backend\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_app_mobile_funcionario_pdv_contract.py -q
```

- [ ] **Step 2: Run app mobile typecheck**

```powershell
npm run typecheck
```

- [ ] **Step 3: Inspect Git status**

```powershell
git status --short
```

- [ ] **Step 4: Commit and push branch**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git_finish_task.ps1 -Mensagem "feat: adiciona pdv mobile funcionario" -Push
```

---

## Self-Review

- Spec coverage: product scan/search, cart, optional client, simple payment, caixa prerequisite, official ERP sale flow, logged employee commission, and no cash management are covered.
- Placeholder scan: no unresolved placeholder markers.
- Type consistency: route names, service names and screen names are aligned across backend, app service and navigation.
