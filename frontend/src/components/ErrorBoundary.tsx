import React, { Component, ErrorInfo, ReactNode } from 'react';

const CHUNK_RELOAD_RETRY_KEY = 'lazy-chunk-reload-at';
const CHUNK_RELOAD_WINDOW_MS = 5 * 60 * 1000;

function isDynamicImportError(error: unknown): boolean {
  const message = String(
    error instanceof Error ? error.message : error || '',
  ).toLowerCase();

  return (
    message.includes('failed to fetch dynamically imported module') ||
    message.includes('importing a module script failed') ||
    message.includes('chunkloaderror') ||
    message.includes('loading chunk')
  );
}

function shouldRetryChunkReload(): boolean {
  try {
    const lastAttempt = Number(
      window.sessionStorage.getItem(CHUNK_RELOAD_RETRY_KEY) || 0,
    );
    return !lastAttempt || Date.now() - lastAttempt > CHUNK_RELOAD_WINDOW_MS;
  } catch {
    return true;
  }
}

function markChunkReloadAttempt(): void {
  try {
    window.sessionStorage.setItem(
      CHUNK_RELOAD_RETRY_KEY,
      String(Date.now()),
    );
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
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    if (isDynamicImportError(error) && shouldRetryChunkReload()) {
      markChunkReloadAttempt();
      window.location.reload();
    }
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const isChunkError = isDynamicImportError(this.state.error);

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
                ? 'A tela foi atualizada no servidor e esta aba ficou com um arquivo antigo. Vamos tentar carregar novamente.'
                : 'Ocorreu um erro inesperado. Por favor, recarregue a pagina.'}
            </p>

            {this.state.error && (
              <div className="mb-6 p-4 bg-gray-50 rounded border border-gray-200">
                <p className="text-xs font-mono text-gray-700 break-words">
                  {this.state.error.message}
                </p>
              </div>
            )}

            <button
              onClick={() => window.location.reload()}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Recarregar pagina
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
