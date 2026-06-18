# 🛍️ Módulo Produtos - SPRINT 7 PASSO 1

## 📋 Visão Geral

Módulo completo de gerenciamento de produtos para o ERP Pet Shop. Desenvolvido com foco em **UX limpa**, **código organizado** e **arquitetura escalável**.

---

## 🏗️ Estrutura de Pastas

```
frontend/src/pages/produtos/
├── components/               # Componentes reutilizáveis
│   ├── ProductFilters.tsx   # Filtros de busca e status
│   └── ProductTable.tsx     # Tabela de listagem
├── hooks/                   # Custom hooks
│   └── useProducts.ts       # Lógica de estado e API
├── styles/                  # Estilos CSS
│   ├── ProdutosPage.css
│   ├── ProductFilters.css
│   └── ProductTable.css
├── ProdutosPage.tsx         # Página principal
├── types.ts                 # Tipos TypeScript
└── index.ts                 # Exportações
```

---

## ✨ Funcionalidades Implementadas

### 1. **Listagem de Produtos**

- ✅ Exibição em tabela responsiva
- ✅ Colunas: Nome, SKU, Tipo, Preço, Estoque, Status, Ações
- ✅ Paginação (20 itens por página)

### 2. **Filtros**

- ✅ Busca por nome ou SKU (tempo real)
- ✅ Filtro por status (Ativo/Inativo)
- ✅ Contador de produtos encontrados
- ✅ Botão "Limpar filtros"

### 3. **Ações**

- ✅ Botão "Novo Produto" (navega para `/produtos/novo`)
- ✅ Editar produto (navega para `/produtos/:id/editar`)
- ✅ Ativar/Inativar produto
- ✅ Excluir produto (com confirmação)

### 4. **Estados Visuais**

- ✅ **Loading**: Spinner durante carregamento
- ✅ **Empty**: Mensagem quando não há produtos
- ✅ **Error**: Mensagem de erro com detalhes

---

## 🎨 Design System

### Paleta de Cores

```css
Primary:    #2563eb (azul)
Success:    #059669 (verde)
Danger:     #dc2626 (vermelho)
Warning:    #f59e0b (amarelo)
Text:       #1f2937 (cinza escuro)
Secondary:  #6b7280 (cinza médio)
Border:     #e5e7eb (cinza claro)
Background: #fafafa (cinza muito claro)
```

### Tipografia

- **Títulos**: 32px, weight 700
- **Subtítulos**: 15px, weight 400
- **Corpo**: 14px, weight 400/500
- **Labels**: 13px, weight 600

### Espaçamento

- Padding padrão: 16px - 24px
- Gap entre elementos: 12px - 16px
- Border radius: 6px - 12px

---

## 🔌 Integração com API

### Endpoint Principal

```
GET /produtos?pagina=1&limite=20&busca=termo&status=ativo
```

### Formato de Resposta Esperado

```typescript
{
  produtos: Product[],
  total: number,
  pagina: number,
  total_paginas: number
}
```

### Modelo de Produto

```typescript
interface Product {
  id: number;
  nome: string;
  sku: string;
  tipo: "simples" | "variacao" | "kit";
  preco: number;
  estoque: number;
  status: "ativo" | "inativo";
  marca?: string;
  categoria?: string;
}
```

---

## 🚀 Como Usar

### 1. Importar na Aplicação

```typescript
import { ProdutosPage } from "@/pages/produtos";
```

### 2. Adicionar Rota

```typescript
<Route path="/produtos" element={<ProdutosPage />} />
```

### 3. Configuração da API

O hook `useProducts` espera que o token esteja em `localStorage`:

```typescript
const token = localStorage.getItem("token");
```

---

## 📱 Responsividade

### Desktop (> 768px)

- Layout completo com todas as colunas
- Filtros em linha horizontal
- Tabela com espaçamento amplo

### Tablet (768px)

- Filtros em coluna
- Colunas menos importantes ocultas
- Botões de ação empilhados

### Mobile (< 480px)

- Layout simplificado
- Apenas colunas essenciais
- Botões compactos

---

## 🧩 Componentes

### ProdutosPage

**Responsabilidade**: Composição e orquestração  
**Props**: Nenhuma (página raiz)  
**Estado**: Gerenciado pelo hook `useProducts`

### ProductFiltersComponent

**Responsabilidade**: Controles de filtro  
**Props**:

