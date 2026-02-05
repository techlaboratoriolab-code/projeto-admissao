export const DEPARTMENTS: string[] = [
  'Administração',
  'Financeiro',
  'TI',
  'Recursos Humanos',
  'Comercial',
  'Operações',
  'Atendimento',
];

export const USER_ROLES = {
  ADMIN: 'admin',
  SUPERVISOR: 'supervisor',
  USUARIO: 'usuario',
} as const;

export const hasPermission = (userRole: string, requiredRole: string): boolean => {
  const hierarchy = {
    admin: 3,
    supervisor: 2,
    usuario: 1,
  };

  return (hierarchy[userRole as keyof typeof hierarchy] || 0) >= 
         (hierarchy[requiredRole as keyof typeof hierarchy] || 0);
};
