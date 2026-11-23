
from datetime import datetime, timedelta, timezone

from app.infrastructure.config import configuracoes
from app.infrastructure.models import (
    Usuario,
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    Pedido,
    TentativaPagamento,
    HistoricoStatusPedido,
    Auditoria,
    MovimentacaoEstoque,
)
from app.infrastructure.seguranca import gerar_hash_senha

def criar_usuario(db_session, email="cliente@teste.com"):
    usuario = Usuario(
        nome="Cliente Teste",
        email=email,
        senha_hash=gerar_hash_senha("Senha123"),
        perfil="CLIENTE",
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

def criar_estrutura_estoque(db_session):
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
        preco=12.50,
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

def criar_pedido_teste(client, token, unidade, produto_unidade, chave):
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

def realizar_pagamento(
    client,
    token,
    id_pedido,
    chave="pagamento-teste-001",
    resultado="APROVADO",
):
    return client.post(
        f"/pedidos/{id_pedido}/pagamento",
        json={
            "forma_pagamento": "PIX",
            "resultado_simulado": resultado,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": chave,
        },
    )

def preparar_pedido(client, db_session, monkeypatch):
    monkeypatch.setattr(configuracoes, "modo_pagamento", "MOCK")

    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_estrutura_estoque(db_session)
    token = obter_token(client, usuario.email)

    pedido = criar_pedido_teste(
        client,
        token,
        unidade,
        produto_unidade,
        "criacao-pedido-pagamento",
    )

    return usuario, token, pedido, estoque

def test_pagamento_aprovado_com_sucesso(client, db_session, monkeypatch):
    usuario, token, pedido, estoque = preparar_pedido(
        client, db_session, monkeypatch
    )

    resposta = realizar_pagamento(
        client,
        token,
        pedido["id_pedido"],
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["status_pagamento"] == "APROVADO"
    assert dados["status_pedido"] == "PAGO"
    assert dados["mensagem"] == "Pagamento aprovado com sucesso"
    assert dados["identificador_transacao"].startswith("MOCK-")

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2

    tentativa = db_session.query(TentativaPagamento).first()
    assert tentativa is not None
    assert tentativa.forma_pagamento == "PIX"
    assert tentativa.mensagem_recusa is None

    historico = db_session.query(HistoricoStatusPedido).filter(
        HistoricoStatusPedido.id_pedido == pedido["id_pedido"]
    ).order_by(HistoricoStatusPedido.id_historico.desc()).first()

    assert historico.status_novo == "PAGO"

    auditoria = db_session.query(Auditoria).filter(
        Auditoria.id_pedido == pedido["id_pedido"]
    ).order_by(Auditoria.id_auditoria.desc()).first()

    assert auditoria.acao == "PROCESSAMENTO_PAGAMENTO"

def test_pagamento_recusado_com_sucesso(client, db_session, monkeypatch):
    usuario, token, pedido, estoque = preparar_pedido(
        client, db_session, monkeypatch
    )

    resposta = realizar_pagamento(
        client,
        token,
        pedido["id_pedido"],
        resultado="RECUSADO",
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["status_pagamento"] == "RECUSADO"
    assert dados["status_pedido"] == "FALHA_PAGAMENTO"
    assert dados["mensagem"] == "Pagamento recusado"

    tentativa = db_session.query(TentativaPagamento).first()
    assert tentativa.mensagem_recusa == "Pagamento recusado no ambiente MOCK"

    db_session.refresh(estoque)
    assert estoque.quantidade_reservada == 2

def test_repetir_pagamento_com_mesma_chave(client, db_session, monkeypatch):
    usuario, token, pedido, estoque = preparar_pedido(
        client, db_session, monkeypatch
    )

    primeira = realizar_pagamento(
        client,
        token,
        pedido["id_pedido"],
        chave="pagamento-repetido",
    )

    segunda = realizar_pagamento(
        client,
        token,
        pedido["id_pedido"],
        chave="pagamento-repetido",
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert segunda.json()["mensagem"] == "Tentativa já processada anteriormente"

    assert db_session.query(TentativaPagamento).count() == 1

def test_reutilizar_chave_em_outro_pedido(client, db_session, monkeypatch):
    monkeypatch.setattr(configuracoes, "modo_pagamento", "MOCK")

    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_estrutura_estoque(db_session)
    token = obter_token(client, usuario.email)

    pedido1 = criar_pedido_teste(
        client, token, unidade, produto_unidade, "pedido-pagamento-1"
    )

    pedido2 = criar_pedido_teste(
        client, token, unidade, produto_unidade, "pedido-pagamento-2"
    )

    primeira = realizar_pagamento(
        client,
        token,
        pedido1["id_pedido"],
        chave="chave-pagamento-compartilhada",
    )

    segunda = realizar_pagamento(
        client,
        token,
        pedido2["id_pedido"],
        chave="chave-pagamento-compartilhada",
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 409
    assert segunda.json()["detail"] == (
        "Chave de idempotência já utilizada em outro pedido"
    )

    assert db_session.query(TentativaPagamento).count() == 1

def test_pagar_pedido_de_outro_cliente(client, db_session, monkeypatch):
    usuario, token, pedido, estoque = preparar_pedido(
        client, db_session, monkeypatch
    )

    outro_usuario = criar_usuario(
        db_session,
        email="outro@teste.com",
    )
    outro_token = obter_token(client, outro_usuario.email)

    resposta = realizar_pagamento(
        client,
        outro_token,
        pedido["id_pedido"],
    )

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Você não tem permissão para pagar este pedido"
    )

def test_pagar_pedido_inexistente(client, db_session, monkeypatch):
    monkeypatch.setattr(configuracoes, "modo_pagamento", "MOCK")

    usuario = criar_usuario(db_session)
    token = obter_token(client, usuario.email)

    resposta = realizar_pagamento(
        client,
        token,
        9999,
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Pedido não encontrado"

def test_pagar_sem_token(client, db_session, monkeypatch):
    monkeypatch.setattr(configuracoes, "modo_pagamento", "MOCK")

    resposta = client.post(
        "/pedidos/1/pagamento",
        json={
            "forma_pagamento": "PIX",
            "resultado_simulado": "APROVADO",
        },
        headers={"Idempotency-Key": "sem-token"},
    )

    assert resposta.status_code == 401

def test_pagamento_com_modo_diferente_de_mock(client, db_session, monkeypatch):
    monkeypatch.setattr(configuracoes, "modo_pagamento", "REAL")

    usuario = criar_usuario(db_session)
    unidade, produto_unidade, estoque = criar_estrutura_estoque(db_session)
    token = obter_token(client, usuario.email)

    pedido = criar_pedido_teste(
        client,
        token,
        unidade,
        produto_unidade,
        "pedido-modo-real",
    )

    resposta = realizar_pagamento(
        client,
        token,
        pedido["id_pedido"],
    )

    assert resposta.status_code == 501
    assert resposta.json()["detail"] == (
        "Este serviço está configurado apenas para pagamento MOCK"
    )

def test_pagamento_com_prazo_expirado(client, db_session, monkeypatch):
    usuario, token, pedido, estoque = preparar_pedido(
        client, db_session, monkeypatch
    )

    registro = db_session.get(Pedido, pedido["id_pedido"])
    registro.data_limite_pagamento = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    db_session.commit()

    resposta = realizar_pagamento(
        client,
        token,
        pedido["id_pedido"],
        chave="pagamento-expirado",
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == (
        "Prazo de pagamento expirado. Pedido cancelado."
    )

    db_session.refresh(registro)
    db_session.refresh(estoque)

    assert registro.status_pedido == "CANCELADO"
    assert registro.motivo_cancelamento == "PRAZO_PAGAMENTO_EXPIRADO"
    assert estoque.quantidade_reservada == 0

    movimentacao = db_session.query(MovimentacaoEstoque).filter(
        MovimentacaoEstoque.id_pedido == pedido["id_pedido"]
    ).order_by(MovimentacaoEstoque.id_movimentacao.desc()).first()

    assert movimentacao.tipo_movimentacao == "LIBERACAO"