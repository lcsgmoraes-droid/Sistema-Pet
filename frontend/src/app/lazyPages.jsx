import { lazy } from "react";

export const Login = lazy(() => import("../pages/Login"));
export const ForgotPassword = lazy(() => import("../pages/ForgotPassword"));
export const Register = lazy(() => import("../pages/Register"));
export const EmailVerification = lazy(() => import("../pages/EmailVerification"));
export const LegalPage = lazy(() => import("../pages/LegalPage"));
export const LandingPage = lazy(() => import("../pages/LandingPage"));
export const Planos = lazy(() => import("../pages/Planos"));
export const MeuPlano = lazy(() => import("../pages/MeuPlano"));
export const AppPublicEntry = lazy(() => import("../pages/AppPublicEntry"));
export const AppPaymentReturn = lazy(() => import("../pages/AppPaymentReturn"));

export const preloadPessoas = () => import("../pages/ClientesNovo");
export const Pessoas = lazy(preloadPessoas);

export const preloadProdutos = () => import("../pages/Produtos");
export const Produtos = lazy(preloadProdutos);
export const ProdutosNovo = lazy(() => import("../pages/ProdutosNovo"));
export const ProdutosRelatorio = lazy(() => import("../pages/ProdutosRelatorio"));
export const ProdutosValorizacaoEstoque = lazy(() => import("../pages/ProdutosValorizacaoEstoque"));
export const ProdutosBalanco = lazy(() => import("../pages/ProdutosBalanco"));
export const AlertasEstoque = lazy(() => import("../pages/AlertasEstoque"));
export const EstoqueFullNF = lazy(() => import("../pages/EstoqueFullNF"));
export const EstoqueTransferenciaParceiro = lazy(
  () => import("../pages/EstoqueTransferenciaParceiro"),
);
export const preloadLembretes = () => import("../pages/Lembretes");
export const Lembretes = lazy(preloadLembretes);
export const CalculadoraRacao = lazy(() => import("../pages/CalculadoraRacao"));

export const GerenciamentoPets = lazy(() => import("../pages/GerenciamentoPets"));
export const PetDetalhes = lazy(() => import("../pages/PetDetalhes"));
export const PetForm = lazy(() => import("../pages/PetForm"));

export const VetDashboard = lazy(() => import("../pages/veterinario/VetDashboard"));
export const VetAgenda = lazy(() => import("../pages/veterinario/VetAgenda"));
export const VetConsultas = lazy(() => import("../pages/veterinario/VetConsultas"));
export const VetConsultaForm = lazy(() => import("../pages/veterinario/VetConsultaForm"));
export const VetVacinas = lazy(() => import("../pages/veterinario/VetVacinas"));
export const VetInternacoes = lazy(() => import("../pages/veterinario/VetInternacoes"));
export const VetCalculadoraDoses = lazy(() => import("../pages/veterinario/VetCalculadoraDoses"));
export const VetCatalogo = lazy(() => import("../pages/veterinario/VetCatalogo"));
export const VetConfiguracoes = lazy(() => import("../pages/veterinario/VetConfiguracoes"));
export const VetRepasse = lazy(() => import("../pages/veterinario/VetRepasse"));
export const VetExamesAnexados = lazy(() => import("../pages/veterinario/VetExamesAnexados"));
export const VetAssistenteIA = lazy(() => import("../pages/veterinario/VetAssistenteIA"));
export const BanhoTosaPage = lazy(() => import("../pages/banhoTosa/BanhoTosaPage"));

export const preloadPDV = () => import("../pages/PDV");
export const PDV = lazy(preloadPDV);
export const MeusCaixas = lazy(() => import("../pages/MeusCaixas"));
export const NFEntrada = lazy(() => import("../pages/NFEntrada"));
export const CentralNFSaida = lazy(() => import("../pages/CentralNFSaida"));

export const ClienteTimelinePage = lazy(() => import("../pages/ClienteTimelinePage"));

export const MovimentacoesProduto = lazy(() => import("../components/MovimentacoesProduto"));
export const EstoqueBling = lazy(() => import("../components/EstoqueBling"));
export const PedidosBling = lazy(() => import("../pages/PedidosBling"));
export const BlingFlowMonitor = lazy(() => import("../pages/BlingFlowMonitor"));
export const PedidosCompra = lazy(() => import("../components/PedidosCompra"));
export const EntradaXML = lazy(() => import("../components/EntradaXML"));
export const ComprasPendencias = lazy(() => import("../components/ComprasPendencias"));

export const preloadDashboardFinanceiro = () => import("../pages/DashboardFinanceiro");
export const DashboardFinanceiro = lazy(preloadDashboardFinanceiro);
export const BancosFinanceiro = lazy(() => import("../pages/BancosFinanceiro"));
export const Imobilizado = lazy(() => import("../pages/Imobilizado"));
export const ValorEmpresa = lazy(() => import("../pages/ValorEmpresa"));
export const ContasBancarias = lazy(() => import("../components/ContasBancarias"));
export const ContasPagar = lazy(() => import("../components/ContasPagar"));
export const ContasReceber = lazy(() => import("../components/ContasReceber"));
export const PontoEquilibrio = lazy(() => import("../pages/PontoEquilibrio"));
export const ConciliacaoCartoesTabs = lazy(() => import("../pages/ConciliacaoCartoesTabs"));
export const HistoricoConciliacoes = lazy(() => import("../pages/HistoricoConciliacoes"));
export const ConciliacaoBancaria = lazy(() => import("../pages/ConciliacaoBancaria"));
export const FormasPagamento = lazy(() => import("../components/FormasPagamento"));
export const OperadorasCartao = lazy(() => import("../pages/OperadorasCartao"));
export const FluxoCaixa = lazy(() => import("../components/FluxoCaixa"));
export const RelatorioVendas = lazy(() => import("../components/RelatorioVendas"));
export const VendasFinanceiro = lazy(() => import("../components/VendasFinanceiro"));
export const VendasCanaisPreview = import.meta.env.DEV
  ? lazy(() => import("../components/financeiro/VendasCanaisPreview"))
  : null;
