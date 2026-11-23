
from decimal import Decimal

from app.infrastructure.models import (
    Usuario,
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    UsuarioUnidade,
)
from app.infrastructure.seguranca import gerar_hash_senha


def criar_cliente(client, email="cliente@teste.com"):
    resposta = client.post(
        "/auth/cadastro",
        json={
            "nome": "Cliente Teste",
            "email": email,
            "senha": "Senha123",
        },
    )
    assert resposta.status_code == 201

    login = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "Senha123",
        },
    )
    assert login.status_code == 200

    return login.json()["access_token"]


def criar_usuario(db_session, perfil, email):
    usuario = Usuario(
        nome="Usuario Teste",
        email=email,
        senha_hash=gerar_hash_senha("Senha123"),
        perfil=perfil,
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


def criar_unidade(db_session, nome="Unidade Teste"):
    unidade = Unidade(
        nome=nome,
        endereco="Rua Teste, 100",
        cidade="Recife",
        estado="PE",
        telefone="81999999999",
        regiao="NORDESTE",
        status="ATIVA",
    )
    db_session.add(unidade)
    db_session.flush()

    return unidade


def criar_produto_com_estoque(db_session, unidade):
    produto = Produto(
        nome="Cuscuz",
        descricao="Cuscuz tradicional",
        categoria="ALIMENTOS",
        status="ATIVO",
    )
    db_session.add(produto)
    db_session.flush()

    produto_unidade = ProdutoUnidade(
        id_unidade=unidade.id_unidade,
        id_produto=produto.id_produto,
        preco=Decimal("12.50"),
        disponivel=True,
    )
    db_session.add(produto_unidade)
    db_session.flush()

    estoque = Estoque(
        id_produto_unidade=produto_unidade.id_produto_unidade,
        quantidade_total=20,
        quantidade_reservada=0,
    )
    db_session.add(estoque)
    db_session.commit()

    return produto_unidade


def criar_pedido(client, token, id_unidade, id_produto_unidade, chave):
    resposta = client.post(
        "/pedidos",
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": chave,
        },
        json={
            "id_unidade": id_unidade,
            "canalPedido": "APP",
            "itens": [
                {
                    "id_produto_unidade": id_produto_unidade,
                    "quantidade": 2,
                }
            ],
        },
    )
    assert resposta.status_code == 201

    return resposta.json()["id_pedido"]


def vincular_atendente(db_session, usuario, unidade):
    vinculo = UsuarioUnidade(
        id_usuario=usuario.id_usuario,
        id_unidade=unidade.id_unidade,
        ativo=True,
    )
    db_session.add(vinculo)
    db_session.commit()


def preparar_ambiente(client, db_session):
    token_cliente = criar_cliente(client)

    unidade = criar_unidade(db_session)
    produto_unidade = criar_produto_com_estoque(db_session, unidade)

    id_pedido = criar_pedido(
        client,
        token_cliente,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        "pedido-consulta-1",
    )

    return token_cliente, unidade, produto_unidade, id_pedido


