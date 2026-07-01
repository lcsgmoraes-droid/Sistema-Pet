// =====================
// AUTENTICAÇÃO
// =====================

export interface AuthTokens {
  access_token?: string | null;
  token_type: string;
}

export interface AuthResponse extends AuthTokens {
  user: EcommerceUser;
  requires_email_verification?: boolean;
  email_verification_sent?: boolean;
}

export type AppProfileType = "cliente" | "entregador" | "veterinario" | "funcionario";

export interface AppAccessProfile {
  type: AppProfileType;
  label: string;
  cliente_id?: number | null;
  nome?: string | null;
  source?: string | null;
}

export interface EcommerceDeliveryAddress {
  entrega_nome?: string | null;
  entrega_cep?: string | null;
  entrega_endereco?: string | null;
  entrega_numero?: string | null;
  entrega_complemento?: string | null;
  entrega_bairro?: string | null;
  entrega_cidade?: string | null;
  entrega_estado?: string | null;
}

export interface EcommerceUser {
  id: number;
  email: string;
  email_verified?: boolean;
  nome: string | null;
  telefone?: string | null;
  cpf?: string | null;
  pontos?: number;
  // endereço
  cep?: string | null;
  endereco?: string | null;
  numero?: string | null;
  complemento?: string | null;
  bairro?: string | null;
  cidade?: string | null;
  estado?: string | null;
  endereco_entrega?: string | null;
  usar_endereco_entrega_diferente?: boolean | null;
  endereco_entrega_detalhado?: EcommerceDeliveryAddress | null;
  // perfil entregador
  is_entregador?: boolean;
  funcionario_id?: number | null;
  // perfil operacional funcionario
  is_funcionario?: boolean;
  // perfil operacional veterinario
  is_veterinario?: boolean;
  veterinario_id?: number | null;
  perfil_operacional?: AppProfileType;
  selected_profile?: AppProfileType;
  available_profiles?: AppAccessProfile[];
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
  veterinario_id?: number | null;
  veterinario_nome?: string | null;
  assinatura_digital?: string | null;
  assinatura_valida?: boolean | null;
  hash_validacao?: string | null;
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

export interface BanhoTosaStatusItem {
  tipo: "agendamento" | "atendimento";
  atendimento_id?: number | null;
  agendamento_id?: number | null;
  pet_id: number;
  pet_nome?: string | null;
  status: string;
  status_label: string;
  progresso_percentual: number;
  etapa_atual?: string | null;
  data_hora_inicio?: string | null;
  data_hora_fim_prevista?: string | null;
  checkin_em?: string | null;
  inicio_em?: string | null;
  fim_em?: string | null;
  entregue_em?: string | null;
  valor_previsto?: number | null;
  servicos: { nome: string; quantidade: number }[];
  pode_avaliar: boolean;
  avaliacao?: {
    id: number;
    nota_nps: number;
    nota_servico?: number | null;
    comentario?: string | null;
    origem?: string | null;
    created_at?: string | null;
  } | null;
}

export interface BanhoTosaStatusResponse {
  total: number;
  itens: BanhoTosaStatusItem[];
}

export interface BanhoTosaServicoOpcao {
  id: number;
  nome: string;
  duracao_padrao_minutos?: number | null;
  preco_base?: number | null;
}

export interface BanhoTosaCalendarioSlot {
  horario_inicio: string;
  horario_fim: string;
  status: "disponivel" | "ocupado";
  vagas: number;
}

export interface BanhoTosaCalendarioDia {
  data: string;
  funciona: boolean;
  slots: BanhoTosaCalendarioSlot[];
}

export interface BanhoTosaCalendarioResponse {
  visivel: boolean;
  whatsapp?: string | null;
  servicos: BanhoTosaServicoOpcao[];
  dias: BanhoTosaCalendarioDia[];
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
  preco_original?: number | null;
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

export interface FuncionarioProdutoEstoque {
  id: number;
  nome: string;
  codigo?: string | null;
  codigo_barras?: string | null;
  gtin_ean?: string | null;
  unidade?: string;
  preco_venda: number;
  preco_custo: number;
  estoque_atual: number;
  imagem_url?: string | null;
  is_parent?: boolean;
  tipo_produto?: string | null;
  tipo_kit?: string | null;
  permite_balanco?: boolean;
  aviso?: string | null;
}

export interface FuncionarioBalancoPayload {
  produto_id: number;
  saldo_final: number;
  numero_lote?: string | null;
  data_validade?: string | null;
  observacao?: string | null;
}

export interface FuncionarioBalancoResponse {
  status: string;
  produto: FuncionarioProdutoEstoque;
  estoque_anterior: number;
  estoque_novo: number;
  diferenca: number;
  tipo_movimentacao?: "entrada" | "saida" | null;
  quantidade_movimentada: number;
  movimentacao_id?: number | null;
  mensagem: string;
}

export interface FuncionarioContagemFornecedor {
  id: number;
  nome: string;
  documento?: string | null;
}

export interface FuncionarioContagemItemPayload {
  produto_id: number;
  quantidade: number;
  observacao?: string | null;
}

export interface FuncionarioContagemPayload {
  titulo?: string | null;
  fornecedor_id?: number | null;
  observacao?: string | null;
  itens: FuncionarioContagemItemPayload[];
}

export interface FuncionarioContagemItem {
  id: number;
  produto_id: number;
  codigo?: string | null;
  codigo_barras?: string | null;
  gtin_ean?: string | null;
  nome: string;
  unidade: string;
  quantidade: number;
  preco_custo: number;
  preco_venda: number;
  observacao?: string | null;
}

export interface FuncionarioContagemResumo {
  id: number;
  titulo: string;
  status: string;
  fornecedor_id?: number | null;
  fornecedor_nome?: string | null;
  observacao?: string | null;
  total_itens: number;
  quantidade_total: number;
  created_at: string;
}

export interface FuncionarioContagem extends FuncionarioContagemResumo {
  itens: FuncionarioContagemItem[];
}

export interface FuncionarioContagemArquivo {
  filename: string;
  mime_type: string;
  base64: string;
}

export interface FuncionarioContagemExportOptions {
  mostrar_custo?: boolean;
  mostrar_venda?: boolean;
}

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

export interface FuncionarioPdvCliente {
  id: number;
  codigo?: string | null;
  nome: string;
  telefone?: string | null;
  celular?: string | null;
  documento?: string | null;
  tipo_cadastro?: string | null;
  email?: string | null;
  endereco?: string | null;
  credito?: number;
  fidelidade?: Record<string, any> | null;
  cupons_disponiveis?: any[];
}

export interface FuncionarioPdvCaixa {
  aberto: boolean;
  caixa_id?: number | null;
  numero_caixa?: number | null;
  mensagem: string;
}

export interface FuncionarioPdvItemPayload {
  produto_id: number;
  quantidade: number;
  preco_unitario: number;
}

export type FuncionarioPdvFormaPagamento = "dinheiro" | "pix" | "credito" | "debito";

export interface FuncionarioPdvFormaPagamentoOpcao {
  id: number;
  nome: string;
  tipo: string;
  key: FuncionarioPdvFormaPagamento;
  taxa_percentual: number;
  permite_parcelamento: boolean;
  numero_parcelas: number;
  max_parcelas: number;
  parcelas_maximas: number;
  operadora?: string | null;
  requer_nsu: boolean;
  tipo_cartao?: string | null;
  bandeira?: string | null;
  split_parcelas: boolean;
}

export interface FuncionarioPdvPagamentoPayload {
  forma_pagamento: FuncionarioPdvFormaPagamento;
  valor: number;
  valor_recebido?: number | null;
  troco?: number | null;
  numero_parcelas: number;
  forma_pagamento_id?: number | null;
  bandeira?: string | null;
  operadora?: string | null;
  nsu_cartao?: string | null;
}

export interface FuncionarioPdvCupomDisponivel {
  code: string;
  coupon_type: string;
  discount_value?: number | null;
  discount_percent?: number | null;
  discount_applied: number;
  min_purchase_value?: number | null;
  valid_until?: string | null;
}

export interface FuncionarioPdvBeneficioGerado {
  tipo: string;
  titulo: string;
  valor?: number | null;
  percentual?: number | null;
  quantidade?: number | null;
  descricao?: string | null;
}

export interface FuncionarioPdvBeneficiosPreviewPayload {
  cliente_id?: number | null;
  itens: FuncionarioPdvItemPayload[];
  cupom_codigo?: string | null;
  cashback_valor?: number | null;
}

export interface FuncionarioPdvBeneficiosPreview {
  subtotal: number;
  desconto_cupom: number;
  cupom_code?: string | null;
  cashback_disponivel: number;
  cashback_valor: number;
  total_venda: number;
  valor_pagamento: number;
  cupons_disponiveis: FuncionarioPdvCupomDisponivel[];
  beneficios_gerados: FuncionarioPdvBeneficioGerado[];
  mensagens: string[];
}

export interface FuncionarioPdvFinalizarPayload {
  cliente_id?: number | null;
  itens: FuncionarioPdvItemPayload[];
  pagamento: FuncionarioPdvPagamentoPayload;
  observacoes?: string | null;
  cupom_codigo?: string | null;
  desconto_cupom?: number | null;
  cashback_valor?: number | null;
}

export interface FuncionarioPdvSalvarPayload {
  cliente_id?: number | null;
  itens: FuncionarioPdvItemPayload[];
  observacoes?: string | null;
  cupom_codigo?: string | null;
  desconto_cupom?: number | null;
  cashback_valor?: number | null;
}

export interface FuncionarioPdvFinalizarResponse {
  status: string;
  venda_id: number;
  numero_venda: string;
  total: number;
  total_pago: number;
  forma_pagamento: string;
  mensagem: string;
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
  historico_id?: string | null;
  origem_tipo?: string | null;
  pedido_id?: string | null;
  numero?: string | null;
  status: string;
  total: number;
  origem?: string | null;
  canal?: string | null;
  canal_label?: string | null;
  venda_id?: number | null;
  status_entrega?: string | null;
  retirado_por?: string | null;
  tem_entrega?: boolean | null;
  tipo_retirada?: string | null;
  is_drive?: boolean | null;
  palavra_chave_retirada?: string | null;
  endereco_entrega?: string | null;
  payment_provider?: string | null;
  payment_preference_id?: string | null;
  payment_url?: string | null;
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
  Beneficios: undefined;
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
  Veterinario: undefined;
  BanhoTosa: undefined;
};
