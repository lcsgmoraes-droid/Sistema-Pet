/**
 * Definição das colunas disponíveis na listagem de produtos
 * 
 * IMPORTANTE:
 * - Colunas 'locked' são sempre visíveis e não podem ser ocultadas
 * - Novas colunas adicionadas aqui aparecem automaticamente para todos os usuários
 * - O hook useColumnPreferences faz merge com preferências salvas
 */

export const COLUNAS_DISPONIVEIS = [
  // ====== ESSENCIAIS (sempre visíveis, locked) ======
  {
    id: 'select',
    label: 'Seleção',
    locked: true,
    order: 0,
    visible: true,
    width: '50px',
  },
  {
    id: 'imagem',
    label: 'Imagem',
    locked: true,
    order: 1,
    visible: true,
    width: '80px',
  },
  {
    id: 'descricao',
    label: 'Descrição',
    locked: true,
    order: 2,
    visible: true,
    width: 'auto',
  },
  
  // ====== OPERACIONAIS (visíveis por padrão, customizáveis) ======
  {
    id: 'codigo',
    label: 'Código',
    locked: false,
    order: 3,
    visible: true,
    width: '120px',
  },
  {
    id: 'custo',
    label: 'Custo',
    locked: false,
    order: 4,
    visible: true,
    width: '100px',
  },
  {
    id: 'pv',
    label: 'PV',
    locked: false,
    order: 5,
    visible: true,
    width: '100px',
  },
  {
    id: 'estoque',
    label: 'Estoque',
    locked: false,
    order: 6,
    visible: true,
    width: '80px',
  },
  {
    id: 'validade',
    label: 'Validade',
    locked: false,
    order: 7,
    visible: true,
    width: '100px',
  },
  {
    id: 'unidade',
    label: 'Unidade',
    locked: false,
    order: 8,
    visible: true,
    width: '80px',
  },
  
  // ====== ADICIONAIS (ocultas por padrão) ======
  {
    id: 'codigo_barras',
    label: 'Cód. Barras',
    locked: false,
    order: 9,
    visible: false,
    width: '130px',
  },
  {
    id: 'categoria',
    label: 'Categoria',
    locked: false,
    order: 10,
    visible: false,
    width: '150px',
  },
  {
    id: 'marca',
    label: 'Marca',
    locked: false,
    order: 11,
    visible: false,
    width: '120px',
  },
  {
    id: 'departamento',
    label: 'Departamento',
    locked: false,
    order: 12,
    visible: false,
    width: '120px',
  },
  {
    id: 'margem',
    label: 'Margem %',
    locked: false,
    order: 13,
    visible: false,
    width: '90px',
  },
  {
    id: 'estoque_min',
    label: 'Estoque Mín.',
    locked: false,
    order: 14,
    visible: false,
    width: '100px',
  },
  {
    id: 'fornecedor',
    label: 'Fornecedor',
    locked: false,
    order: 15,
    visible: false,
    width: '150px',
  },
  
  // ====== AÇÕES (sempre visíveis, locked, última coluna) ======
  {
    id: 'acoes',
    label: 'Ações',
    locked: true,
    order: 999,
    visible: true,
    width: '120px',
  },
];
