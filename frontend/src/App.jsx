import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Pessoas from './pages/ClientesNovo';

// ========================================
// 🆕 SPRINT 7 - NOVA INTERFACE DE PRODUTOS (TYPESCRIPT) - DESATIVADA
// ========================================
// import ProdutosPage from './pages/produtos/ProdutosPage';
// import ProdutoForm from './pages/produtos/components/ProdutoForm';
// import ProdutoEditPage from './pages/produtos/ProdutoEditPage';

// ========================================
// 📦 INTERFACE OFICIAL DE PRODUTOS (JSX) - ATIVA
// ========================================
import Produtos from './pages/Produtos';
import ProdutosNovo from './pages/ProdutosNovo';
import ProdutosRelatorio from './pages/ProdutosRelatorio';
import AlertasEstoque from './pages/AlertasEstoque';
import Lembretes from './pages/Lembretes';
import CalculadoraRacao from './pages/CalculadoraRacao';

// Componentes de Pets
import GerenciamentoPets from './pages/GerenciamentoPets';
import PetDetalhes from './pages/PetDetalhes';
import PetForm from './pages/PetForm';

import PDV from './pages/PDV';
import MeusCaixas from './pages/MeusCaixas';
import NotasFiscais from './pages/NotasFiscais';

// Timeline de Cliente
import ClienteTimelinePage from './pages/ClienteTimelinePage';

// Componentes de Estoque/Compras
import MovimentacoesProduto from './components/MovimentacoesProduto';
import EstoqueBling from './components/EstoqueBling';
import PedidosCompra from './components/PedidosCompra';
import EntradaXML from './components/EntradaXML';

// Componentes Financeiros
import DashboardFinanceiro from './pages/DashboardFinanceiro';
import ContasBancarias from './components/ContasBancarias';
import ContasPagar from './components/ContasPagar';
import ContasReceber from './components/ContasReceber';
import ConciliacaoCartoesTabs from './pages/ConciliacaoCartoesTabs';  // FASE 8: Arquitetura 3 Abas
import HistoricoConciliacoes from './pages/HistoricoConciliacoes';  // Histórico de Conciliações
import ConciliacaoBancaria from './pages/ConciliacaoBancaria';
import FormasPagamento from './components/FormasPagamento';
import OperadorasCartao from './pages/OperadorasCartao';
import FluxoCaixa from './components/FluxoCaixa';
import RelatorioVendas from './components/RelatorioVendas';
import VendasFinanceiro from './components/VendasFinanceiro';
import DRE from './components/DRE';

// Componentes de IA
import IAFluxoCaixa from './pages/IAFluxoCaixa';
import ChatIA from './pages/IA/ChatIA';
import DREInteligente from './pages/IA/DREInteligente';
import RotasInteligentes from './pages/RotasInteligentes';
import { WhatsAppDashboard } from './pages/WhatsAppDashboard/index.tsx';
import Comissoes from './pages/Comissoes';
import ComissoesListagem from './pages/comissoes/ComissoesListagem';
import ComissoesAbertas from './pages/comissoes/ComissoesAbertas';
import ComissoesFechamentoFuncionario from './pages/comissoes/ComissoesFechamentoFuncionario';
import ConferenciaAvancada from './pages/comissoes/ConferenciaAvancada';
import ComissoesHistoricoFechamentos from './pages/comissoes/ComissoesHistoricoFechamentos';
import ComissoesFechamentoDetalhe from './pages/comissoes/ComissoesFechamentoDetalhe';
import RelatoriosComissoes from './pages/comissoes/RelatoriosComissoes';
import Subcategorias from './pages/Subcategorias';
import Categorias from './pages/Cadastros/Categorias';
import CategoriasFinanceiras from './pages/CategoriasFinanceiras';
import EspeciesRacas from './pages/EspeciesRacas';
import ClienteFinanceiro from './pages/ClienteFinanceiro';
import DashboardGerencial from './pages/DashboardGerencial';
import UsuariosPage from './pages/UsuariosPage.jsx';
import RolesPage from './pages/RolesPage.jsx';
import Configuracoes from './pages/Configuracoes';
import ConfiguracaoFiscalEmpresa from './pages/configuracoes/ConfiguracaoFiscalEmpresa';
import EntregasConfig from './pages/configuracoes/EntregasConfig';
import CustosMoto from './pages/configuracoes/CustosMoto';
import ConfiguracaoEstoque from './pages/configuracoes/ConfiguracaoEstoque';
// import FechamentoSimples from './pages/FechamentoSimples'; // TODO: Criar arquivo
import AuditoriaMensal from './pages/AuditoriaMensal';
import ProjecaoCaixa from './pages/ProjecaoCaixa';
import SimulacaoContratacao from './pages/SimulacaoContratacao';
import Cargos from './pages/Cadastros/Cargos';
import Funcionarios from './pages/RH/Funcionarios';
import EntregasAbertas from './pages/entregas/EntregasAbertas';
import RotasEntrega from './pages/entregas/RotasEntrega';
import HistoricoEntregas from './pages/entregas/HistoricoEntregas';
import DashEntregasFinanceiro from './pages/entregas/DashEntregasFinanceiro';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" />
        <Routes>
          {/* Rotas Públicas */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
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
          </Route>
          
          {/* Redirect para dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
