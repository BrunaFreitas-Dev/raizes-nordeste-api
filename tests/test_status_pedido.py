
from decimal import Decimal

from app.infrastructure.models import (
    Usuario,
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    UsuarioUnidade,
    Pedido,
)
from app.infrastructure.seguranca import gerar_hash_senha
from app.infrastructure import config

def criar_usuario_cliente(client, email="cliente@teste.com"):
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

def criar_atendente(db_session, email="atendente@teste.com"):
    atendente = Usuario(
        nome="Atendente Teste",
        email=email,
        senha_hash=gerar_hash_senha("Senha123"),
        perfil="ATENDENTE",
        ativo=True,
    )
    db_session.add(atendente)
    db_session.commit()
    db_session.refresh(atendente)

    return atendente

def obter_token_atendente(client, email="atendente@teste.com"):
    resposta = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": "Senha123",
        },
    )
    assert resposta.status_code == 200

    return resposta.json()["access_token"]

def preparar_pedido_pago(client, db_session, monkeypatch):
    monkeypatch.setattr(config.configuracoes, "modo_pagamento", "MOCK")

    token_cliente = criar_usuario_cliente(client)

    unidade = Unidade(
        nome="Unidade Teste",
        endereco="Rua Teste, 100",
        cidade="Recife",
        estado="PE",
        telefone="81999999999",
        regiao="NORDESTE",
        status="ATIVA",
    )
    db_session.add(unidade)
    db_session.flush()

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
        quantidade_total=10,
        quantidade_reservada=0,
    )
    db_session.add(estoque)
    db_session.commit()

    resposta_pedido = client.post(
        "/pedidos",
        headers={
            "Authorization": f"Bearer {token_cliente}",
            "Idempotency-Key": "criacao-status-teste",
        },
        json={
            "id_unidade": unidade.id_unidade,
            "canalPedido": "APP",
            "itens": [
                {
                    "id_produto_unidade": produto_unidade.id_produto_unidade,
                    "quantidade": 2,
                }
            ],
        },
    )
    assert resposta_pedido.status_code == 201

    id_pedido = resposta_pedido.json()["id_pedido"]

    resposta_pagamento = client.post(
        f"/pedidos/{id_pedido}/pagamento",
        headers={
            "Authorization": f"Bearer {token_cliente}",
            "Idempotency-Key": "pagamento-status-teste",
        },
        json={
            "forma_pagamento": "PIX",
            "resultado_simulado": "APROVADO",
        },
    )
    assert resposta_pagamento.status_code == 200

    return unidade, id_pedido

def vincular_atendente(db_session, atendente, unidade):
    vinculo = UsuarioUnidade(
        id_usuario=atendente.id_usuario,
        id_unidade=unidade.id_unidade,
        ativo=True,
    )
    db_session.add(vinculo)
    db_session.commit()

def test_atendente_vinculado_marca_pedido_como_pronto(
    client, db_session, monkeypatch
):
    unidade, id_pedido = preparar_pedido_pago(
        client, db_session, monkeypatch
    )

    atendente = criar_atendente(db_session)
    vincular_atendente(db_session, atendente, unidade)
    token = obter_token_atendente(client)

    resposta = client.patch(
        f"/pedidos/{id_pedido}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"observacao": "Pedido separado para retirada"},
    )

    assert resposta.status_code == 200

    pedido = db_session.get(Pedido, id_pedido)
    db_session.refresh(pedido)

    assert pedido.status_pedido == "PRONTO_PARA_RETIRADA"

def test_atendente_sem_vinculo_nao_atualiza_status(
    client, db_session, monkeypatch
):
    unidade, id_pedido = preparar_pedido_pago(
        client, db_session, monkeypatch
    )

    atendente = criar_atendente(db_session)
    token = obter_token_atendente(client)

    resposta = client.patch(
        f"/pedidos/{id_pedido}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Você não está vinculado a esta unidade"

def test_cliente_nao_pode_atualizar_status(
    client, db_session, monkeypatch
):
    _, id_pedido = preparar_pedido_pago(
        client, db_session, monkeypatch
    )

    token = criar_usuario_cliente(client, "cliente2@teste.com")

    resposta = client.patch(
        f"/pedidos/{id_pedido}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Somente atendentes podem atualizar este status"

def test_pedido_nao_pago_nao_pode_ficar_pronto(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(config.configuracoes, "modo_pagamento", "MOCK")

    token_cliente = criar_usuario_cliente(client)

    unidade = Unidade(
        nome="Unidade Teste",
        endereco="Rua Teste, 100",
        cidade="Recife",
        estado="PE",
        telefone="81999999999",
        regiao="NORDESTE",
        status="ATIVA",
    )
    db_session.add(unidade)
    db_session.flush()

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

    db_session.add(
        Estoque(
            id_produto_unidade=produto_unidade.id_produto_unidade,
            quantidade_total=10,
            quantidade_reservada=0,
        )
    )
    db_session.commit()

    resposta_pedido = client.post(
        "/pedidos",
        headers={
            "Authorization": f"Bearer {token_cliente}",
            "Idempotency-Key": "pedido-nao-pago-status",
        },
        json={
            "id_unidade": unidade.id_unidade,
            "canalPedido": "APP",
            "itens": [
                {
                    "id_produto_unidade": produto_unidade.id_produto_unidade,
                    "quantidade": 2,
                }
            ],
        },
    )
    assert resposta_pedido.status_code == 201

    id_pedido = resposta_pedido.json()["id_pedido"]

    atendente = criar_atendente(db_session)
    vincular_atendente(db_session, atendente, unidade)
    token_atendente = obter_token_atendente(client)

    resposta = client.patch(
        f"/pedidos/{id_pedido}/status",
        headers={"Authorization": f"Bearer {token_atendente}"},
        json={},
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == (
        "Somente pedidos pagos podem ficar prontos para retirada"
    )

def test_atualizar_status_de_pedido_inexistente(
    client, db_session
):
    atendente = criar_atendente(db_session)
    token = obter_token_atendente(client)

    resposta = client.patch(
        "/pedidos/9999/status",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    assert resposta.status_code == 404

def test_atualizar_status_sem_token(client):
    resposta = client.patch(
        "/pedidos/1/status",
        json={},
    )

    assert resposta.status_code == 401