export const DEPARTMENTS = [
  { id: 'Administração', name: 'Administração' },
  { id: 'Financeiro', name: 'Financeiro' },
  { id: 'TI', name: 'TI' },
  { id: 'Recursos Humanos', name: 'Recursos Humanos' },
  { id: 'Comercial', name: 'Comercial' },
  { id: 'Operações', name: 'Operações' },
  { id: 'Atendimento', name: 'Atendimento' },
] as const;

export type DepartmentId = typeof DEPARTMENTS[number]['id'];

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
