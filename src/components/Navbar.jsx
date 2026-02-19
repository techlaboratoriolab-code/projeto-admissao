import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../contexts/ThemeContext';

const Navbar = () => {
  const { userProfile, signOut } = useAuth();
  const { isDarkMode, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const isAdmin = () => userProfile?.role === 'admin';

  const handleLogout = async () => {
    if (window.confirm('Deseja realmente sair do sistema?')) {
      await signOut();
      navigate('/login');
    }
  };

  return (
    <nav className="bg-white dark:bg-neutral-800 shadow-card sticky top-0 z-[100] transition-colors">
      <div className="max-w-[1400px] mx-auto px-8 py-4 flex justify-between items-center gap-8 max-md:flex-col max-md:gap-4">
        <div className="flex-shrink-0">
          <Link to="/admissao" className="flex items-center gap-3 no-underline text-neutral-700 dark:text-neutral-200 font-semibold text-lg transition-opacity hover:opacity-80">
            <img 
              src="/logo-horizontal.svg" 
              alt="Logo" 
              className="h-10 w-auto object-contain dark:brightness-0 dark:invert" 
            />
          </Link>
        </div>

        <div className="flex gap-6 flex-1 max-md:w-full max-md:gap-2 max-md:justify-center">
          <Link to="/admissao" className="no-underline text-neutral-600 dark:text-neutral-300 text-[15px] font-medium px-4 py-2 rounded-md transition-all hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:text-primary">
            Admissão
          </Link>

          {isAdmin() && (
            <Link to="/usuarios" className="no-underline text-neutral-600 dark:text-neutral-300 text-[15px] font-medium px-4 py-2 rounded-md transition-all hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:text-primary">
              Gerenciar Usuários
            </Link>
          )}
        </div>

        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="flex flex-col items-end gap-0.5 max-md:hidden">
            <span className="text-sm font-semibold text-neutral-700 dark:text-neutral-200">{userProfile?.name || userProfile?.username}</span>
            <span className="text-xs text-neutral-500 dark:text-neutral-400 capitalize">{userProfile?.role === 'admin' ? 'Administrador' : userProfile?.role === 'supervisor' ? 'Supervisor' : 'Usuário'}</span>
          </div>
          
          <button
            onClick={toggleTheme}
            className="p-2 rounded-md bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 border-0 cursor-pointer transition-all hover:bg-neutral-200 dark:hover:bg-neutral-600"
            title={isDarkMode ? 'Modo Claro' : 'Modo Escuro'}
          >
            {isDarkMode ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5"/>
                <line x1="12" y1="1" x2="12" y2="3"/>
                <line x1="12" y1="21" x2="12" y2="23"/>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                <line x1="1" y1="12" x2="3" y2="12"/>
                <line x1="21" y1="12" x2="23" y2="12"/>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>
          
          <button
            className="px-4 py-2 bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 border-0 rounded-md text-sm font-semibold cursor-pointer transition-all hover:bg-neutral-300 dark:hover:bg-neutral-600 hover:text-neutral-700 dark:hover:text-neutral-200"
            onClick={handleLogout}
          >
            Sair
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
