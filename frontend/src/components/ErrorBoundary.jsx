import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

const CHUNK_RELOAD_RETRY_KEY = 'lazy-chunk-reload-at';
const CHUNK_RELOAD_WINDOW_MS = 5 * 60 * 1000;

function isDynamicImportError(error) {
  const message = String(error?.message || error || '').toLowerCase();

  return (
    message.includes('failed to fetch dynamically imported module') ||
    message.includes('importing a module script failed') ||
    message.includes('chunkloaderror') ||
    message.includes('loading chunk')
  );
}

function shouldRetryChunkReload() {
  try {
    const lastAttempt = Number(
      window.sessionStorage.getItem(CHUNK_RELOAD_RETRY_KEY) || 0,
    );
    return !lastAttempt || Date.now() - lastAttempt > CHUNK_RELOAD_WINDOW_MS;
  } catch {
    return true;
  }
}

function markChunkReloadAttempt() {
  try {
    window.sessionStorage.setItem(
      CHUNK_RELOAD_RETRY_KEY,
      String(Date.now()),
    );
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
    console.error('Critical error caught by ErrorBoundary:', error, errorInfo);

    if (isDynamicImportError(error) && shouldRetryChunkReload()) {
      markChunkReloadAttempt();
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

      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-red-100 p-8 max-w-lg w-full text-center">
            <div className="flex justify-center mb-4">
              <div className="bg-red-100 rounded-full p-4">
                <AlertTriangle className="w-10 h-10 text-red-600" />
              </div>
            </div>

            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Algo deu errado
            </h1>
            <p className="text-gray-600 mb-6">
              {isChunkError
                ? 'A tela foi atualizada no servidor e esta aba ficou com um arquivo antigo. Vamos tentar carregar novamente.'
                : 'Ocorreu um erro inesperado na tela. Seus dados estao seguros. Recarregue a pagina para continuar.'}
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
              <button
                onClick={this.handleBack}
                className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                {'<-'} Voltar
              </button>
              <button
                onClick={this.handleReload}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Recarregar pagina
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
