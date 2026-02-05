import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const PrivateRoute = ({ children, requireAdmin = false }) => {
  const { authenticated, userProfile, loading } = useAuth();

  // Mostrar loading enquanto verifica autenticação
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-lg text-blue-600">
        Verificando autenticação...
      </div>
    );
  }

  // Redirecionar para login se não estiver autenticado
  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }

  // Verificar permissão de admin se necessário
  if (requireAdmin && userProfile?.role !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-5 text-center">
        <h1 className="text-5xl text-error-dark m-0">403</h1>
        <h2 className="text-2xl text-neutral-700 mt-4">Acesso Negado</h2>
        <p className="text-base text-neutral-600 mt-2">
          Você não tem permissão para acessar esta página.
        </p>
        <button
          onClick={() => window.history.back()}
          className="mt-6 px-6 py-3 bg-primary text-white border-0 rounded-lg text-base cursor-pointer hover:bg-primary-dark transition-colors"
        >
          Voltar
        </button>
      </div>
    );
  }

  // Renderizar componente filho se tudo ok
  return children;
};

export default PrivateRoute;
