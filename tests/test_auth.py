
def test_cadastrar_usuario_com_sucesso(client):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "Cliente Teste",
            "email": "cliente@teste.com",
            "senha": "Senha123"
        }
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["nome"] == "Cliente Teste"
    assert dados["email"] == "cliente@teste.com"
    assert dados["perfil"] == "CLIENTE"
    assert dados["ativo"] is True
    assert "senha" not in dados
    assert "senha_hash" not in dados


def test_cadastrar_usuario_com_email_duplicado(client):
    dados = {
        "nome": "Cliente Teste",
        "email": "cliente@teste.com",
        "senha": "Senha123"
    }

    primeira_resposta = client.post(
        "/auth/cadastro",
        json=dados
    )

    segunda_resposta = client.post(
        "/auth/cadastro",
        json=dados
    )

    assert primeira_resposta.status_code == 201
    assert segunda_resposta.status_code == 409
    assert segunda_resposta.json()["detail"] == "E-mail já cadastrado"


def test_cadastrar_usuario_com_nome_invalido(client):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "A",
            "email": "cliente@teste.com",
            "senha": "Senha123"
        }
    )

    assert resposta.status_code == 422


def test_cadastrar_usuario_com_email_invalido(client):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "Cliente Teste",
            "email": "email-invalido",
            "senha": "Senha123"
        }
    )

    assert resposta.status_code == 422


def test_cadastrar_usuario_com_senha_curta(client):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "Cliente Teste",
            "email": "cliente@teste.com",
            "senha": "123"
        }
    )

    assert resposta.status_code == 422


def test_cadastrar_usuario_sem_campos_obrigatorios(client):
    resposta = client.post(
        "/auth/cadastro",
        json={}
    )

    assert resposta.status_code == 422


def test_cadastrar_usuario_com_campo_extra(client):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "Cliente Teste",
            "email": "cliente@teste.com",
            "senha": "Senha123",
            "perfil": "ADMINISTRADOR"
        }
    )

    assert resposta.status_code == 422
