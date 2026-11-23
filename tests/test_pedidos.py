
from decimal import Decimal

from app.infrastructure.models import (
    Usuario,
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    ItemPedido,
    MovimentacaoEstoque,
    HistoricoStatusPedido,
    Auditoria,
    Pedido,
    UsuarioUnidade,
)
from app.infrastructure.seguranca import gerar_hash_senha


def criar_usuario(db_session, perfil="CLIENTE", usuario_tecnico=False):
    usuario = Usuario(
        nome="Usuario Teste",
        email=f"{perfil.lower()}{usuario_tecnico}@teste.com",
        senha_hash=gerar_hash_senha("Senha123"),
        perfil=perfil,
        usuario_tecnico=usuario_tecnico,
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


def criar_produto_com_estoque(db_session, quantidade=10):
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
        descricao="Bolo de milho tradicional",
        categoria="Bolos",
        status="ATIVO",
    )
    db_session.add(produto)
    db_session.commit()
    db_session.refresh(produto)

    produto_unidade = ProdutoUnidade(
        id_unidade=unidade.id_unidade,
        id_produto=produto.id_produto,
        preco=Decimal("12.50"),
        disponivel=True,
    )
    db_session.add(produto_unidade)
    db_session.commit()
    db_session.refresh(produto_unidade)

    estoque = Estoque(
        id_produto_unidade=produto_unidade.id_produto_unidade,
        quantidade_total=quantidade,
        quantidade_reservada=0,
    )
    db_session.add(estoque)
    db_session.commit()
    db_session.refresh(estoque)

    return unidade, produto_unidade, estoque


def criar_pedido(client, token, id_unidade, id_produto_unidade,
                 quantidade=2, chave="pedido-teste-001"):
    return client.post(
        "/pedidos",
        json={
            "id_unidade": id_unidade,
            "canalPedido": "APP",
            "itens": [
                {
                    "id_produto_unidade": id_produto_unidade,
                    "quantidade": quantidade,
                }
            ],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": chave,
        },
    )


def test_criar_pedido_com_sucesso(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)
    token = obter_token(client, usuario.email)

    resposta = criar_pedido(
        client,
        token,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert dados["id_unidade"] == unidade.id_unidade
    assert dados["canal_pedido"] == "APP"
    assert dados["status_pedido"] == "AGUARDANDO_PAGAMENTO"
    assert dados["valor_total"] == "25.00"
    assert dados["codigo_acompanhamento"]

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2

    item = db_session.query(ItemPedido).first()
    assert item is not None
    assert item.quantidade == 2
    assert item.preco_unitario == Decimal("12.50")
    assert item.subtotal == Decimal("25.00")

    movimentacao = db_session.query(MovimentacaoEstoque).first()
    assert movimentacao is not None
    assert movimentacao.tipo_movimentacao == "RESERVA"

    historico = db_session.query(HistoricoStatusPedido).first()
    assert historico.status_novo == "AGUARDANDO_PAGAMENTO"

    auditoria = db_session.query(Auditoria).first()
    assert auditoria.acao == "CRIACAO_PEDIDO"


def test_criar_pedido_com_chave_idempotencia_repetida(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)
    token = obter_token(client, usuario.email)

    primeira = criar_pedido(
        client, token, unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        chave="chave-repetida",
    )

    segunda = criar_pedido(
        client, token, unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        chave="chave-repetida",
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json()["detail"] == "Chave de idempotência já utilizada"

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2
    assert db_session.query(Pedido).count() == 1


def test_criar_pedido_sem_token(client, db_session):
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)

    resposta = client.post(
        "/pedidos",
        json={
            "id_unidade": unidade.id_unidade,
            "canalPedido": "APP",
            "itens": [
                {
                    "id_produto_unidade": produto_unidade.id_produto_unidade,
                    "quantidade": 1,
                }
            ],
        },
        headers={"Idempotency-Key": "sem-token"},
    )

    assert resposta.status_code == 401


def test_criar_pedido_sem_chave_idempotencia(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)
    token = obter_token(client, usuario.email)

    resposta = client.post(
        "/pedidos",
        json={
            "id_unidade": unidade.id_unidade,
            "canalPedido": "APP",
            "itens": [
                {
                    "id_produto_unidade": produto_unidade.id_produto_unidade,
                    "quantidade": 1,
                }
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 422


def test_cliente_nao_pode_criar_pedido_no_canal_balCAO(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)
    token = obter_token(client, usuario.email)

    resposta = client.post(
        "/pedidos",
        json={
            "id_unidade": unidade.id_unidade,
            "canalPedido": "BALCAO",
            "itens": [
                {
                    "id_produto_unidade": produto_unidade.id_produto_unidade,
                    "quantidade": 1,
                }
            ],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "canal-invalido",
        },
    )

    assert resposta.status_code == 403


def test_criar_pedido_com_unidade_inexistente(client, db_session):
    usuario = criar_usuario(db_session)
    token = obter_token(client, usuario.email)

    resposta = criar_pedido(
        client,
        token,
        9999,
        1,
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Unidade não encontrada ou inativa"


def test_criar_pedido_com_quantidade_zero(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)
    token = obter_token(client, usuario.email)

    resposta = criar_pedido(
        client,
        token,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        quantidade=0,
    )

    assert resposta.status_code == 422


def test_criar_pedido_com_estoque_insuficiente(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(
        db_session,
        quantidade=1,
    )
    token = obter_token(client, usuario.email)

    resposta = criar_pedido(
        client,
        token,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
        quantidade=2,
    )

    assert resposta.status_code == 409
    assert "Estoque insuficiente" in resposta.json()["detail"]

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 0


def test_criar_pedido_com_produto_indisponivel(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_produto_com_estoque(db_session)
    produto_unidade.disponivel = False
    db_session.commit()

    token = obter_token(client, usuario.email)

    resposta = criar_pedido(
        client,
        token,
        unidade.id_unidade,
        produto_unidade.id_produto_unidade,
    )

    assert resposta.status_code == 409
    assert "indisponível" in resposta.json()["detail"]
