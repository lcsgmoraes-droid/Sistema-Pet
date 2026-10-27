import React, { Component, ErrorInfo, ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import BotaoInteracao from "./v2/BotaoInteracao/BotaoInteracao";
import { isDynamicImportError, recoverFromChunkError } from "../utils/chunkRecovery";
const DOM_DETACH_RELOAD_RETRY_KEY = "dom-detach-reload-at";
const DOM_DETACH_RELOAD_WINDOW_MS = 2 * 60 * 1000;

function isDomDetachError(error: unknown): boolean {
  const message = String(error instanceof Error ? error.message : error || "").toLowerCase();

  return (
    message.includes("failed to execute 'removechild' on 'node'") ||
    message.includes("the node to be removed is not a child of this node")
  );
}

function shouldRetryDomDetachReload(): boolean {
  try {
    const lastAttempt = Number(window.sessionStorage.getItem(DOM_DETACH_RELOAD_RETRY_KEY) || 0);
    return !lastAttempt || Date.now() - lastAttempt > DOM_DETACH_RELOAD_WINDOW_MS;
  } catch {
    return true;
  }
}

function markDomDetachReloadAttempt(): void {
  try {
    window.sessionStorage.setItem(DOM_DETACH_RELOAD_RETRY_KEY, String(Date.now()));
  } catch {
    // Ignore storage issues and fallback to the regular error screen.
  }
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    if (recoverFromChunkError(error)) return;

    if (isDomDetachError(error) && shouldRetryDomDetachReload()) {
      markDomDetachReloadAttempt();
      window.location.reload();
    }
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const isChunkError = isDynamicImportError(this.state.error);
      const isDomDetach = isDomDetachError(this.state.error);

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h1 className="text-xl font-semibold text-gray-900 text-center mb-2">
              Algo deu errado
            </h1>

            <p className="text-sm text-gray-600 text-center mb-6">
              {isChunkError
                ? "Não foi possível carregar esta parte da tela. Verifique sua conexão e tente recarregar a página."
                : isDomDetach
                  ? "A tela teve uma falha pontual de renderizacao. Recarregue a pagina para continuar."
                  : "Ocorreu um erro inesperado. Por favor, recarregue a pagina."}
            </p>

            {this.state.error && (
              <div className="mb-6 p-4 bg-gray-50 rounded border border-gray-200">
                <p className="text-xs font-mono text-gray-700 break-words">
                  {this.state.error.message}
                </p>
              </div>
            )}

            <BotaoInteracao onClick={() => window.location.reload()} icon={RefreshCw} larguraTotal>
              Recarregar pagina
            </BotaoInteracao>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
