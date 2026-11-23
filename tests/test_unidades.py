
from decimal import Decimal

from app.infrastructure.models import (
    Unidade,
    Produto,
    ProdutoUnidade,
)


def criar_unidade(db_session, status="ATIVA"):
    unidade = Unidade(
        nome="Unidade Teste",
        endereco="Rua de Teste, 100",
        cidade="Recife",
        estado="PE",
        telefone="81999999999",
        regiao="NORDESTE",
        status=status,
    )

    db_session.add(unidade)
    db_session.commit()
    db_session.refresh(unidade)

    return unidade


def criar_produto(db_session, unidade, status="ATIVO"):
    produto = Produto(
        nome="Bolo de Milho",
        descricao="Bolo de milho tradicional",
        categoria="Bolos",
        status=status,
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

    return produto


def test_listar_unidades_retorna_unidades_ativas(client, db_session):
    criar_unidade(db_session, status="ATIVA")
    criar_unidade(db_session, status="INATIVA")

    resposta = client.get("/unidades/")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["status"] == "ATIVA"


def test_consultar_cardapio_de_unidade_ativa(client, db_session):
    unidade = criar_unidade(db_session)
    criar_produto(db_session, unidade)

    resposta = client.get(
        f"/unidades/{unidade.id_unidade}/cardapio"
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1

    produto = resposta.json()[0]

    assert produto["nome"] == "Bolo de Milho"
    assert produto["categoria"] == "Bolos"
    assert produto["preco"] == "12.50"
    assert produto["disponivel"] is True


def test_consultar_cardapio_de_unidade_inexistente(client):
    resposta = client.get("/unidades/9999/cardapio")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == (
        "Unidade não encontrada ou inativa"
    )


def test_consultar_cardapio_de_unidade_inativa(client, db_session):
    unidade = criar_unidade(db_session, status="INATIVA")

    resposta = client.get(
        f"/unidades/{unidade.id_unidade}/cardapio"
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == (
        "Unidade não encontrada ou inativa"
    )
