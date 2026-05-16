import { Suspense, lazy, useEffect } from "react";
import { Toaster } from "react-hot-toast";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import ModuloBloqueado from "./components/ModuloBloqueado";
import OpsLayout from "./components/OpsLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./contexts/AuthContext";
import { ModulosProvider } from "./contexts/ModulosContext";
import { isMobileViewport, isVeterinarioProfile } from "./utils/veterinarioPerfil";
const Login = lazy(() => import("./pages/Login"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const Register = lazy(() => import("./pages/Register"));
const EmailVerification = lazy(() => import("./pages/EmailVerification"));
const LegalPage = lazy(() => import("./pages/LegalPage"));
const LandingPage = lazy(() => import("./pages/LandingPage"));
const Planos = lazy(() => import("./pages/Planos"));
const AppPublicEntry = lazy(() => import("./pages/AppPublicEntry"));
const preloadPessoas = () => import("./pages/ClientesNovo");
const Pessoas = lazy(preloadPessoas);

// ========================================
// 🆕 SPRINT 7 - NOVA INTERFACE DE PRODUTOS (TYPESCRIPT) - DESATIVADA
// ========================================
// import ProdutosPage from './pages/produtos/ProdutosPage';
// import ProdutoForm from './pages/produtos/components/ProdutoForm';
// import ProdutoEditPage from './pages/produtos/ProdutoEditPage';

// ========================================
// 📦 INTERFACE OFICIAL DE PRODUTOS (JSX) - ATIVA
// ========================================
const preloadProdutos = () => import("./pages/Produtos");
const Produtos = lazy(preloadProdutos);
const ProdutosNovo = lazy(() => import("./pages/ProdutosNovo"));
const ProdutosRelatorio = lazy(() => import("./pages/ProdutosRelatorio"));
const ProdutosValorizacaoEstoque = lazy(
  () => import("./pages/ProdutosValorizacaoEstoque"),
);
const ProdutosBalanco = lazy(() => import("./pages/ProdutosBalanco"));
const AlertasEstoque = lazy(() => import("./pages/AlertasEstoque"));
const EstoqueFullNF = lazy(() => import("./pages/EstoqueFullNF"));
const EstoqueTransferenciaParceiro = lazy(
  () => import("./pages/EstoqueTransferenciaParceiro"),
);
const SEFAZImportacao = lazy(() => import("./pages/SEFAZImportacao"));
const preloadLembretes = () => import("./pages/Lembretes");
const Lembretes = lazy(preloadLembretes);
const CalculadoraRacao = lazy(() => import("./pages/CalculadoraRacao"));

// Componentes de Pets
const GerenciamentoPets = lazy(() => import("./pages/GerenciamentoPets"));
const PetDetalhes = lazy(() => import("./pages/PetDetalhes"));
const PetForm = lazy(() => import("./pages/PetForm"));

// ========================================
// 🩺 MÓDULO VETERINÁRIO
// ========================================
const VetDashboard = lazy(() => import("./pages/veterinario/VetDashboard"));
const VetAgenda = lazy(() => import("./pages/veterinario/VetAgenda"));
const VetConsultas = lazy(() => import("./pages/veterinario/VetConsultas"));
const VetConsultaForm = lazy(() => import("./pages/veterinario/VetConsultaForm"));
const VetVacinas = lazy(() => import("./pages/veterinario/VetVacinas"));
const VetInternacoes = lazy(() => import("./pages/veterinario/VetInternacoes"));
const VetCalculadoraDoses = lazy(() => import("./pages/veterinario/VetCalculadoraDoses"));
const VetCatalogo = lazy(() => import("./pages/veterinario/VetCatalogo"));
const VetConfiguracoes = lazy(() => import("./pages/veterinario/VetConfiguracoes"));
const VetRepasse = lazy(() => import("./pages/veterinario/VetRepasse"));
const VetExamesAnexados = lazy(() => import("./pages/veterinario/VetExamesAnexados"));
const VetAssistenteIA = lazy(() => import("./pages/veterinario/VetAssistenteIA"));
const BanhoTosaPage = lazy(() => import("./pages/banhoTosa/BanhoTosaPage"));

const preloadPDV = () => import("./pages/PDV");
const PDV = lazy(preloadPDV);
const MeusCaixas = lazy(() => import("./pages/MeusCaixas"));
const NotasFiscais = lazy(() => import("./pages/NotasFiscais"));
const NFEntrada = lazy(() => import("./pages/NFEntrada"));
const NFSaida = lazy(() => import("./pages/NFSaida"));
const CentralNFSaida = lazy(() => import("./pages/CentralNFSaida"));

// Timeline de Cliente
const ClienteTimelinePage = lazy(() => import("./pages/ClienteTimelinePage"));

// Componentes de Estoque/Compras
const MovimentacoesProduto = lazy(
  () => import("./components/MovimentacoesProduto"),
);
const EstoqueBling = lazy(() => import("./components/EstoqueBling"));
const PedidosBling = lazy(() => import("./pages/PedidosBling"));
const BlingFlowMonitor = lazy(() => import("./pages/BlingFlowMonitor"));
const PedidosCompra = lazy(() => import("./components/PedidosCompra"));
const EntradaXML = lazy(() => import("./components/EntradaXML"));
const ComprasPendencias = lazy(() => import("./components/ComprasPendencias"));

// Componentes Financeiros
const preloadDashboardFinanceiro = () => import("./pages/DashboardFinanceiro");
const DashboardFinanceiro = lazy(preloadDashboardFinanceiro);
const ContasBancarias = lazy(() => import("./components/ContasBancarias"));
const ContasPagar = lazy(() => import("./components/ContasPagar"));
const ContasReceber = lazy(() => import("./components/ContasReceber"));
const ConciliacaoCartoesTabs = lazy(
  () => import("./pages/ConciliacaoCartoesTabs"),
);
const HistoricoConciliacoes = lazy(
  () => import("./pages/HistoricoConciliacoes"),
);
const ConciliacaoBancaria = lazy(() => import("./pages/ConciliacaoBancaria"));
const FormasPagamento = lazy(() => import("./components/FormasPagamento"));
const OperadorasCartao = lazy(() => import("./pages/OperadorasCartao"));
const FluxoCaixa = lazy(() => import("./components/FluxoCaixa"));
const RelatorioVendas = lazy(() => import("./components/RelatorioVendas"));
const VendasFinanceiro = lazy(() => import("./components/VendasFinanceiro"));
const AlertasRacao = lazy(() => import("./components/AlertasRacao"));
const OpcoesRacao = lazy(() => import("./components/OpcoesRacao"));
const DRE = lazy(() => import("./components/DRE"));

// Componentes de IA
const IAFluxoCaixa = lazy(() => import("./pages/IAFluxoCaixa"));
const ChatIA = lazy(() => import("./pages/IA/ChatIA"));
const DREInteligente = lazy(() => import("./pages/IA/DREInteligente"));
const RotasInteligentes = lazy(() => import("./pages/RotasInteligentes"));
const WhatsAppDashboard = lazy(async () => {
  const module = await import("./pages/WhatsAppDashboard/index.tsx");
  return { default: module.WhatsAppDashboard };
});
const Comissoes = lazy(() => import("./pages/Comissoes"));
const ComissoesListagem = lazy(
  () => import("./pages/comissoes/ComissoesListagem"),
);
const ComissoesAbertas = lazy(
  () => import("./pages/comissoes/ComissoesAbertas"),
);
const ComissoesFechamentoFuncionario = lazy(
  () => import("./pages/comissoes/ComissoesFechamentoFuncionario"),
);
const ConferenciaAvancada = lazy(
  () => import("./pages/comissoes/ConferenciaAvancada"),
);
const ComissoesHistoricoFechamentos = lazy(
  () => import("./pages/comissoes/ComissoesHistoricoFechamentos"),
);
const ComissoesFechamentoDetalhe = lazy(
  () => import("./pages/comissoes/ComissoesFechamentoDetalhe"),
);
const RelatoriosComissoes = lazy(
  () => import("./pages/comissoes/RelatoriosComissoes"),
);
const Subcategorias = lazy(() => import("./pages/Subcategorias"));
const Categorias = lazy(() => import("./pages/Cadastros/Categorias"));
const Departamentos = lazy(() => import("./pages/Cadastros/Departamentos"));
const Marcas = lazy(() => import("./pages/Cadastros/Marcas"));
const TipoDespesa = lazy(() => import("./pages/Cadastros/TipoDespesa"));
const CategoriasFinanceiras = lazy(
  () => import("./pages/CategoriasFinanceiras"),
);
const EspeciesRacas = lazy(() => import("./pages/EspeciesRacas"));
const ClienteFinanceiro = lazy(() => import("./pages/ClienteFinanceiro"));
const DashboardGerencial = lazy(() => import("./pages/DashboardGerencial"));
const UsuariosPage = lazy(() => import("./pages/UsuariosPage.jsx"));
const RolesPage = lazy(() => import("./pages/RolesPage.jsx"));
const LGPDOperacional = lazy(() => import("./pages/LGPDOperacional.jsx"));
const OpsDashboard = lazy(() => import("./pages/OpsDashboard.jsx"));
const OpsIncidentes = lazy(() => import("./pages/OpsIncidentes.jsx"));
const Observabilidade = lazy(() => import("./pages/Observabilidade.jsx"));
const Configuracoes = lazy(() => import("./pages/Configuracoes"));
const ConfiguracaoFiscalEmpresa = lazy(
  () => import("./pages/configuracoes/ConfiguracaoFiscalEmpresa"),
);
const EntregasConfig = lazy(
  () => import("./pages/configuracoes/EntregasConfig"),
);
const CustosMoto = lazy(() => import("./pages/configuracoes/CustosMoto"));
const ConfiguracaoEstoque = lazy(
  () => import("./pages/configuracoes/ConfiguracaoEstoque"),
);
const ConfiguracaoGeralNegocio = lazy(
  () => import("./pages/configuracoes/ConfiguracaoGeralNegocio"),
);
const Integracoes = lazy(() => import("./pages/configuracoes/Integracoes"));
// import FechamentoSimples from './pages/FechamentoSimples'; // TODO: Criar arquivo
const AuditoriaMensal = lazy(() => import("./pages/AuditoriaMensal"));
const ProjecaoCaixa = lazy(() => import("./pages/ProjecaoCaixa"));
const SimulacaoContratacao = lazy(() => import("./pages/SimulacaoContratacao"));
const Cargos = lazy(() => import("./pages/Cadastros/Cargos"));
const Funcionarios = lazy(() => import("./pages/RH/Funcionarios"));
const EntregasAbertas = lazy(() => import("./pages/entregas/EntregasAbertas"));
const RotasEntrega = lazy(() => import("./pages/entregas/RotasEntrega"));
const RastreioPublico = lazy(() => import("./pages/entregas/RastreioPublico"));
const HistoricoEntregas = lazy(
  () => import("./pages/entregas/HistoricoEntregas"),
);
const DashEntregasFinanceiro = lazy(
  () => import("./pages/entregas/DashEntregasFinanceiro"),
);
const EcommerceMVP = lazy(() => import("./pages/ecommerce/EcommerceMVP"));
const EcommerceAparencia = lazy(
  () => import("./pages/ecommerce/EcommerceAparencia"),
);
const EcommerceConfig = lazy(() => import("./pages/ecommerce/EcommerceConfig"));
const EcommerceAnalytics = lazy(
  () => import("./pages/ecommerce/EcommerceAnalytics"),
);
const Campanhas = lazy(() => import("./pages/Campanhas"));
const CanalDescontos = lazy(() => import("./pages/CanalDescontos"));
const Ajuda = lazy(() => import("./pages/Ajuda"));

function AppRoutePreloader() {
  useEffect(() => {
    let cancelled = false;
    let idleId;
    let timerId;
    let delayedTimerId;

    const connection =
      navigator.connection ||
      navigator.mozConnection ||
      navigator.webkitConnection;

    const shouldSkipPreload =
      Boolean(connection?.saveData) ||
      (typeof connection?.effectiveType === "string" &&
        /(^|-)2g$/.test(connection.effectiveType));

    if (shouldSkipPreload) {
      return () => {};
    }

    const runPreload = () => {
      if (cancelled) {
        return;
      }

      preloadLembretes();
      preloadDashboardFinanceiro();
      preloadPessoas();
      preloadProdutos();

      delayedTimerId = window.setTimeout(() => {
        if (!cancelled) {
          preloadPDV();
        }
      }, 4500);
    };

    if (typeof window.requestIdleCallback === "function") {
      idleId = window.requestIdleCallback(runPreload, { timeout: 2200 });
    } else {
      timerId = window.setTimeout(runPreload, 1200);
    }

    return () => {
      cancelled = true;

      if (
        typeof window.cancelIdleCallback === "function" &&
        typeof idleId === "number"
      ) {
        window.cancelIdleCallback(idleId);
      }

      if (typeof timerId === "number") {
        window.clearTimeout(timerId);
      }

      if (typeof delayedTimerId === "number") {
        window.clearTimeout(delayedTimerId);
      }
    };
  }, []);

  return null;
}

function DefaultProtectedHomeRedirect() {
  const { user } = useAuth();
  const destino = isMobileViewport() && isVeterinarioProfile(user) ? "/veterinario/agenda" : "/lembretes";
  return <Navigate to={destino} replace />;
}

function ModuleGate({ modulo, children }) {
  return <ModuloBloqueado modulo={modulo}>{children}</ModuloBloqueado>;
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ModulosProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Toaster position="top-right" />
            <AppRoutePreloader />
            <Suspense
              fallback={
                <div className="p-4 text-sm text-gray-500">Carregando...</div>
              }
            >
              <Routes>
                {/* Rotas Públicas */}
                <Route path="/login" element={<Login />} />
                <Route path="/recuperar-senha" element={<ForgotPassword />} />
                <Route path="/register" element={<Register />} />
                <Route path="/verificar-email" element={<EmailVerification />} />
                <Route path="/termos" element={<LegalPage type="termos" />} />
                <Route path="/privacidade" element={<LegalPage type="privacidade" />} />
                <Route path="/landing" element={<LandingPage />} />
                <Route path="/planos" element={<Planos />} />
                <Route path="/rastreio/:token" element={<RastreioPublico />} />
                <Route path="/app" element={<AppPublicEntry />} />
                <Route path="/ecommerce" element={<EcommerceMVP />} />

                {/* Rota dinâmica do e-commerce (precisa ficar após as rotas fixas) */}
                <Route path="/:tenantId" element={<EcommerceMVP />} />

                {/* Central operacional MLProHub Ops */}
                <Route
                  path="/ops"
                  element={
                    <ProtectedRoute permission="usuarios.manage">
                      <OpsLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<OpsDashboard />} />
                  <Route path="incidentes" element={<OpsIncidentes />} />
                  <Route path="observabilidade" element={<Observabilidade />} />
                </Route>

                {/* Rotas Protegidas */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<DefaultProtectedHomeRedirect />} />
                  <Route
                    path="dashboard"
                    element={
                      <ProtectedRoute permission="relatorios.gerencial">
                        <DashboardFinanceiro />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="dashboard-gerencial"
                    element={
                      <ProtectedRoute permission="relatorios.gerencial">
                        <DashboardGerencial />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="clientes"
                    element={
                      <ProtectedRoute permission="clientes.visualizar">
                        <Pessoas />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="clientes/:clienteId/financeiro"
                    element={
                      <ProtectedRoute permission="clientes.visualizar">
                        <ClienteFinanceiro />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="clientes/:clienteId/timeline"
                    element={
                      <ProtectedRoute permission="clientes.visualizar">
                        <ClienteTimelinePage />
                      </ProtectedRoute>
                    }
                  />

                  {/* Rotas de Pets - Módulo Dedicado */}
                  <Route path="pets" element={<ProtectedRoute permission="clientes.visualizar"><GerenciamentoPets /></ProtectedRoute>} />
                  <Route path="pets/novo" element={<ProtectedRoute permission="clientes.visualizar"><PetForm /></ProtectedRoute>} />
                  <Route path="pets/:petId" element={<ProtectedRoute permission="clientes.visualizar"><PetDetalhes /></ProtectedRoute>} />
                  <Route path="pets/:petId/editar" element={<ProtectedRoute permission="clientes.visualizar"><PetForm /></ProtectedRoute>} />

                  {/* ========================================
                🩺 MÓDULO VETERINÁRIO
                ======================================== */}
                  <Route path="veterinario" element={<ModuleGate modulo="veterinario"><VetDashboard /></ModuleGate>} />
                  <Route path="veterinario/agenda" element={<ModuleGate modulo="veterinario"><VetAgenda /></ModuleGate>} />
                  <Route path="veterinario/consultas" element={<ModuleGate modulo="veterinario"><VetConsultas /></ModuleGate>} />
                  <Route path="veterinario/consultas/nova" element={<ModuleGate modulo="veterinario"><VetConsultaForm /></ModuleGate>} />
                  <Route path="veterinario/consultas/:consultaId" element={<ModuleGate modulo="veterinario"><VetConsultaForm /></ModuleGate>} />
                  <Route path="veterinario/exames" element={<ModuleGate modulo="veterinario"><VetExamesAnexados /></ModuleGate>} />
                  <Route path="veterinario/ia" element={<ModuleGate modulo="veterinario"><VetAssistenteIA /></ModuleGate>} />
                  <Route path="veterinario/assistente-ia" element={<ModuleGate modulo="veterinario"><VetAssistenteIA /></ModuleGate>} />
                  <Route path="veterinario/calculadora-doses" element={<ModuleGate modulo="veterinario"><VetCalculadoraDoses /></ModuleGate>} />
                  <Route path="veterinario/vacinas" element={<ModuleGate modulo="veterinario"><VetVacinas /></ModuleGate>} />
                  <Route path="veterinario/internacoes" element={<ModuleGate modulo="veterinario"><VetInternacoes /></ModuleGate>} />
                  <Route path="veterinario/catalogo" element={<ModuleGate modulo="veterinario"><VetCatalogo /></ModuleGate>} />
                  <Route path="veterinario/configuracoes" element={<ModuleGate modulo="veterinario"><VetConfiguracoes /></ModuleGate>} />
                  <Route path="veterinario/repasse" element={<ModuleGate modulo="veterinario"><VetRepasse /></ModuleGate>} />

                  {/* Modulo Banho & Tosa */}
                  <Route path="banho-tosa" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="dashboard" /></ModuleGate>} />
                  <Route path="banho-tosa/servicos" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="servicos" /></ModuleGate>} />
                  <Route path="banho-tosa/parametros" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="parametros" /></ModuleGate>} />
                  <Route path="banho-tosa/recursos" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="recursos" /></ModuleGate>} />
                  <Route path="banho-tosa/agenda" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="agenda" /></ModuleGate>} />
                  <Route path="banho-tosa/fila" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="fila" /></ModuleGate>} />
                  <Route path="banho-tosa/fechamentos" element={<Navigate to="/banho-tosa/fila" replace />} />
                  <Route path="banho-tosa/pacotes" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="pacotes" /></ModuleGate>} />
                  <Route path="banho-tosa/retornos" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="retornos" /></ModuleGate>} />
                  <Route path="banho-tosa/taxi-dog" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="taxi-dog" /></ModuleGate>} />
                  <Route path="banho-tosa/relatorios" element={<ModuleGate modulo="banho_tosa"><BanhoTosaPage view="relatorios" /></ModuleGate>} />

                  {/* ========================================
                📦 ROTAS OFICIAIS DE PRODUTOS (JSX) - ATIVAS
                ======================================== */}
                  <Route
                    path="produtos"
                    element={
                      <ProtectedRoute permission="produtos.visualizar">
                        <Produtos />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="produtos/novo"
                    element={
                      <ProtectedRoute permission="produtos.criar">
                        <ProdutosNovo />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="produtos/:id/editar"
                    element={
                      <ProtectedRoute permission="produtos.editar">
                        <ProdutosNovo />
                      </ProtectedRoute>
                    }
                  />

                  {/* ========================================
                🆕 SPRINT 7 - ROTAS TYPESCRIPT (DESATIVADAS)
                ======================================== */}
                  {/* <Route path="produtos" element={<ProdutosPage />} /> */}
                  {/* <Route path="produtos/novo" element={<ProdutoForm mode="create" />} /> */}
                  {/* <Route path="produtos/:id/editar" element={<ProdutoEditPage />} /> */}

                  {/* Rotas auxiliares de produtos (mantidas) */}
                  <Route
                    path="produtos/:id/movimentacoes"
                    element={<ProtectedRoute permission="produtos.visualizar"><MovimentacoesProduto /></ProtectedRoute>}
                  />
                  <Route
                    path="produtos/relatorio"
                    element={<ProtectedRoute permission="produtos.visualizar"><ProdutosRelatorio /></ProtectedRoute>}
                  />
                  <Route
                    path="produtos/validade-proxima"
                    element={<Navigate to="/estoque/alertas?aba=validade" replace />}
                  />
                  <Route
                    path="produtos/valorizacao-estoque"
                    element={
                      <ProtectedRoute permission="produtos.visualizar">
                        <ProdutosValorizacaoEstoque />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="produtos/balanco"
                    element={
                      <ProtectedRoute permission="produtos.editar">
                        <ProdutosBalanco />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="estoque/alertas"
                    element={
                      <ProtectedRoute permission="produtos.visualizar">
                        <AlertasEstoque />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="estoque/full-nf"
                    element={
                      <ProtectedRoute permission="produtos.editar">
                        <EstoqueFullNF />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="estoque/transferencia-parceiro"
                    element={
                      <ProtectedRoute permission="produtos.editar">
                        <EstoqueTransferenciaParceiro />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="fiscal/sefaz"
                    element={<Navigate to="/compras/entrada-xml" replace />}
                  />
                  <Route path="lembretes" element={<Lembretes />} />
                  <Route
                    path="calculadora-racao"
                    element={<ProtectedRoute permission="produtos.visualizar"><CalculadoraRacao /></ProtectedRoute>}
                  />

                  {/* Rotas de Vendas */}
                  <Route
                    path="pdv"
                    element={
                      <ProtectedRoute permission="vendas.criar">
                        <PDV />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="meus-caixas" element={<ProtectedRoute permission="vendas.criar"><MeusCaixas /></ProtectedRoute>} />
                  <Route path="notas-fiscais" element={<Navigate to="/notas-fiscais/saida" replace />} />
                  <Route path="notas-fiscais/vendas" element={<Navigate to="/notas-fiscais/saida" replace />} />
                  <Route path="notas-fiscais/saida" element={<ModuleGate modulo="fiscal"><CentralNFSaida /></ModuleGate>} />
                  <Route path="notas-fiscais/entrada" element={<ModuleGate modulo="compras"><NFEntrada /></ModuleGate>} />
                  <Route
                    path="campanhas"
                    element={
                      <ModuloBloqueado modulo="campanhas">
                        <Campanhas />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="campanhas/canais"
                    element={
                      <ModuloBloqueado modulo="campanhas">
                        <CanalDescontos />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="ecommerce/aparencia"
                    element={
                      <ModuloBloqueado modulo="ecommerce">
                        <EcommerceAparencia />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="ecommerce/configuracoes"
                    element={
                      <ModuloBloqueado modulo="ecommerce">
                        <EcommerceConfig />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="ecommerce/analytics"
                    element={
                      <ModuloBloqueado modulo="ecommerce">
                        <EcommerceAnalytics />
                      </ModuloBloqueado>
                    }
                  />

                  {/* Rotas de Compras */}
                  <Route
                    path="compras/pedidos"
                    element={
                      <ModuleGate modulo="compras">
                        <ProtectedRoute permission="compras.gerenciar">
                          <PedidosCompra />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="compras/entrada-xml"
                    element={
                      <ModuleGate modulo="compras">
                        <ProtectedRoute permission="compras.gerenciar">
                          <EntradaXML />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="compras/pendencias"
                    element={
                      <ModuleGate modulo="compras">
                        <ProtectedRoute permission="compras.gerenciar">
                          <ComprasPendencias />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="produtos/sinc-bling"
                    element={
                      <ModuleGate modulo="bling">
                        <ProtectedRoute permission="compras.gerenciar">
                          <EstoqueBling />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route path="compras/bling" element={<Navigate to="/produtos/sinc-bling" replace />} />
                  <Route
                    path="vendas/bling-pedidos"
                    element={
                      <ModuleGate modulo="bling">
                        <ProtectedRoute permission="compras.gerenciar">
                          <PedidosBling />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="vendas/bling-monitor"
                    element={
                      <ModuleGate modulo="bling">
                        <ProtectedRoute permission="compras.gerenciar">
                          <BlingFlowMonitor />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />

                  {/* Rotas Financeiras */}
                  <Route
                    path="financeiro"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <DashboardFinanceiro />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/vendas"
                    element={
                      <ProtectedRoute
                        anyOfPermissions={[
                          "relatorios.financeiro",
                          "clientes.visualizar",
                        ]}
                      >
                        <VendasFinanceiro />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="financeiro/relatorio-vendas"
                    element={
                      <ProtectedRoute permission="relatorios.financeiro">
                        <RelatorioVendas />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="financeiro/contas-pagar"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <ContasPagar />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/contas-receber"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <ContasReceber />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/conciliacao-3abas"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <ConciliacaoCartoesTabs />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/historico-conciliacoes"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <HistoricoConciliacoes />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/conciliacao-bancaria"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <ConciliacaoBancaria />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/fluxo-caixa"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <FluxoCaixa />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="financeiro/dre"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="relatorios.financeiro">
                          <DRE />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />

                  {/* Rotas de Comissões */}
                  <Route path="comissoes" element={<ModuleGate modulo="comissoes"><Comissoes /></ModuleGate>} />
                  <Route
                    path="comissoes/demonstrativo"
                    element={<ModuleGate modulo="comissoes"><ComissoesListagem /></ModuleGate>}
                  />
                  <Route
                    path="comissoes/relatorios"
                    element={<ModuleGate modulo="comissoes"><RelatoriosComissoes /></ModuleGate>}
                  />
                  <Route
                    path="comissoes/abertas"
                    element={<ModuleGate modulo="comissoes"><ComissoesAbertas /></ModuleGate>}
                  />
                  <Route
                    path="comissoes/fechamento/:funcionario_id"
                    element={<ModuleGate modulo="comissoes"><ConferenciaAvancada /></ModuleGate>}
                  />
                  <Route
                    path="comissoes/fechamentos"
                    element={<ModuleGate modulo="comissoes"><ComissoesHistoricoFechamentos /></ModuleGate>}
                  />
                  <Route
                    path="comissoes/fechamentos/detalhe"
                    element={<ModuleGate modulo="comissoes"><ComissoesFechamentoDetalhe /></ModuleGate>}
                  />
                  <Route path="subcategorias" element={<Subcategorias />} />

                  {/* Rotas de Cadastros */}
                  <Route path="cadastros/departamentos" element={<ProtectedRoute permission="cadastros.categorias_produtos"><Departamentos /></ProtectedRoute>} />
                  <Route path="cadastros/marcas" element={<ProtectedRoute permission="cadastros.categorias_produtos"><Marcas /></ProtectedRoute>} />
                  <Route path="cadastros/categorias" element={<ProtectedRoute permission="cadastros.categorias_produtos"><Categorias /></ProtectedRoute>} />
                  <Route
                    path="cadastros/tipos-despesa"
                    element={<ProtectedRoute permission="cadastros.categorias_financeiras"><TipoDespesa /></ProtectedRoute>}
                  />
                  <Route
                    path="cadastros/despesas-rapidas"
                    element={<ProtectedRoute permission="cadastros.categorias_financeiras"><TipoDespesa /></ProtectedRoute>}
                  />
                  <Route
                    path="cadastros/categorias-financeiras"
                    element={<ModuleGate modulo="financeiro_erp"><CategoriasFinanceiras /></ModuleGate>}
                  />
                  <Route
                    path="cadastros/especies-racas"
                    element={<ProtectedRoute permission="cadastros.especies_racas"><EspeciesRacas /></ProtectedRoute>}
                  />
                  <Route path="cadastros/cargos" element={<ModuleGate modulo="rh"><Cargos /></ModuleGate>} />
                  <Route
                    path="cadastros/financeiro/bancos"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="configuracoes.editar">
                          <ContasBancarias />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="cadastros/financeiro/formas-pagamento"
                    element={
                      <ProtectedRoute permission="configuracoes.editar">
                        <FormasPagamento />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="cadastros/financeiro/operadoras"
                    element={
                      <ProtectedRoute permission="configuracoes.editar">
                        <OperadorasCartao />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="subcategorias" element={<Subcategorias />} />

                  {/* Rotas de Administração */}
                  <Route
                    path="admin/usuarios"
                    element={
                      <ProtectedRoute permission="usuarios.manage">
                        <UsuariosPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="configuracoes"
                    element={
                      <ProtectedRoute permission="configuracoes.editar">
                        <Configuracoes />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="configuracoes/fiscal"
                    element={
                      <ProtectedRoute anyOfPermissions={["configuracoes.empresa", "configuracoes.editar"]}>
                        <ConfiguracaoFiscalEmpresa />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="configuracoes/geral"
                    element={
                      <ProtectedRoute permission="configuracoes.editar">
                        <ConfiguracaoGeralNegocio />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="configuracoes/entregas"
                    element={<ModuleGate modulo="entregas"><EntregasConfig /></ModuleGate>}
                  />
                  <Route
                    path="configuracoes/custos-moto"
                    element={<ModuleGate modulo="entregas"><CustosMoto /></ModuleGate>}
                  />
                  <Route
                    path="configuracoes/estoque"
                    element={
                      <ProtectedRoute permission="configuracoes.editar">
                        <ConfiguracaoEstoque />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="configuracoes/integracoes"
                    element={<ModuleGate modulo="integracoes"><Integracoes /></ModuleGate>}
                  />
                  {/* <Route path="configuracoes/simples/fechamento" element={<FechamentoSimples />} /> */}
                  <Route
                    path="auditoria/provisoes"
                    element={<ModuleGate modulo="financeiro_erp"><AuditoriaMensal /></ModuleGate>}
                  />
                  <Route path="projecao-caixa" element={<ModuleGate modulo="financeiro_erp"><ProjecaoCaixa /></ModuleGate>} />
                  <Route
                    path="simulacao-contratacao"
                    element={<ModuleGate modulo="rh"><SimulacaoContratacao /></ModuleGate>}
                  />
                  <Route path="rh/funcionarios" element={<ModuleGate modulo="rh"><Funcionarios /></ModuleGate>} />
                  <Route
                    path="admin/roles"
                    element={
                      <ProtectedRoute permission="usuarios.manage">
                        <RolesPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="admin/lgpd"
                    element={
                      <ProtectedRoute permission="usuarios.manage">
                        <LGPDOperacional />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="lgpd"
                    element={<Navigate to="/admin/lgpd" replace />}
                  />
                  <Route
                    path="admin/observabilidade"
                    element={<Navigate to="/ops/observabilidade" replace />}
                  />

                  {/* Página de ajuda, planos e dúvidas — acessível sem módulo */}
                  <Route path="ajuda" element={<Ajuda />} />

                  {/* Rotas de Entregas */}
                  <Route
                    path="entregas/abertas"
                    element={
                      <ModuloBloqueado modulo="entregas">
                        <EntregasAbertas />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="entregas/rotas"
                    element={
                      <ModuloBloqueado modulo="entregas">
                        <RotasEntrega />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="entregas/historico"
                    element={
                      <ModuloBloqueado modulo="entregas">
                        <HistoricoEntregas />
                      </ModuloBloqueado>
                    }
                  />
                  <Route
                    path="entregas/financeiro"
                    element={
                      <ModuloBloqueado modulo="entregas">
                        <DashEntregasFinanceiro />
                      </ModuloBloqueado>
                    }
                  />

                  {/* Rotas de E-commerce MVP */}

                  <Route
                    path="ia/fluxo-caixa"
                    element={
                      <ModuleGate modulo="financeiro_erp">
                        <ProtectedRoute permission="ia.fluxo_caixa">
                          <IAFluxoCaixa />
                        </ProtectedRoute>
                      </ModuleGate>
                    }
                  />
                  <Route
                    path="ia/chat"
                    element={<ModuleGate modulo="financeiro_erp"><ChatIA /></ModuleGate>}
                  />
                  <Route
                    path="ia/whatsapp"
                    element={
                      <ProtectedRoute permission="ia.whatsapp">
                        <ModuloBloqueado modulo="whatsapp">
                          <WhatsAppDashboard />
                        </ModuloBloqueado>
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="ia/alertas-racao"
                    element={
                      <ProtectedRoute permission="produtos.editar">
                        <AlertasRacao />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="cadastros/opcoes-racao"
                    element={
                      <ProtectedRoute permission="produtos.editar">
                        <OpcoesRacao />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* Redirect para dashboard */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ModulosProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
