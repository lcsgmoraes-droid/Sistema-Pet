import { Suspense } from "react";
import { Toaster } from "react-hot-toast";
import { BrowserRouter } from "react-router-dom";
import AppRoutePreloader from "./app/AppRoutePreloader";
import AppRoutes from "./app/AppRoutes";
import ErrorBoundary from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { ModulosProvider } from "./contexts/ModulosContext";
import { ThemeProvider } from "./theme/ThemeContext";

function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <AuthProvider>
          <ModulosProvider>
            <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
              <Toaster position="top-right" toastOptions={{ className: "corepet-toast" }} />
              <AppRoutePreloader />
              <Suspense
                fallback={
                  <div className="p-4 text-sm text-gray-500 dark:text-slate-400">Carregando...</div>
                }
              >
                <AppRoutes />
              </Suspense>
            </BrowserRouter>
          </ModulosProvider>
        </AuthProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
