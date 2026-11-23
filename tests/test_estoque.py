
from app.infrastructure.models import (
    Usuario,
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    MovimentacaoEstoque,
)
from app.infrastructure.seguranca import gerar_hash_senha

def criar_usuario(db_session, perfil="GERENTE"):
    usuario = Usuario(
        nome="Usuario Teste",
        email=f"{perfil.lower()}@teste.com",
        senha_hash=gerar_hash_senha("Senha123"),
        perfil=perfil,
        usuario_tecnico=False,
        ativo=True,
    )

    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)

    return usuario

def obter_token(client, email):
    resposta = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "Senha123",
        },
    )

    assert resposta.status_code == 200

    return resposta.json()["access_token"]

def criar_estoque(db_session):
    unidade = Unidade(
        nome="Unidade Teste",
        endereco="Rua de Teste, 100",
        cidade="Recife",
        estado="PE",
        telefone="81999999999",
        regiao="NORDESTE",
        status="ATIVA",
    )

    db_session.add(unidade)
    db_session.commit()
    db_session.refresh(unidade)

    produto = Produto(
        nome="Bolo de Milho",
        descricao="Bolo tradicional",
        categoria="Bolos",
        status="ATIVO",
    )

    db_session.add(produto)
    db_session.commit()
    db_session.refresh(produto)

    produto_unidade = ProdutoUnidade(
        id_unidade=unidade.id_unidade,
        id_produto=produto.id_produto,
        preco=12.50,
        disponivel=True,
    )

    db_session.add(produto_unidade)
    db_session.commit()
    db_session.refresh(produto_unidade)

    estoque = Estoque(
        id_produto_unidade=produto_unidade.id_produto_unidade,
        quantidade_total=10,
        quantidade_reservada=2,
    )

    db_session.add(estoque)
    db_session.commit()
    db_session.refresh(estoque)

    return estoque

def test_registrar_entrada_estoque_com_sucesso(client, db_session):
    usuario = criar_usuario(db_session, "GERENTE")
    estoque = criar_estoque(db_session)

    token = obter_token(client, usuario.email)

    resposta = client.post(
        f"/estoque/{estoque.id_produto_unidade}/entrada",
        json={
            "quantidade": 5,
            "observacao": "Reposição de produtos",
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["quantidade_total"] == 15
    assert dados["quantidade_reservada"] == 2
    assert dados["mensagem"] == (
        "Entrada de estoque registrada com sucesso"
    )

    movimentacao = db_session.query(MovimentacaoEstoque).first()

    assert movimentacao is not None
    assert movimentacao.tipo_movimentacao == "ENTRADA"
    assert movimentacao.quantidade == 5
    assert movimentacao.id_usuario == usuario.id_usuario

def test_registrar_entrada_com_quantidade_zero(client, db_session):
    usuario = criar_usuario(db_session, "GERENTE")
    estoque = criar_estoque(db_session)

    token = obter_token(client, usuario.email)

    resposta = client.post(
        f"/estoque/{estoque.id_produto_unidade}/entrada",
        json={"quantidade": 0},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 422

def test_registrar_entrada_com_quantidade_negativa(client, db_session):
    usuario = criar_usuario(db_session, "GERENTE")
    estoque = criar_estoque(db_session)

    token = obter_token(client, usuario.email)

    resposta = client.post(
        f"/estoque/{estoque.id_produto_unidade}/entrada",
        json={"quantidade": -5},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 422

def test_registrar_entrada_em_estoque_inexistente(client, db_session):
    usuario = criar_usuario(db_session, "GERENTE")
    token = obter_token(client, usuario.email)

    resposta = client.post(
        "/estoque/9999/entrada",
        json={"quantidade": 5},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Estoque não encontrado"

def test_cliente_nao_pode_registrar_entrada(client, db_session):
    usuario = criar_usuario(db_session, "CLIENTE")
    estoque = criar_estoque(db_session)

    token = obter_token(client, usuario.email)

    resposta = client.post(
        f"/estoque/{estoque.id_produto_unidade}/entrada",
        json={"quantidade": 5},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 403

def test_atendente_nao_pode_registrar_entrada(client, db_session):
    usuario = criar_usuario(db_session, "ATENDENTE")
    estoque = criar_estoque(db_session)

    token = obter_token(client, usuario.email)

    resposta = client.post(
        f"/estoque/{estoque.id_produto_unidade}/entrada",
        json={"quantidade": 5},
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert resposta.status_code == 403

def test_registrar_entrada_sem_token(client, db_session):
    estoque = criar_estoque(db_session)

    resposta = client.post(
        f"/estoque/{estoque.id_produto_unidade}/entrada",
        json={"quantidade": 5},
    )

    assert resposta.status_code == 401