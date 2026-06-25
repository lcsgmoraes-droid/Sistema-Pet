import { Navigate, Route } from "react-router-dom";
import ProtectedRoute from "../../components/ProtectedRoute";
import {
  AlertasEstoque,
  CalculadoraRacao,
  EstoqueFullNF,
  EstoqueTransferenciaParceiro,
  Lembretes,
  MovimentacoesProduto,
  Produtos,
  ProdutosBalanco,
  ProdutosNovo,
  ProdutosRelatorio,
  ProdutosValorizacaoEstoque,
} from "../lazyPages";

export function createProductInventoryRoutes() {
  return (
    <>
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
      <Route
        path="produtos/:id/movimentacoes"
        element={
          <ProtectedRoute permission="produtos.visualizar">
            <MovimentacoesProduto />
          </ProtectedRoute>
        }
      />
      <Route
        path="produtos/relatorio"
        element={
          <ProtectedRoute permission="produtos.visualizar">
            <ProdutosRelatorio />
          </ProtectedRoute>
        }
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
      <Route path="fiscal/sefaz" element={<Navigate to="/compras/entrada-xml" replace />} />
      <Route path="lembretes" element={<Lembretes />} />
      <Route
        path="calculadora-racao"
        element={
          <ProtectedRoute permission="produtos.visualizar">
            <CalculadoraRacao />
          </ProtectedRoute>
        }
      />
    </>
  );
}
