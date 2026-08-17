import { Suspense, useEffect } from "react";
import { Toaster, toast } from "react-hot-toast";
import { BrowserRouter } from "react-router-dom";
import AppRoutePreloader from "./app/AppRoutePreloader";
import AppRoutes from "./app/AppRoutes";
import ErrorBoundary from "./components/ErrorBoundary";
import CorePetDialogHost from "./components/ui/CorePetDialogHost";
import { AuthProvider } from "./contexts/AuthContext";
import { ModulosProvider } from "./contexts/ModulosContext";
import { PlatformAuthProvider } from "./contexts/PlatformAuthContext";
import { ThemeProvider } from "./theme/ThemeContext";

function App() {
  useEffect(() => {
    const alertaNativo = window.alert;

    window.alert = (mensagem) => {
      const texto = String(mensagem ?? "").trim() || "Operação concluída.";
      const textoNormalizado = texto.toLocaleLowerCase("pt-BR");

      if (/(erro|falha|inválid|invalíd|não foi possível|nao foi possivel)/.test(textoNormalizado)) {
        toast.error(texto, { duration: 5000 });
        return;
      }

      if (/(sucesso|concluíd|salv[ao]|criad[ao]|atualizad[ao])/.test(textoNormalizado)) {
        toast.success(texto, { duration: 4000 });
        return;
      }

      toast(texto, { icon: "ℹ️", duration: 4500 });
    };

    return () => {
      window.alert = alertaNativo;
    };
  }, []);

  return (
    <ThemeProvider>
      <ErrorBoundary>
        <AuthProvider>
          <PlatformAuthProvider>
            <ModulosProvider>
              <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                <Toaster position="top-right" toastOptions={{ className: "corepet-toast" }} />
                <CorePetDialogHost />
                <AppRoutePreloader />
                <Suspense
                  fallback={
                    <div className="p-4 text-sm text-gray-500 dark:text-slate-400">
                      Carregando...
                    </div>
                  }
                >
                  <AppRoutes />
                </Suspense>
              </BrowserRouter>
            </ModulosProvider>
          </PlatformAuthProvider>
        </AuthProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
