Raízes do Nordeste — API Back-end

API REST desenvolvida em Python com FastAPI para gerenciamento de unidades, produtos, estoque, pedidos e pagamentos simulados da rede Raízes do Nordeste.

1. Tecnologias utilizadas

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Alembic
- Pydantic
- JWT (PyJWT)
- bcrypt
- pytest
- Uvicorn

As dependências e versões estão especificadas em `requirements.txt`.

 2. Requisitos

- Python instalado.
- Git instalado.
- Terminal PowerShell ou equivalente.

3. Clonar o repositório

```bash
git clone https://github.com/BrunaFreitas-Dev/raizes-nordeste-api.git
cd raizes-nordeste-api
```

 4. Criar e ativar o ambiente virtual

No Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

5. Instalar as dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

6. Configurar as variáveis de ambiente

Crie uma cópia do arquivo `.env.example` com o nome `.env`.

No PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure as variáveis:

```env
DATABASE_URL=sqlite:///./raizes.db
SECRET_KEY=SUBSTITUA_POR_UMA_CHAVE_SEGURA
ACCESS_TOKEN_EXPIRE_MINUTES=60
MODO_PAGAMENTO=MOCK
```

Descrição:

| Variável | Finalidade |
|---|---|
| DATABASE_URL | Endereço de conexão com o banco de dados |
| SECRET_KEY | Chave secreta utilizada na autenticação |
| ACCESS_TOKEN_EXPIRE_MINUTES | Tempo de validade do token em minutos |
| MODO_PAGAMENTO | Modo de processamento do pagamento |

A chave secreta deve ser substituída por um valor seguro. Não compartilhe o arquivo `.env`.

 7. Criar e atualizar o banco de dados

Execute as migrações:

```powershell
python -m alembic upgrade head
```

8. Popular o banco com dados iniciais

Execute:

```powershell
python -m app.infrastructure.seed
```

O seed cadastra os dados iniciais, incluindo unidades, produtos, vínculos entre produtos e unidades, estoques e usuários de teste.

O seed verifica registros existentes antes de inserir novos dados.

Usuários de teste

A senha inicial dos usuários criados pelo seed é:

`Senha@123`

| Perfil | E-mail |
|---|---|
| Administrador | admin@raizes.com |
| Gerente | gerente@raizes.com |
| Atendente | atendente@raizes.com |
| Cliente | cliente@raizes.com |
| Técnico | totem@raizes.com |

Os usuários são destinados aos testes dos diferentes perfis e permissões da API.

9. Executar a aplicação

Inicie o servidor:

```powershell
uvicorn main:app --reload
```

A API ficará disponível em:

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

O endpoint raiz pode ser acessado em `GET /`.

10. Principais grupos de endpoints

| Grupo | Prefixo | Funcionalidade |
|---|---|---|
| Autenticação | `/auth` | Cadastro, login e consulta do usuário autenticado |
| Unidades | `/unidades` | Consulta de unidades |
| Estoque | `/estoque` | Consulta e entrada de estoque |
| Pedidos | `/pedidos` | Criação, consulta, pagamento, cancelamento e atualização de status |

A documentação interativa do Swagger apresenta os métodos, parâmetros, schemas e respostas disponíveis.

11. Autenticação

A autenticação utiliza JWT (JSON Web Token).

Para realizar login, utilize `POST /auth/login` com os campos de formulário:

- `username`: e-mail do usuário.
- `password`: senha.

A resposta fornece o token de acesso.

No Swagger, clique em **Authorize** e informe as credenciais conforme o mecanismo OAuth2 configurado.

Os endpoints protegidos exigem autenticação e respeitam as permissões de cada perfil.

12. Pagamentos

O projeto utiliza pagamento simulado (`MOCK`), sem integração com instituições financeiras ou processamento de transações reais.

O fluxo permite simular resultados de pagamento aprovado ou recusado, além de registrar tentativas e atualizar o status do pedido conforme as regras implementadas.

13. Executar os testes automatizados

Com o ambiente virtual ativado, execute:

```powershell
python -m pytest tests -v
```

Os testes automatizados verificam funcionalidades como:

- Inicialização da API.
- Cadastro e autenticação.
- Login e permissões.
- Consulta de unidades.
- Entrada e consulta de estoque.
- Criação e consulta de pedidos.
- Pagamento aprovado e recusado.
- Cancelamento de pedidos.
- Atualização de status.
- Regras de acesso e validações.

14. Estrutura do projeto

```text
raizes-nordeste-api/
│
├── alembic/
│   └── versions/
│
├── app/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
│
├── tests/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── main.py
├── requirements.txt
└── README.md
```

A aplicação está organizada em camadas:

- **API:** rotas, dependências e schemas.
- **Application:** serviços e regras de aplicação.
- **Domain:** enums e conceitos do domínio.
- **Infrastructure:** banco de dados, modelos, autenticação e seed.

15. Repositório

GitHub:

https://github.com/BrunaFreitas-Dev/raizes-nordeste-api

16. Observações

- O banco SQLite é criado localmente conforme a configuração de conexão.
- O arquivo `.env` não deve ser enviado ao repositório.
- Arquivos de banco de dados locais (`*.db`) são ignorados pelo Git.
- Os pagamentos são simulados e não representam transações financeiras reais.
- Para consultar os contratos atualizados dos endpoints, utilize o Swagger da aplicação.