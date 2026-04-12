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
  // perfil entregador
  is_entregador?: boolean;
  funcionario_id?: number | null;
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
  alergias_lista?: string[];
  observacoes?: string | null;
  restricoes_alimentares_lista?: string[];
  condicoes_cronicas_lista?: string[];
  medicamentos_continuos_lista?: string[];
  tipo_sanguineo?: string | null;
  foto_url?: string | null;
}

export interface PetAlerta {
  tipo: string;
  nivel: string;
  mensagem: string;
}

export interface VacinaCarteirinha {
  id: number;
  nome: string;
  data_aplicacao?: string | null;
  data_proxima_dose?: string | null;
  numero_dose?: number | null;
  lote?: string | null;
  fabricante?: string | null;
  status?: string | null;
}

export interface PetCarteirinha {
  pet: Pet;
  alertas: PetAlerta[];
  status_vacinal: {
    carteira: VacinaCarteirinha[];
    pendentes: { nome: string; motivo?: string | null }[];
    vencidas: { nome: string; data_proxima_dose?: string | null; dias_atraso?: number | null }[];
    resumo: {
      total_aplicadas: number;
      total_pendentes: number;
      total_vencidas: number;
    };
  };
  consultas: {
    id: number;
    data?: string | null;
    tipo?: string | null;
    status?: string | null;
    diagnostico?: string | null;
    observacoes_tutor?: string | null;
  }[];
  exames: {
    id: number;
    nome: string;
    tipo?: string | null;
    status?: string | null;
    data_resultado?: string | null;
    interpretacao_ia_resumo?: string | null;
    arquivo_url?: string | null;
  }[];
}

export interface PushStatus {
  token_registrado: boolean;
  push_token_preview?: string | null;
  pendencias: { id: number; assunto?: string | null; mensagem?: string | null; scheduled_at?: string | null }[];
  proximos_agendamentos: { id: number; pet_id: number; data_hora?: string | null; tipo?: string | null; status?: string | null }[];
  observacao?: string | null;
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

export type VetFocusSection = "vacinas" | "exames" | "consultas";

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
  is_drive?: boolean | null;
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
  ForgotPassword: undefined;
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
  ListaPets: { focusSection?: VetFocusSection } | undefined;
  FormPet: { pet?: Pet };
  CalculadoraRacao: { pet?: Pet };
  DetalhePet: { pet: Pet; focusSection?: VetFocusSection };
};
