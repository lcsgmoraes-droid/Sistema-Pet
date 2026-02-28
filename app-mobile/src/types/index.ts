// =====================
// AUTENTICAÇÃO
// =====================

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface AuthResponse extends AuthTokens {
  user: EcommerceUser;
}

export interface EcommerceUser {
  id: number;
  email: string;
  nome: string | null;
  telefone?: string | null;
  cpf?: string | null;
  pontos?: number;
  // endereço
  cep?: string | null;
  endereco?: string | null;
  numero?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  estado?: string | null;
}

// =====================
// PETS
// =====================

export interface Pet {
  id: number;
  codigo: string;
  nome: string;
  especie: string; // cão, gato, coelho, etc.
  raca?: string | null;
  sexo?: string | null; // macho, fêmea
  castrado: boolean;
  data_nascimento?: string | null; // ISO date
  idade_aproximada?: number | null; // meses
  peso?: number | null; // kg
  cor?: string | null;
  porte?: string | null; // mini, pequeno, médio, grande, gigante
  alergias?: string | null;
  observacoes?: string | null;
  foto_url?: string | null;
}

export interface PetFormData {
  nome: string;
  especie: string;
  raca?: string;
  sexo?: string;
  castrado?: boolean;
  data_nascimento?: string;
  peso?: number;
  porte?: string;
  cor?: string;
  alergias?: string;
  observacoes?: string;
}

// =====================
// PRODUTOS
// =====================

export interface Produto {
  id: number;
  nome: string;
  preco: number;
  preco_promocional?: number | null;
  promocao_ativa?: boolean;
  descricao?: string | null;
  foto_url?: string | null;
  estoque?: number;
  estoque_ecommerce?: number | null;   // estoque específico do e-commerce
  codigo?: string | null;              // SKU / código interno
  codigo_barras?: string | null;
  unidade?: string;
  categoria_nome?: string | null;
  marca_nome?: string | null;
  peso_embalagem_kg?: number | null;   // para calculadora de ração
}

// =====================
// CARRINHO & PEDIDO
// =====================

export interface ItemCarrinho {
  produto_id: number;
  nome: string;
  preco_unitario: number;
  quantidade: number;
  subtotal: number;
  foto_url?: string | null;
}

export interface Pedido {
  pedido_id: string;
  status: string;
  total: number;
  tipo_retirada?: string | null;
  palavra_chave_retirada?: string | null;
  endereco_entrega?: string | null;
  created_at?: string | null;
  itens: {
    produto_id: number;
    nome: string;
    quantidade: number;
    preco_unitario: number;
    subtotal: number;
  }[];
}

// =====================
// CALCULADORA DE RAÇÃO
// =====================

export interface CalculadoraInput {
  peso_pet_kg: number;
  idade_meses?: number;
  nivel_atividade: 'baixo' | 'normal' | 'alto';
  produto_id?: number;
  peso_embalagem_kg?: number;
  preco?: number;
}

export interface CalculadoraResultado {
  quantidade_diaria_g: number;
  quantidade_diaria_display: string;
  duracao_dias: number;
  custo_dia: number;
  custo_mes: number;
  alerta?: string | null;
  produto_nome?: string | null;
  preco?: number | null;
}

// =====================
// NAVEGAÇÃO
// =====================

export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  Main: undefined;
};

export type MainTabParamList = {
  Home: undefined;
  Loja: undefined;
  Favoritos: undefined;
  Pets: undefined;
  Pedidos: undefined;
  Perfil: undefined;
};

export type LojaStackParamList = {
  Catalogo: undefined;
  DetalhesProduto: { produto: Produto };
  Carrinho: undefined;
  BarcodeScanner: undefined;
  CheckoutSucesso: { pedido: Pedido };
};

export type PetsStackParamList = {
  ListaPets: undefined;
  FormPet: { pet?: Pet };
  CalculadoraRacao: { pet?: Pet };
};
