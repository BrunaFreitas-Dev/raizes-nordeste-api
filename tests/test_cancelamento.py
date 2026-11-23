
from decimal import Decimal

from app.infrastructure.models import (
    Usuario,
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    Pedido,
    MovimentacaoEstoque,
    HistoricoStatusPedido,
    Auditoria,
    UsuarioUnidade,
)
from app.infrastructure.seguranca import gerar_hash_senha


def criar_usuario(db_session, perfil="CLIENTE", email="cliente@teste.com"):
    usuario = Usuario(
        nome="Usuario Teste",
        email=email,
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
        data={"username": email, "password": "Senha123"},
    )
    assert resposta.status_code == 200
    return resposta.json()["access_token"]


def criar_estrutura(db_session):
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
        preco=Decimal("12.50"),
        disponivel=True,
    )
    db_session.add(produto_unidade)
    db_session.commit()
    db_session.refresh(produto_unidade)

    estoque = Estoque(
        id_produto_unidade=produto_unidade.id_produto_unidade,
        quantidade_total=10,
        quantidade_reservada=0,
    )
    db_session.add(estoque)
    db_session.commit()
    db_session.refresh(estoque)

    return unidade, produto_unidade, estoque


def criar_pedido(client, token, unidade, produto_unidade, chave):
    resposta = client.post(
        "/pedidos",
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
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": chave,
        },
    )
    assert resposta.status_code == 201
    return resposta.json()


def cancelar(client, token, id_pedido, motivo="Desistência do cliente"):
    return client.post(
        f"/pedidos/{id_pedido}/cancelar",
        json={"motivo": motivo},
        headers={"Authorization": f"Bearer {token}"},
    )


def preparar_pedido(client, db_session):
    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_estrutura(db_session)
    token = obter_token(client, usuario.email)

    pedido = criar_pedido(
        client,
        token,
        unidade,
        produto_unidade,
        "pedido-cancelamento",
    )

    return usuario, token, unidade, pedido, estoque


def test_cliente_cancela_proprio_pedido(client, db_session):
    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    resposta = cancelar(client, token, pedido["id_pedido"])

    assert resposta.status_code == 200
    dados = resposta.json()

    assert dados["status_pedido"] == "CANCELADO"
    assert dados["motivo_cancelamento"] == "Desistência do cliente"
    assert dados["mensagem"] == (
        "Pedido cancelado e estoque liberado com sucesso"
    )

    db_session.refresh(estoque)
    assert estoque.quantidade_total == 10
    assert estoque.quantidade_reservada == 0

    movimentacao = db_session.query(MovimentacaoEstoque).filter(
        MovimentacaoEstoque.id_pedido == pedido["id_pedido"],
        MovimentacaoEstoque.tipo_movimentacao == "LIBERACAO",
    ).first()
    assert movimentacao is not None
    assert movimentacao.quantidade == 2

    historico = db_session.query(HistoricoStatusPedido).filter(
        HistoricoStatusPedido.id_pedido == pedido["id_pedido"]
    ).order_by(HistoricoStatusPedido.id_historico.desc()).first()
    assert historico.status_anterior == "AGUARDANDO_PAGAMENTO"
    assert historico.status_novo == "CANCELADO"

    auditoria = db_session.query(Auditoria).filter(
        Auditoria.id_pedido == pedido["id_pedido"]
    ).order_by(Auditoria.id_auditoria.desc()).first()
    assert auditoria.acao == "CANCELAMENTO_MANUAL"


def test_cliente_nao_cancela_pedido_de_outro_cliente(client, db_session):
    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    outro_usuario = criar_usuario(
        db_session,
        email="outro@teste.com",
    )
    outro_token = obter_token(client, outro_usuario.email)

    resposta = cancelar(client, outro_token, pedido["id_pedido"])

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Você não pode cancelar este pedido"
    )

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2


def test_cancelar_pedido_inexistente(client, db_session):
    usuario = criar_usuario(db_session)
    token = obter_token(client, usuario.email)

    resposta = cancelar(client, token, 9999)

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Pedido não encontrado"


def test_cancelar_pedido_sem_token(client, db_session):
    resposta = client.post(
        "/pedidos/1/cancelar",
        json={"motivo": "Desistência do cliente"},
    )

    assert resposta.status_code == 401


def test_cliente_nao_cancela_pedido_pago(client, db_session, monkeypatch):
    from app.infrastructure.config import configuracoes

    monkeypatch.setattr(configuracoes, "modo_pagamento", "MOCK")

    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    pagamento = client.post(
        f"/pedidos/{pedido['id_pedido']}/pagamento",
        json={
            "forma_pagamento": "PIX",
            "resultado_simulado": "APROVADO",
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "pagamento-antes-cancelamento",
        },
    )
    assert pagamento.status_code == 200

    resposta = cancelar(client, token, pedido["id_pedido"])

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == (
        "Este pedido não pode ser cancelado neste status"
    )

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2


def test_atendente_sem_vinculo_nao_cancela_pedido(client, db_session):
    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    atendente = criar_usuario(
        db_session,
        perfil="ATENDENTE",
        email="atendente@teste.com",
    )
    token_atendente = obter_token(client, atendente.email)

    resposta = cancelar(
        client,
        token_atendente,
        pedido["id_pedido"],
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Você não está vinculado a esta unidade"
    )


def test_atendente_vinculado_cancela_pedido(client, db_session):
    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    atendente = criar_usuario(
        db_session,
        perfil="ATENDENTE",
        email="atendente-vinculado@teste.com",
    )

    vinculo = UsuarioUnidade(
        id_usuario=atendente.id_usuario,
        id_unidade=unidade.id_unidade,
        ativo=True,
    )
    db_session.add(vinculo)
    db_session.commit()

    token_atendente = obter_token(client, atendente.email)

    resposta = cancelar(
        client,
        token_atendente,
        pedido["id_pedido"],
        motivo="Cancelamento pela unidade",
    )

    assert resposta.status_code == 200
    assert resposta.json()["status_pedido"] == "CANCELADO"
    assert resposta.json()["motivo_cancelamento"] == (
        "Cancelamento pela unidade"
    )

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 0


def test_perfil_gerente_nao_pode_cancelar_pedido(client, db_session):
    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    gerente = criar_usuario(
        db_session,
        perfil="GERENTE",
        email="gerente@teste.com",
    )
    token_gerente = obter_token(client, gerente.email)

    resposta = cancelar(
        client,
        token_gerente,
        pedido["id_pedido"],
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Você não tem permissão para cancelar pedidos"
    )



def test_cancelar_pedido_com_motivo_curto(client, db_session):
    usuario, token, unidade, pedido, estoque = preparar_pedido(
        client, db_session
    )

    resposta = cancelar(
        client,
        token,
        pedido["id_pedido"],
        motivo="Oi",
    )

    assert resposta.status_code == 422

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2
