# Contribuindo para o Sistema de Automação de Admissão

Obrigado por considerar contribuir com este projeto! Este documento fornece diretrizes para contribuições.

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Contribuir](#como-contribuir)
- [Padrões de Código](#padrões-de-código)
- [Processo de Pull Request](#processo-de-pull-request)
- [Reportando Bugs](#reportando-bugs)
- [Sugerindo Melhorias](#sugerindo-melhorias)

---

## 🤝 Código de Conduta

Este projeto adere a um código de conduta. Ao participar, você concorda em manter um ambiente respeitoso e inclusivo.

### Nossos Valores

- **Respeito**: Trate todos com respeito e profissionalismo
- **Colaboração**: Trabalhe em conjunto para melhorar o projeto
- **Transparência**: Comunique-se de forma clara e honesta
- **Qualidade**: Mantenha altos padrões de código e documentação

---

## 🚀 Como Contribuir

### 1. Fork o Repositório

```bash
# Clone seu fork
git clone https://github.com/seu-usuario/automacao-admissao.git
cd automacao-admissao

# Adicione o repositório original como upstream
git remote add upstream https://github.com/original/automacao-admissao.git
```

### 2. Crie uma Branch

Use nomes descritivos para suas branches:

```bash
# Para novas funcionalidades
git checkout -b feature/nome-da-funcionalidade

# Para correções de bugs
git checkout -b fix/descricao-do-bug

# Para melhorias de documentação
git checkout -b docs/descricao-da-melhoria

# Para refatorações
git checkout -b refactor/descricao
```

### 3. Faça suas Alterações

- Escreva código limpo e legível
- Adicione comentários quando necessário
- Siga os padrões de código do projeto
- Teste suas alterações

### 4. Commit suas Mudanças

Use mensagens de commit claras e descritivas:

```bash
# Formato: tipo(escopo): descrição

git commit -m "feat(api): adiciona endpoint de busca por nome"
git commit -m "fix(auth): corrige validação de token expirado"
git commit -m "docs(readme): atualiza instruções de instalação"
git commit -m "refactor(components): simplifica lógica do PatientCard"
```

**Tipos de commit:**
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Mudanças na documentação
- `style`: Formatação, ponto e vírgula, etc (sem mudança de código)
- `refactor`: Refatoração de código
- `test`: Adição ou correção de testes
- `chore`: Atualizações de build, configurações, etc

### 5. Push para seu Fork

```bash
git push origin feature/nome-da-funcionalidade
```

### 6. Abra um Pull Request

- Vá para o repositório original no GitHub
- Clique em "New Pull Request"
- Selecione sua branch
- Preencha o template de PR

---

## 💻 Padrões de Código

### Python (Backend)

#### Estilo
- Siga o [PEP 8](https://pep8.org/)
- Use 4 espaços para indentação
- Máximo 88 caracteres por linha (Black formatter)

#### Exemplo:
```python
def buscar_paciente_por_cpf(cpf: str) -> dict:
    """
    Busca paciente no banco de dados pelo CPF.
    
    Args:
        cpf: CPF do paciente (apenas números)
        
    Returns:
        Dicionário com dados do paciente
        
    Raises:
        ValueError: Se CPF inválido
        NotFoundError: Se paciente não encontrado
    """
    if not validar_cpf(cpf):
        raise ValueError("CPF inválido")
    
    paciente = database.query(f"SELECT * FROM pacientes WHERE cpf = '{cpf}'")
    
    if not paciente:
        raise NotFoundError("Paciente não encontrado")
    
    return paciente
```

#### Ferramentas Recomendadas:
- **Black**: Formatação automática
- **Flake8**: Linting
- **isort**: Organização de imports
- **mypy**: Type checking (opcional)

### JavaScript/React (Frontend)

#### Estilo
- Use 2 espaços para indentação
- Use aspas simples para strings
- Ponto e vírgula opcional (mas seja consistente)

#### Exemplo:
```javascript
// Componente funcional com hooks
import React, { useState, useEffect } from 'react';

const PatientCard = ({ patient, onSelect }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // Efeito colateral
    console.log('Patient loaded:', patient.name);
  }, [patient]);

  const handleClick = () => {
    setIsExpanded(!isExpanded);
    onSelect(patient);
  };

  return (
    <div className="patient-card" onClick={handleClick}>
      <h3>{patient.name}</h3>
      {isExpanded && (
        <div className="patient-details">
          <p>CPF: {patient.cpf}</p>
          <p>Data Nascimento: {patient.birthDate}</p>
        </div>
      )}
    </div>
  );
};

export default PatientCard;
```

#### Convenções:
- **Componentes**: PascalCase (`PatientCard.jsx`)
- **Funções**: camelCase (`handleClick`)
- **Constantes**: UPPER_SNAKE_CASE (`API_URL`)
- **Arquivos**: kebab-case ou PascalCase

#### Ferramentas Recomendadas:
- **ESLint**: Linting
- **Prettier**: Formatação automática

### CSS/Tailwind

- Use classes do Tailwind sempre que possível
- Evite CSS inline, exceto para estilos dinâmicos
- Organize classes: layout → tipografia → cores → outros

```jsx
// Bom
<div className="flex flex-col p-4 bg-white rounded-lg shadow-md">
  <h2 className="text-xl font-bold text-gray-800">Título</h2>
  <p className="text-sm text-gray-600">Descrição</p>
</div>

// Evite
<div style={{ display: 'flex', padding: '16px', backgroundColor: 'white' }}>
  <h2 style={{ fontSize: '20px', fontWeight: 'bold' }}>Título</h2>
</div>
```

---

## 🔄 Processo de Pull Request

### Antes de Submeter

- [ ] Código está funcionando e testado
- [ ] Testes passam (se aplicável)
- [ ] Documentação atualizada
- [ ] Código segue os padrões do projeto
- [ ] Commits estão bem organizados
- [ ] Branch está atualizada com main

### Template de Pull Request

```markdown
## Descrição
Breve descrição das mudanças realizadas.

## Tipo de Mudança
- [ ] Bug fix (correção que resolve um problema)
- [ ] Nova funcionalidade (mudança que adiciona funcionalidade)
- [ ] Breaking change (correção ou funcionalidade que causa quebra)
- [ ] Documentação
- [ ] Refatoração

## Como Testar
1. Passo 1
2. Passo 2
3. Resultado esperado

## Checklist
- [ ] Meu código segue os padrões do projeto
- [ ] Fiz uma auto-revisão do meu código
- [ ] Comentei áreas difíceis de entender
- [ ] Atualizei a documentação
- [ ] Minhas mudanças não geram novos warnings
- [ ] Adicionei testes que provam que minha correção funciona
- [ ] Testes novos e existentes passam localmente

## Screenshots (se aplicável)
Adicione screenshots das mudanças visuais.

## Observações Adicionais
Qualquer informação adicional relevante.
```

### Processo de Revisão

1. **Revisor atribuído**: Um mantenedor será atribuído para revisar
2. **Feedback**: Responda aos comentários e faça ajustes necessários
3. **Aprovação**: Após aprovação, o PR será mergeado
4. **Merge**: Mantenedores farão o merge para a branch principal

---

## 🐛 Reportando Bugs

### Antes de Reportar

- Verifique se o bug já foi reportado nas [Issues](https://github.com/seu-repo/issues)
- Verifique se você está usando a versão mais recente
- Colete informações sobre o bug

### Template de Bug Report

```markdown
## Descrição do Bug
Descrição clara e concisa do que é o bug.

## Para Reproduzir
Passos para reproduzir o comportamento:
1. Vá para '...'
2. Clique em '....'
3. Role até '....'
4. Veja o erro

## Comportamento Esperado
Descrição clara do que deveria acontecer.

## Screenshots
Se aplicável, adicione screenshots para ajudar a explicar o problema.

## Ambiente
- OS: [ex: Windows 11]
- Browser: [ex: Chrome 120]
- Versão do Node: [ex: 18.0.0]
- Versão do Python: [ex: 3.11]

## Logs
Cole aqui logs relevantes:
```
[logs aqui]
```

## Contexto Adicional
Adicione qualquer outro contexto sobre o problema aqui.
```

---

## 💡 Sugerindo Melhorias

### Template de Feature Request

```markdown
## Problema Relacionado
Esta funcionalidade resolve algum problema? Descreva.

## Solução Proposta
Descrição clara da solução que você gostaria de ver.

## Alternativas Consideradas
Descrição de soluções alternativas que você considerou.

## Contexto Adicional
Adicione qualquer outro contexto ou screenshots sobre a feature.

## Benefícios
- Benefício 1
- Benefício 2

## Possíveis Desafios
- Desafio 1
- Desafio 2
```

---

## 🧪 Testes

### Backend (Python)

```bash
# Executar testes
cd backend
pytest

# Com coverage
pytest --cov=. --cov-report=html
```

### Frontend (React)

```bash
# Executar testes
npm test

# Com coverage
npm test -- --coverage
```

### Testes Manuais

1. Inicie o sistema: `iniciar_sistema.bat`
2. Teste as funcionalidades principais:
   - Login/Logout
   - Busca de pacientes
   - Visualização de documentos
   - Gerenciamento de usuários (admin)

---

## 📚 Recursos Úteis

### Documentação
- [README.md](README.md) - Visão geral do projeto
- [INSTALACAO.md](INSTALACAO.md) - Guia de instalação
- [API.md](API.md) - Documentação da API

### Ferramentas
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Supabase Docs](https://supabase.com/docs)

### Comunidade
- GitHub Issues
- Pull Requests
- Discussions

---

## ✅ Checklist do Contribuidor

Antes de submeter sua contribuição:

- [ ] Li e entendi o guia de contribuição
- [ ] Criei uma branch apropriada
- [ ] Meu código segue os padrões do projeto
- [ ] Adicionei/atualizei testes
- [ ] Todos os testes passam
- [ ] Atualizei a documentação
- [ ] Meus commits são claros e descritivos
- [ ] Abri um Pull Request com descrição completa

---

## 🙏 Agradecimentos

Obrigado por dedicar seu tempo para contribuir! Cada contribuição, por menor que seja, é valiosa para o projeto.

---

## 📞 Dúvidas?

Se tiver dúvidas sobre como contribuir:

1. Abra uma [Issue](https://github.com/seu-repo/issues) com a tag `question`
2. Entre em contato com os mantenedores
3. Participe das [Discussions](https://github.com/seu-repo/discussions)

---

**Happy Coding! 🚀**
