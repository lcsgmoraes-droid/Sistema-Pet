import artigosPorModulo from "./centralAjudaArtigos.json";
import {
  FiBarChart2,
  FiBookOpen,
  FiCalendar,
  FiCpu,
  FiPackage,
  FiSettings,
  FiTruck,
  FiUsers,
} from "react-icons/fi";

// Categorias estáticas da Central de Ajuda; a ordem é definida pelo catálogo principal.
export const AJUDA_DASHBOARD = {
  modulo: "dashboard",
  label: "Dashboard",
  icone: FiBarChart2,
  cor: "indigo",
  artigos: artigosPorModulo["dashboard"],
};

export const AJUDA_PESSOAS = {
  modulo: "pessoas",
  label: "Pessoas (Clientes, Fornecedores, Veterinários)",
  icone: FiUsers,
  cor: "blue",
  artigos: artigosPorModulo["pessoas"],
};

export const AJUDA_PETS = {
  modulo: "pets",
  label: "Pets",
  icone: FiBookOpen,
  cor: "green",
  artigos: artigosPorModulo["pets"],
};

export const AJUDA_PRODUTOS = {
  modulo: "produtos",
  label: "Produtos e Estoque",
  icone: FiPackage,
  cor: "orange",
  artigos: artigosPorModulo["produtos"],
};

export const AJUDA_LEMBRETES = {
  modulo: "lembretes",
  label: "Lembretes e Agendamentos",
  icone: FiCalendar,
  cor: "purple",
  artigos: artigosPorModulo["lembretes"],
};

export const AJUDA_CALCULADORA = {
  modulo: "calculadora",
  label: "Calculadora de Ração",
  icone: FiCpu,
  cor: "teal",
  artigos: artigosPorModulo["calculadora"],
};

export const AJUDA_NFE = {
  modulo: "nfe",
  label: "Notas Fiscais",
  icone: FiBookOpen,
  cor: "gray",
  artigos: artigosPorModulo["nfe"],
};

export const AJUDA_CONFIGURACOES = {
  modulo: "configuracoes",
  label: "Configurações",
  icone: FiSettings,
  cor: "gray",
  artigos: artigosPorModulo["configuracoes"],
};

export const AJUDA_COMPRAS = {
  modulo: "compras",
  label: "Compras e Pedidos",
  icone: FiTruck,
  cor: "blue",
  artigos: artigosPorModulo["compras"],
};

export const AJUDA_IA = {
  modulo: "ia",
  label: "Inteligência Artificial",
  icone: FiCpu,
  cor: "purple",
  artigos: artigosPorModulo["ia"],
};
