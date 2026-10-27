import React from "react";
import { AlertTriangle, ArrowLeft, RefreshCw } from "lucide-react";
import BotaoInteracao from "./v2/BotaoInteracao/BotaoInteracao";
import { isDynamicImportError, recoverFromChunkError } from "../utils/chunkRecovery";
const DOM_DETACH_RELOAD_RETRY_KEY = "dom-detach-reload-at";
const DOM_DETACH_RELOAD_WINDOW_MS = 2 * 60 * 1000;

function isDomDetachError(error) {
  const message = String(error?.message || error || "").toLowerCase();
  return (
    message.includes("failed to execute 'removechild' on 'node'") ||
    message.includes("the node to be removed is not a child of this node")
  );
}

function shouldRetryDomDetachReload() {
  try {
    const lastAttempt = Number(window.sessionStorage.getItem(DOM_DETACH_RELOAD_RETRY_KEY) || 0);
    return !lastAttempt || Date.now() - lastAttempt > DOM_DETACH_RELOAD_WINDOW_MS;
  } catch {
    return true;
  }
}

function markDomDetachReloadAttempt() {
  try {
    window.sessionStorage.setItem(DOM_DETACH_RELOAD_RETRY_KEY, String(Date.now()));
  } catch {
    // Ignore storage issues and fallback to the regular error screen.
  }
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("Critical error caught by ErrorBoundary:", error, errorInfo);

    if (recoverFromChunkError(error)) return;

    if (isDomDetachError(error) && shouldRetryDomDetachReload()) {
      markDomDetachReloadAttempt();
      window.location.reload();
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleBack = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.history.back();
  };

  render() {
    if (this.state.hasError) {
      const isChunkError = isDynamicImportError(this.state.error);
      const isDomDetach = isDomDetachError(this.state.error);

      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-red-100 p-8 max-w-lg w-full text-center">
            <div className="flex justify-center mb-4">
              <div className="bg-red-100 rounded-full p-4">
                <AlertTriangle className="w-10 h-10 text-red-600" />
              </div>
            </div>

            <h1 className="text-2xl font-bold text-gray-900 mb-2">Algo deu errado</h1>
            <p className="text-gray-600 mb-6">
              {isChunkError
                ? "Não foi possível carregar esta parte da tela. Verifique sua conexão e tente recarregar a página."
                : isDomDetach
                  ? "A tela teve uma falha pontual de renderizacao. Recarregue a pagina para continuar."
                  : "Ocorreu um erro inesperado na tela. Seus dados estao seguros. Recarregue a pagina para continuar."}
            </p>

            {this.state.error && (
              <details className="mb-6 text-left bg-gray-50 rounded-lg p-4 border border-gray-200">
                <summary className="text-sm font-medium text-gray-700 cursor-pointer">
                  Detalhes tecnicos
                </summary>
                <pre className="mt-2 text-xs text-red-700 overflow-auto whitespace-pre-wrap">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}

            <div className="flex gap-3 justify-center">
              <BotaoInteracao onClick={this.handleBack} icon={ArrowLeft}>
                Voltar
              </BotaoInteracao>
              <BotaoInteracao onClick={this.handleReload} icon={RefreshCw}>
                Recarregar pagina
              </BotaoInteracao>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
