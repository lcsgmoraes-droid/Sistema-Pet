import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children, permission, requiredPermissions }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Se uma permissão específica é exigida
  if (permission || requiredPermissions) {
    const userPermissions = user?.permissions || [];
    const roleName = user?.role?.name?.toLowerCase();
    
    // Admin tem acesso a tudo
    if (roleName === 'admin') {
      return children;
    }

    // Verifica permissão única (permissions é array de strings)
    if (permission) {
      const hasPermission = userPermissions.includes(permission);
      if (!hasPermission) {
        return (
          <div className="flex items-center justify-center min-h-screen bg-gray-50">
            <div className="text-center">
              <div className="text-6xl mb-4">🔒</div>
              <h1 className="text-2xl font-bold text-gray-800 mb-2">Acesso Negado</h1>
              <p className="text-gray-600 mb-4">Você não tem permissão para acessar esta página.</p>
              <p className="text-sm text-gray-500">Permissão necessária: {permission}</p>
              <button 
                onClick={() => window.history.back()} 
                className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Voltar
              </button>
            </div>
          </div>
        );
      }
    }

    // Verifica múltiplas permissões (todas necessárias)
    if (requiredPermissions && requiredPermissions.length > 0) {
      const hasAllPermissions = requiredPermissions.every(
        reqPerm => userPermissions.includes(reqPerm)
      );
      if (!hasAllPermissions) {
        return (
          <div className="flex items-center justify-center min-h-screen bg-gray-50">
            <div className="text-center">
              <div className="text-6xl mb-4">🔒</div>
              <h1 className="text-2xl font-bold text-gray-800 mb-2">Acesso Negado</h1>
              <p className="text-gray-600 mb-4">Você não tem permissão para acessar esta página.</p>
              <p className="text-sm text-gray-500">Permissões necessárias: {requiredPermissions.join(', ')}</p>
              <button 
                onClick={() => window.history.back()} 
                className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Voltar
              </button>
            </div>
          </div>
        );
      }
    }
  }

  return children;
};

export default ProtectedRoute;
