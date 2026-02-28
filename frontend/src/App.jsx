import React, { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const preloadPessoas = () => import('./pages/ClientesNovo');
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
const preloadProdutos = () => import('./pages/Produtos');
const Produtos = lazy(preloadProdutos);
const ProdutosNovo = lazy(() => import('./pages/ProdutosNovo'));
const ProdutosRelatorio = lazy(() => import('./pages/ProdutosRelatorio'));
const AlertasEstoque = lazy(() => import('./pages/AlertasEstoque'));
const preloadLembretes = () => import('./pages/Lembretes');
const Lembretes = lazy(preloadLembretes);
const CalculadoraRacao = lazy(() => import('./pages/CalculadoraRacao'));

// Componentes de Pets
const GerenciamentoPets = lazy(() => import('./pages/GerenciamentoPets'));
const PetDetalhes = lazy(() => import('./pages/PetDetalhes'));
const PetForm = lazy(() => import('./pages/PetForm'));

const preloadPDV = () => import('./pages/PDV');
const PDV = lazy(preloadPDV);
const MeusCaixas = lazy(() => import('./pages/MeusCaixas'));
const NotasFiscais = lazy(() => import('./pages/NotasFiscais'));

// Timeline de Cliente
const ClienteTimelinePage = lazy(() => import('./pages/ClienteTimelinePage'));

// Componentes de Estoque/Compras
const MovimentacoesProduto = lazy(() => import('./components/MovimentacoesProduto'));
const EstoqueBling = lazy(() => import('./components/EstoqueBling'));
const PedidosCompra = lazy(() => import('./components/PedidosCompra'));
const EntradaXML = lazy(() => import('./components/EntradaXML'));

// Componentes Financeiros
const preloadDashboardFinanceiro = () => import('./pages/DashboardFinanceiro');
const DashboardFinanceiro = lazy(preloadDashboardFinanceiro);
const ContasBancarias = lazy(() => import('./components/ContasBancarias'));
const ContasPagar = lazy(() => import('./components/ContasPagar'));
const ContasReceber = lazy(() => import('./components/ContasReceber'));
const ConciliacaoCartoesTabs = lazy(() => import('./pages/ConciliacaoCartoesTabs'));
const HistoricoConciliacoes = lazy(() => import('./pages/HistoricoConciliacoes'));
const ConciliacaoBancaria = lazy(() => import('./pages/ConciliacaoBancaria'));
const FormasPagamento = lazy(() => import('./components/FormasPagamento'));
const OperadorasCartao = lazy(() => import('./pages/OperadorasCartao'));
const FluxoCaixa = lazy(() => import('./components/FluxoCaixa'));
const RelatorioVendas = lazy(() => import('./components/RelatorioVendas'));
const VendasFinanceiro = lazy(() => import('./components/VendasFinanceiro'));
const AlertasRacao = lazy(() => import('./components/AlertasRacao'));
const OpcoesRacao = lazy(() => import('./components/OpcoesRacao'));
const DRE = lazy(() => import('./components/DRE'));

// Componentes de IA
const IAFluxoCaixa = lazy(() => import('./pages/IAFluxoCaixa'));
const ChatIA = lazy(() => import('./pages/IA/ChatIA'));
const DREInteligente = lazy(() => import('./pages/IA/DREInteligente'));
const RotasInteligentes = lazy(() => import('./pages/RotasInteligentes'));
const WhatsAppDashboard = lazy(async () => {
  const module = await import('./pages/WhatsAppDashboard/index.tsx');
  return { default: module.WhatsAppDashboard };
});
const Comissoes = lazy(() => import('./pages/Comissoes'));
const ComissoesListagem = lazy(() => import('./pages/comissoes/ComissoesListagem'));
const ComissoesAbertas = lazy(() => import('./pages/comissoes/ComissoesAbertas'));
const ComissoesFechamentoFuncionario = lazy(() => import('./pages/comissoes/ComissoesFechamentoFuncionario'));
const ConferenciaAvancada = lazy(() => import('./pages/comissoes/ConferenciaAvancada'));
const ComissoesHistoricoFechamentos = lazy(() => import('./pages/comissoes/ComissoesHistoricoFechamentos'));
const ComissoesFechamentoDetalhe = lazy(() => import('./pages/comissoes/ComissoesFechamentoDetalhe'));
const RelatoriosComissoes = lazy(() => import('./pages/comissoes/RelatoriosComissoes'));
const Subcategorias = lazy(() => import('./pages/Subcategorias'));
const Categorias = lazy(() => import('./pages/Cadastros/Categorias'));
const CategoriasFinanceiras = lazy(() => import('./pages/CategoriasFinanceiras'));
const EspeciesRacas = lazy(() => import('./pages/EspeciesRacas'));
const ClienteFinanceiro = lazy(() => import('./pages/ClienteFinanceiro'));
const DashboardGerencial = lazy(() => import('./pages/DashboardGerencial'));
const UsuariosPage = lazy(() => import('./pages/UsuariosPage.jsx'));
const RolesPage = lazy(() => import('./pages/RolesPage.jsx'));
const Configuracoes = lazy(() => import('./pages/Configuracoes'));
const ConfiguracaoFiscalEmpresa = lazy(() => import('./pages/configuracoes/ConfiguracaoFiscalEmpresa'));
const EntregasConfig = lazy(() => import('./pages/configuracoes/EntregasConfig'));
const CustosMoto = lazy(() => import('./pages/configuracoes/CustosMoto'));
const ConfiguracaoEstoque = lazy(() => import('./pages/configuracoes/ConfiguracaoEstoque'));
// import FechamentoSimples from './pages/FechamentoSimples'; // TODO: Criar arquivo
const AuditoriaMensal = lazy(() => import('./pages/AuditoriaMensal'));
const ProjecaoCaixa = lazy(() => import('./pages/ProjecaoCaixa'));
const SimulacaoContratacao = lazy(() => import('./pages/SimulacaoContratacao'));
const Cargos = lazy(() => import('./pages/Cadastros/Cargos'));
const Funcionarios = lazy(() => import('./pages/RH/Funcionarios'));
const EntregasAbertas = lazy(() => import('./pages/entregas/EntregasAbertas'));
const RotasEntrega = lazy(() => import('./pages/entregas/RotasEntrega'));
const HistoricoEntregas = lazy(() => import('./pages/entregas/HistoricoEntregas'));
const DashEntregasFinanceiro = lazy(() => import('./pages/entregas/DashEntregasFinanceiro'));
const EcommerceMVP = lazy(() => import('./pages/ecommerce/EcommerceMVP'));
const EcommerceAparencia = lazy(() => import('./pages/ecommerce/EcommerceAparencia'));
const EcommerceConfig = lazy(() => import('./pages/ecommerce/EcommerceConfig'));
const EcommerceAnalytics = lazy(() => import('./pages/ecommerce/EcommerceAnalytics'));

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
      typeof connection?.effectiveType === 'string' && /(^|-)2g$/.test(connection.effectiveType);

    if (shouldSkipPreload) {
      return () => {
      };
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

    if (typeof window.requestIdleCallback === 'function') {
      idleId = window.requestIdleCallback(runPreload, { timeout: 2200 });
    } else {
      timerId = window.setTimeout(runPreload, 1200);
    }

    return () => {
      cancelled = true;

      if (typeof window.cancelIdleCallback === 'function' && typeof idleId === 'number') {
        window.cancelIdleCallback(idleId);
      }

      if (typeof timerId === 'number') {
        window.clearTimeout(timerId);
      }

      if (typeof delayedTimerId === 'number') {
        window.clearTimeout(delayedTimerId);
      }
    };
  }, []);

  return null;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" />
        <AppRoutePreloader />
        <Suspense fallback={<div className="p-4 text-sm text-gray-500">Carregando...</div>}>
        <Routes>
          {/* Rotas Públicas */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/:tenantId" element={<EcommerceMVP />} />
          <Route path="/ecommerce" element={<EcommerceMVP />} />
          
          {/* Rotas Protegidas */}
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/lembretes" replace />} />
            <Route path="dashboard" element={
              <ProtectedRoute permission="relatorios.gerencial">
                <DashboardFinanceiro />
              </ProtectedRoute>
            } />
            <Route path="dashboard-gerencial" element={
              <ProtectedRoute permission="relatorios.gerencial">
                <DashboardGerencial />
              </ProtectedRoute>
            } />
            <Route path="clientes" element={
              <ProtectedRoute permission="clientes.visualizar">
                <Pessoas />
              </ProtectedRoute>
            } />
            <Route path="clientes/:clienteId/financeiro" element={
              <ProtectedRoute permission="clientes.visualizar">
                <ClienteFinanceiro />
              </ProtectedRoute>
            } />
            <Route path="clientes/:clienteId/timeline" element={
              <ProtectedRoute permission="clientes.visualizar">
                <ClienteTimelinePage />
              </ProtectedRoute>
            } />
            
            {/* Rotas de Pets - Módulo Dedicado */}
            <Route path="pets" element={<GerenciamentoPets />} />
            <Route path="pets/novo" element={<PetForm />} />
            <Route path="pets/:petId" element={<PetDetalhes />} />
            <Route path="pets/:petId/editar" element={<PetForm />} />
            
            {/* ========================================
                📦 ROTAS OFICIAIS DE PRODUTOS (JSX) - ATIVAS
                ======================================== */}
            <Route path="produtos" element={
              <ProtectedRoute permission="produtos.visualizar">
                <Produtos />
              </ProtectedRoute>
            } />
            <Route path="produtos/novo" element={
              <ProtectedRoute permission="produtos.criar">
                <ProdutosNovo />
              </ProtectedRoute>
            } />
            <Route path="produtos/:id/editar" element={
              <ProtectedRoute permission="produtos.editar">
                <ProdutosNovo />
              </ProtectedRoute>
            } />
            
            {/* ========================================
                🆕 SPRINT 7 - ROTAS TYPESCRIPT (DESATIVADAS)
                ======================================== */}
            {/* <Route path="produtos" element={<ProdutosPage />} /> */}
            {/* <Route path="produtos/novo" element={<ProdutoForm mode="create" />} /> */}
            {/* <Route path="produtos/:id/editar" element={<ProdutoEditPage />} /> */}
            
            {/* Rotas auxiliares de produtos (mantidas) */}
            <Route path="produtos/:id/movimentacoes" element={<MovimentacoesProduto />} />
            <Route path="produtos/relatorio" element={<ProdutosRelatorio />} />
            <Route path="estoque/alertas" element={
              <ProtectedRoute permission="produtos.visualizar">
                <AlertasEstoque />
              </ProtectedRoute>
            } />
            <Route path="lembretes" element={<Lembretes />} />
            <Route path="calculadora-racao" element={<CalculadoraRacao />} />

            {/* Rotas de Vendas */}
            <Route path="pdv" element={
              <ProtectedRoute permission="vendas.criar">
                <PDV />
              </ProtectedRoute>
            } />
            <Route path="meus-caixas" element={<MeusCaixas />} />
            <Route path="notas-fiscais" element={<NotasFiscais />} />
            <Route path="ecommerce/aparencia" element={<EcommerceAparencia />} />
            <Route path="ecommerce/configuracoes" element={<EcommerceConfig />} />
            <Route path="ecommerce/analytics" element={<EcommerceAnalytics />} />
            
            {/* Rotas de Compras */}
            <Route path="compras/pedidos" element={
              <ProtectedRoute permission="compras.gerenciar">
                <PedidosCompra />
              </ProtectedRoute>
            } />
            <Route path="compras/entrada-xml" element={
              <ProtectedRoute permission="compras.gerenciar">
                <EntradaXML />
              </ProtectedRoute>
            } />
            <Route path="compras/bling" element={
              <ProtectedRoute permission="compras.gerenciar">
                <EstoqueBling />
              </ProtectedRoute>
            } />
            
            {/* Rotas Financeiras */}
            <Route path="financeiro" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <DashboardFinanceiro />
              </ProtectedRoute>
            } />
            <Route path="financeiro/vendas" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <VendasFinanceiro />
              </ProtectedRoute>
            } />
            <Route path="financeiro/relatorio-vendas" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <RelatorioVendas />
              </ProtectedRoute>
            } />
            <Route path="financeiro/contas-pagar" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <ContasPagar />
              </ProtectedRoute>
            } />
            <Route path="financeiro/contas-receber" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <ContasReceber />
              </ProtectedRoute>
            } />
            <Route path="financeiro/conciliacao-3abas" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <ConciliacaoCartoesTabs />
              </ProtectedRoute>
            } />
            <Route path="financeiro/historico-conciliacoes" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <HistoricoConciliacoes />
              </ProtectedRoute>
            } />
            <Route path="financeiro/conciliacao-bancaria" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <ConciliacaoBancaria />
              </ProtectedRoute>
            } />
            <Route path="financeiro/fluxo-caixa" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <FluxoCaixa />
              </ProtectedRoute>
            } />
            <Route path="financeiro/dre" element={
              <ProtectedRoute permission="relatorios.financeiro">
                <DRE />
              </ProtectedRoute>
            } />
            
            {/* Rotas de Comissões */}
            <Route path="comissoes" element={<Comissoes />} />
            <Route path="comissoes/demonstrativo" element={<ComissoesListagem />} />
            <Route path="comissoes/relatorios" element={<RelatoriosComissoes />} />
            <Route path="comissoes/abertas" element={<ComissoesAbertas />} />
            <Route path="comissoes/fechamento/:funcionario_id" element={<ConferenciaAvancada />} />
            <Route path="comissoes/fechamentos" element={<ComissoesHistoricoFechamentos />} />
            <Route path="comissoes/fechamentos/detalhe" element={<ComissoesFechamentoDetalhe />} />
            <Route path="subcategorias" element={<Subcategorias />} />
            
            {/* Rotas de Cadastros */}
            <Route path="cadastros/categorias" element={<Categorias />} />
            <Route path="cadastros/categorias-financeiras" element={<CategoriasFinanceiras />} />
            <Route path="cadastros/especies-racas" element={<EspeciesRacas />} />
            <Route path="cadastros/cargos" element={<Cargos />} />
            <Route path="cadastros/financeiro/bancos" element={
              <ProtectedRoute permission="configuracoes.editar">
                <ContasBancarias />
              </ProtectedRoute>
            } />
            <Route path="cadastros/financeiro/formas-pagamento" element={
              <ProtectedRoute permission="configuracoes.editar">
                <FormasPagamento />
              </ProtectedRoute>
            } />
            <Route path="cadastros/financeiro/operadoras" element={
              <ProtectedRoute permission="configuracoes.editar">
                <OperadorasCartao />
              </ProtectedRoute>
            } />
            <Route path="subcategorias" element={<Subcategorias />} />
            
            {/* Rotas de Administração */}
            <Route path="admin/usuarios" element={
              <ProtectedRoute permission="usuarios.manage">
                <UsuariosPage />
              </ProtectedRoute>
            } />
            <Route path="configuracoes" element={
              <ProtectedRoute permission="configuracoes.editar">
                <Configuracoes />
              </ProtectedRoute>
            } />
            <Route path="configuracoes/fiscal" element={<ConfiguracaoFiscalEmpresa />} />
            <Route path="configuracoes/entregas" element={<EntregasConfig />} />
            <Route path="configuracoes/custos-moto" element={<CustosMoto />} />
            <Route path="configuracoes/estoque" element={<ConfiguracaoEstoque />} />
            {/* <Route path="configuracoes/simples/fechamento" element={<FechamentoSimples />} /> */}
            <Route path="auditoria/provisoes" element={<AuditoriaMensal />} />
            <Route path="projecao-caixa" element={<ProjecaoCaixa />} />
            <Route path="simulacao-contratacao" element={<SimulacaoContratacao />} />
            <Route path="rh/funcionarios" element={<Funcionarios />} />
            <Route path="admin/roles" element={<RolesPage />} />

            {/* Rotas de Entregas */}
            <Route path="entregas/abertas" element={<EntregasAbertas />} />
            <Route path="entregas/rotas" element={<RotasEntrega />} />
            <Route path="entregas/historico" element={<HistoricoEntregas />} />
            <Route path="entregas/financeiro" element={<DashEntregasFinanceiro />} />

            {/* Rotas de E-commerce MVP */}

            <Route path="ia/fluxo-caixa" element={
              <ProtectedRoute permission="ia.fluxo_caixa">
                <IAFluxoCaixa />
              </ProtectedRoute>
            } />
            <Route path="ia/chat" element={<ChatIA />} />
            <Route path="ia/whatsapp" element={
              <ProtectedRoute permission="ia.whatsapp">
                <WhatsAppDashboard />
              </ProtectedRoute>
            } />
            <Route path="ia/alertas-racao" element={
              <ProtectedRoute permission="produtos.editar">
                <AlertasRacao />
              </ProtectedRoute>
            } />
            <Route path="cadastros/opcoes-racao" element={
              <ProtectedRoute permission="produtos.editar">
                <OpcoesRacao />
              </ProtectedRoute>
            } />
          </Route>
          
          {/* Redirect para dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