def test_cliente_lista_seus_pedidos(client, db_session):
    token, _, _, id_pedido = preparar_ambiente(client, db_session)

    resposta = client.get(
        "/pedidos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["id_pedido"] == id_pedido
    assert resposta.json()[0]["status_pedido"] == "AGUARDANDO_PAGAMENTO"


def test_cliente_consulta_detalhes_do_proprio_pedido(client, db_session):
    token, _, produto_unidade, id_pedido = preparar_ambiente(
        client, db_session
    )

    resposta = client.get(
        f"/pedidos/{id_pedido}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["id_pedido"] == id_pedido
    assert dados["canal_pedido"] == "APP"
    assert dados["status_pedido"] == "AGUARDANDO_PAGAMENTO"
    assert dados["valor_total"] == "25.00"
    assert len(dados["itens"]) == 1
    assert dados["itens"][0]["id_produto_unidade"] == (
        produto_unidade.id_produto_unidade
    )
    assert dados["itens"][0]["quantidade"] == 2
    assert dados["itens"][0]["preco_unitario"] == "12.50"
    assert dados["itens"][0]["subtotal"] == "25.00"


def test_cliente_nao_consulta_pedido_de_outro_cliente(
    client, db_session
):
    token_cliente, _, _, id_pedido = preparar_ambiente(
        client, db_session
    )

    criar_cliente(client, "outro@teste.com")
    token_outro = obter_token(client, "outro@teste.com")

    resposta = client.get(
        f"/pedidos/{id_pedido}",
        headers={"Authorization": f"Bearer {token_outro}"},
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Pedido não encontrado"


def test_cliente_lista_apenas_seus_pedidos(
    client, db_session
):
    token_cliente, unidade, produto_unidade, id_pedido = preparar_ambiente(
        client, db_session
    )

    criar_cliente(client, "outro@teste.com")
    token_outro = obter_token(client, "outro@teste.com")

    criar_pedido(
        client,
        token_outro,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        "pedido-consulta-2",
    )

    resposta = client.get(
        "/pedidos",
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["id_pedido"] == id_pedido


def test_atendente_lista_pedidos_da_unidade_vinculada(
    client, db_session
):
    token_cliente, unidade, _, id_pedido = preparar_ambiente(
        client, db_session
    )

    atendente = criar_usuario(
        db_session,
        "ATENDENTE",
        "atendente@teste.com",
    )
    vincular_atendente(db_session, atendente, unidade)
    token_atendente = obter_token(client, "atendente@teste.com")

    resposta = client.get(
        "/pedidos",
        headers={"Authorization": f"Bearer {token_atendente}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["id_pedido"] == id_pedido


def test_atendente_sem_vinculo_nao_lista_pedidos(
    client, db_session
):
    preparar_ambiente(client, db_session)

    criar_usuario(
        db_session,
        "ATENDENTE",
        "atendente@teste.com",
    )
    token = obter_token(client, "atendente@teste.com")

    resposta = client.get(
        "/pedidos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Atendente não possui vínculo ativo com nenhuma unidade"
    )


def test_atendente_nao_consulta_pedido_de_unidade_sem_vinculo(
    client, db_session
):
    _, _, _, id_pedido = preparar_ambiente(client, db_session)

    outra_unidade = criar_unidade(db_session, "Outra Unidade")

    atendente = criar_usuario(
        db_session,
        "ATENDENTE",
        "atendente@teste.com",
    )
    vincular_atendente(db_session, atendente, outra_unidade)
    token = obter_token(client, "atendente@teste.com")

    resposta = client.get(
        f"/pedidos/{id_pedido}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Pedido não encontrado"


def test_gerente_nao_pode_listar_pedidos(client, db_session):
    preparar_ambiente(client, db_session)

    criar_usuario(
        db_session,
        "GERENTE",
        "gerente@teste.com",
    )
    token = obter_token(client, "gerente@teste.com")

    resposta = client.get(
        "/pedidos",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Usuário sem permissão para listar pedidos"
    )


def test_administrador_nao_pode_consultar_pedido(
    client, db_session
):
    _, _, _, id_pedido = preparar_ambiente(client, db_session)

    criar_usuario(
        db_session,
        "ADMINISTRADOR",
        "admin@teste.com",
    )
    token = obter_token(client, "admin@teste.com")

    resposta = client.get(
        f"/pedidos/{id_pedido}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Usuário sem permissão para consultar pedidos"
    )


def test_consultar_pedido_inexistente(client, db_session):
    token = criar_cliente(client)

    resposta = client.get(
        "/pedidos/9999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Pedido não encontrado"


def test_listar_pedidos_sem_token(client):
    resposta = client.get("/pedidos")

    assert resposta.status_code == 401


def test_consultar_pedido_sem_token(client):
    resposta = client.get("/pedidos/1")

    assert resposta.status_code == 401


def test_filtrar_pedidos_por_canal(client, db_session):
    token, _, _, _ = preparar_ambiente(client, db_session)

    resposta = client.get(
        "/pedidos?canalPedido=APP",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["canal_pedido"] == "APP"


def test_filtrar_pedidos_por_status(client, db_session):
    token, _, _, _ = preparar_ambiente(client, db_session)

    resposta = client.get(
        "/pedidos?status=AGUARDANDO_PAGAMENTO",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["status_pedido"] == "AGUARDANDO_PAGAMENTO"


def test_filtrar_pedidos_por_unidade(client, db_session):
    token, unidade, _, _ = preparar_ambiente(client, db_session)

    resposta = client.get(
        f"/pedidos?id_unidade={unidade.id_unidade}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_paginacao_da_listagem_de_pedidos(client, db_session):
    token, unidade, produto_unidade, primeiro_id = preparar_ambiente(
        client, db_session
    )

    criar_pedido(
        client,
        token,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        "pedido-paginacao-2",
    )

    resposta = client.get(
        "/pedidos?page=1&limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["id_pedido"] != primeiro_id


def test_pagina_invalida_retorna_422(client, db_session):
    token, _, _, _ = preparar_ambiente(client, db_session)

    resposta = client.get(
        "/pedidos?page=0",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 422


def test_limite_acima_do_maximo_retorna_422(client, db_session):
    token, _, _, _ = preparar_ambiente(client, db_session)

    resposta = client.get(
        "/pedidos?limit=51",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 422