export const AlertasRacao = lazy(() => import("../components/AlertasRacao"));
export const OpcoesRacao = lazy(() => import("../components/OpcoesRacao"));
export const DRE = lazy(() => import("../components/DRE"));

export const IAFluxoCaixa = lazy(() => import("../pages/IAFluxoCaixa"));
export const ChatIA = lazy(() => import("../pages/IA/ChatIA"));
export const WhatsAppDashboard = lazy(async () => {
  const module = await import("../pages/WhatsAppDashboard/index.tsx");
  return { default: module.WhatsAppDashboard };
});

export const Comissoes = lazy(() => import("../pages/Comissoes"));
export const ComissoesListagem = lazy(() => import("../pages/comissoes/ComissoesListagem"));
export const ComissoesAbertas = lazy(() => import("../pages/comissoes/ComissoesAbertas"));
export const ConferenciaAvancada = lazy(() => import("../pages/comissoes/ConferenciaAvancada"));
export const ComissoesHistoricoFechamentos = lazy(
  () => import("../pages/comissoes/ComissoesHistoricoFechamentos"),
);
export const ComissoesFechamentoDetalhe = lazy(
  () => import("../pages/comissoes/ComissoesFechamentoDetalhe"),
);
export const RelatoriosComissoes = lazy(() => import("../pages/comissoes/RelatoriosComissoes"));

export const Subcategorias = lazy(() => import("../pages/Subcategorias"));
export const Categorias = lazy(() => import("../pages/Cadastros/Categorias"));
export const Departamentos = lazy(() => import("../pages/Cadastros/Departamentos"));
export const Marcas = lazy(() => import("../pages/Cadastros/Marcas"));
export const TipoDespesa = lazy(() => import("../pages/Cadastros/TipoDespesa"));
export const CategoriasFinanceiras = lazy(() => import("../pages/CategoriasFinanceiras"));
export const EspeciesRacas = lazy(() => import("../pages/EspeciesRacas"));
export const ClienteFinanceiro = lazy(() => import("../pages/ClienteFinanceiro"));
export const UsuariosPage = lazy(() => import("../pages/UsuariosPage.jsx"));
export const RolesPage = lazy(() => import("../pages/RolesPage.jsx"));
export const LGPDOperacional = lazy(() => import("../pages/LGPDOperacional.jsx"));
export const OpsDashboard = lazy(() => import("../pages/OpsDashboard.jsx"));
export const OpsIncidentes = lazy(() => import("../pages/OpsIncidentes.jsx"));
export const OpsTenants = lazy(() => import("../pages/OpsTenants.jsx"));
export const Observabilidade = lazy(() => import("../pages/Observabilidade.jsx"));
export const Configuracoes = lazy(() => import("../pages/Configuracoes"));
export const ConfiguracaoFiscalEmpresa = lazy(
  () => import("../pages/configuracoes/ConfiguracaoFiscalEmpresa"),
);
export const EntregasConfig = lazy(() => import("../pages/configuracoes/EntregasConfig"));
export const CustosMoto = lazy(() => import("../pages/configuracoes/CustosMoto"));
export const ConfiguracaoEstoque = lazy(() => import("../pages/configuracoes/ConfiguracaoEstoque"));
export const ConfiguracaoGeralNegocio = lazy(
  () => import("../pages/configuracoes/ConfiguracaoGeralNegocio"),
);
export const Integracoes = lazy(() => import("../pages/configuracoes/Integracoes"));
export const AuditoriaMensal = lazy(() => import("../pages/AuditoriaMensal"));
export const ProjecaoCaixa = lazy(() => import("../pages/ProjecaoCaixa"));
export const SimulacaoContratacao = lazy(() => import("../pages/SimulacaoContratacao"));
export const Cargos = lazy(() => import("../pages/Cadastros/Cargos"));
export const Funcionarios = lazy(() => import("../pages/RH/Funcionarios"));
export const EntregasAbertas = lazy(() => import("../pages/entregas/EntregasAbertas"));
export const RotasEntrega = lazy(() => import("../pages/entregas/RotasEntrega"));
export const RastreioPublico = lazy(() => import("../pages/entregas/RastreioPublico"));
export const HistoricoEntregas = lazy(() => import("../pages/entregas/HistoricoEntregas"));
export const DashEntregasFinanceiro = lazy(
  () => import("../pages/entregas/DashEntregasFinanceiro"),
);
export const EcommerceMVP = lazy(() => import("../pages/ecommerce/EcommerceMVP"));
export const EcommerceAparencia = lazy(() => import("../pages/ecommerce/EcommerceAparencia"));
export const EcommerceConfig = lazy(() => import("../pages/ecommerce/EcommerceConfig"));
export const EcommerceAnalytics = lazy(() => import("../pages/ecommerce/EcommerceAnalytics"));
export const Campanhas = lazy(() => import("../pages/Campanhas"));
export const CanalDescontos = lazy(() => import("../pages/CanalDescontos"));
export const Ajuda = lazy(() => import("../pages/Ajuda"));
