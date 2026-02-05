import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import PrivateRoute from './components/PrivateRoute';
import Navbar from './components/Navbar';
import LoginNew from './pages/LoginNew';
import AdmissionView from './pages/AdmissionView';
import UserManagement from './pages/UserManagement';

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <div className="App">
          <Routes>
            {/* Rota pública - Login */}
            <Route path="/login" element={<LoginNew />} />

            {/* Rota raiz redireciona para admissão */}
            <Route path="/" element={<Navigate to="/admissao" replace />} />

            {/* Rotas protegidas - Requer autenticação */}
            <Route
              path="/admissao"
              element={
                <PrivateRoute>
                  <Navbar />
                  <AdmissionView />
                </PrivateRoute>
              }
            />

            {/* Rota de gerenciamento de usuários - Requer admin */}
            <Route
              path="/usuarios"
              element={
                <PrivateRoute requireAdmin={true}>
                  <Navbar />
                  <UserManagement />
                </PrivateRoute>
              }
            />

            {/* Rota 404 - Página não encontrada */}
            <Route
              path="*"
              element={
                <div className="flex flex-col items-center justify-center min-h-screen text-center">
                  <h1 className="text-7xl m-0 text-primary">404</h1>
                  <h2 className="text-2xl mt-4 text-neutral-700">Página não encontrada</h2>
                  <p className="text-base mt-2 text-neutral-600">
                    A página que você está procurando não existe.
                  </p>
                  <a
                    href="/admissao"
                    className="mt-6 px-6 py-3 bg-primary text-white no-underline rounded-lg font-semibold hover:bg-primary-dark transition-colors"
                  >
                    Voltar para Admissão
                  </a>
                </div>
              }
            />
          </Routes>
          </div>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
