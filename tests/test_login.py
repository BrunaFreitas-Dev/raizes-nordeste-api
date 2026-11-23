
def criar_cliente(client):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "Cliente Teste",
            "email": "cliente@teste.com",
            "senha": "Senha123"
        }
    )

    assert resposta.status_code == 201


def obter_token(client):
    resposta = client.post(
        "/auth/login",
        data={
            "username": "cliente@teste.com",
            "password": "Senha123"
        }
    )

    assert resposta.status_code == 200

    return resposta.json()["access_token"]


def test_login_com_credenciais_corretas(client):
    criar_cliente(client)

    resposta = client.post(
        "/auth/login",
        data={
            "username": "cliente@teste.com",
            "password": "Senha123"
        }
    )

    assert resposta.status_code == 200
    assert "access_token" in resposta.json()
    assert resposta.json()["token_type"] == "bearer"


def test_login_com_senha_incorreta(client):
    criar_cliente(client)

    resposta = client.post(
        "/auth/login",
        data={
            "username": "cliente@teste.com",
            "password": "SenhaErrada"
        }
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "credenciais inválidas"


def test_login_com_email_inexistente(client):
    resposta = client.post(
        "/auth/login",
        data={
            "username": "inexistente@teste.com",
            "password": "Senha123"
        }
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "credenciais inválidas"


def test_consultar_usuario_com_token_valido(client):
    criar_cliente(client)
    token = obter_token(client)

    resposta = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert resposta.status_code == 200
    assert resposta.json()["email"] == "cliente@teste.com"
    assert resposta.json()["perfil"] == "CLIENTE"


def test_consultar_usuario_sem_token(client):
    resposta = client.get("/auth/me")

    assert resposta.status_code == 401


def test_consultar_usuario_com_token_invalido(client):
    resposta = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer token_invalido"
        }
    )

    assert resposta.status_code == 401