- `filters`: Estado atual dos filtros
- `onFiltersChange`: Callback de mudança
- `totalProducts`: Contador de produtos

### ProductTableComponent

**Responsabilidade**: Exibição e ações  
**Props**:

- `products`: Array de produtos
- `loading`: Estado de carregamento
- `error`: Mensagem de erro
- `onDelete`: Callback de exclusão
- `onToggleStatus`: Callback de mudança de status

---

## 🔧 Hooks Customizados

### useProducts()

**Retorno**:

```typescript
{
  products: Product[];          // Lista de produtos
  loading: boolean;             // Estado de carregamento
  error: string | null;         // Mensagem de erro
  currentPage: number;          // Página atual
  totalPages: number;           // Total de páginas
  total: number;                // Total de produtos
  filters: ProductFilters;      // Filtros ativos
  setFilters: (f) => void;      // Atualizar filtros
  setCurrentPage: (p) => void;  // Mudar página
  refetch: () => void;          // Recarregar dados
  deleteProduct: (id) => void;  // Excluir produto
  toggleProductStatus: (id, status) => void; // Ativar/Inativar
}
```

---

## ⚡ Performance

### Otimizações Implementadas

- ✅ `useCallback` para evitar re-renders desnecessários
- ✅ Debounce automático no filtro de busca
- ✅ Lazy loading de imagens (preparado)
- ✅ Paginação para limitar dados carregados

### Métricas Alvo

- **Time to Interactive**: < 1s
- **First Contentful Paint**: < 500ms
- **Bundle size**: < 50KB (gzipped)

---

## 🧪 Próximos Passos (Sprints Futuros)

### Sprint 7 - Passo 2: Cadastro de Produtos

- [ ] Formulário de criação
- [ ] Validações
- [ ] Upload de imagem

### Sprint 7 - Passo 3: Edição de Produtos

- [ ] Formulário de edição
- [ ] Histórico de alterações

### Sprint 7 - Passo 4: Variações

- [ ] Gestão de atributos
- [ ] Combinações de variação

### Sprint 7 - Passo 5: Kits

- [ ] Composição de kits
- [ ] Cálculo de preço e estoque

---

## 📝 Decisões de Arquitetura

### Por que TypeScript?

- **Type safety**: Prevenção de erros em tempo de desenvolvimento
- **Autocomplete**: Melhor DX (Developer Experience)
- **Documentação**: Tipos como documentação viva

### Por que Custom Hooks?

- **Separação de responsabilidades**: Lógica isolada da UI
- **Reutilização**: Hook pode ser usado em outros contextos
- **Testabilidade**: Lógica facilmente testável

### Por que CSS Module?

- **Escopo**: Estilos não vazam para outros componentes
- **Manutenibilidade**: Fácil encontrar e alterar estilos
- **Performance**: CSS é carregado apenas quando necessário

### Por que Não Redux?

- **Simplicidade**: Estado local é suficiente para este módulo
- **Performance**: Menos overhead
- **Manutenibilidade**: Menos boilerplate

---

## 🎯 Princípios Seguidos

### SOLID

- **S**: Cada componente tem uma responsabilidade única
- **O**: Componentes abertos para extensão, fechados para modificação
- **L**: Componentes podem ser substituídos por implementações alternativas
- **I**: Interfaces mínimas e específicas
- **D**: Dependências injetadas via props

### Clean Code

- ✅ Nomes descritivos
- ✅ Funções pequenas e focadas
- ✅ Comentários apenas quando necessário
- ✅ Formatação consistente

### DRY (Don't Repeat Yourself)

- ✅ Estilos comuns em variáveis CSS
- ✅ Lógica compartilhada em hooks
- ✅ Componentes reutilizáveis

---

## 🐛 Troubleshooting

### Produtos não carregam

1. Verificar token no localStorage
2. Verificar endpoint da API
3. Verificar console do navegador

### Filtros não funcionam

1. Verificar se `setFilters` está sendo chamado
2. Verificar query params enviados à API
3. Verificar debounce do input

### Estilos não aplicados

1. Verificar importação dos CSS
2. Verificar ordem de importação
3. Verificar conflitos de classe

---

## 📚 Referências

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Linear Design System](https://linear.app/design)
- [Stripe Design](https://stripe.com/design)

---

**Desenvolvido com ❤️ para o Sistema Pet ERP**  
Sprint 7 - Passo 1 | Janeiro 2026
