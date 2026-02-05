export type UserRole = 'admin' | 'supervisor' | 'usuario';

export type Department = 
  | 'Administração'
  | 'Financeiro'
  | 'TI'
  | 'Recursos Humanos'
  | 'Comercial'
  | 'Operações'
  | 'Atendimento';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  department?: Department;
  username?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Session {
  user: {
    id: string;
    email?: string;
    user_metadata?: {
      name?: string;
      username?: string;
      nome_completo?: string;
      telefone?: string;
      role?: UserRole;
      department?: Department;
    };
  };
  access_token: string;
  refresh_token: string;
}
