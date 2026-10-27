import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Carregando } from "./components/ui";
import Layout from "./layout/Layout";
import Dashboard from "./pages/Dashboard";
import LojaDetalhe from "./pages/LojaDetalhe";
import Lojas from "./pages/Lojas";
import Login from "./pages/Login";
import TrocarSenha from "./pages/TrocarSenha";

function Protegida({ children }) {
  const { admin, carregando } = useAuth();
  if (carregando) {
    return (
      <div className="mx-auto max-w-md p-8">
        <Carregando rotulo="Verificando acesso" />
      </div>
    );
  }
  if (!admin) return <Navigate to="/login" replace />;
  return children;
}

// Senha provisoria: nada abre antes de trocar.
function ExigeSenhaDefinitiva({ children }) {
  const { admin } = useAuth();
  if (admin?.precisa_trocar_a_senha) return <Navigate to="/trocar-senha" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/trocar-senha"
        element={
          <Protegida>
            <TrocarSenhaNoLayout />
          </Protegida>
        }
      />
      <Route
        element={
          <Protegida>
            <ExigeSenhaDefinitiva>
              <Layout />
            </ExigeSenhaDefinitiva>
          </Protegida>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="lojas" element={<Lojas />} />
        <Route path="lojas/:id" element={<LojaDetalhe />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// Troca voluntaria usa o menu; a obrigatoria aparece sozinha, sem menu.
function TrocarSenhaNoLayout() {
  const { admin } = useAuth();
  if (admin?.precisa_trocar_a_senha) return <TrocarSenha />;
  return (
    <Layout outlet={<TrocarSenha />} />
  );
}
