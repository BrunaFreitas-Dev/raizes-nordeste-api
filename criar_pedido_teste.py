import sqlite3
import datetime
import secrets

con = sqlite3.connect("raizes.db")
cur = con.cursor()

agora = datetime.datetime.now()

cur.execute("""
    INSERT INTO pedido (
        id_cliente,
        id_registrado_por,
        id_unidade,
        id_credencial,
        canal_pedido,
        status_pedido,
        valor_total,
        data_pedido,
        data_limite_pagamento,
        motivo_cancelamento,
        codigo_acompanhamento_hash,
        chave_idempotencia_criacao
    )
    VALUES (?, NULL, ?, NULL, ?, ?, ?, ?, ?, NULL, ?, ?)
""", (
    7,
    2,
    "APP",
    "AGUARDANDO_PAGAMENTO",
    18,
    agora.isoformat(),
    (agora + datetime.timedelta(minutes=30)).isoformat(),
    secrets.token_hex(32),
    "teste-unidade-2-direto-001"
))

id_pedido = cur.lastrowid

cur.execute("""
    INSERT INTO item_pedido (
        id_pedido,
        id_produto_unidade,
        quantidade,
        preco_unitario,
        subtotal
    )
    VALUES (?, ?, ?, ?, ?)
""", (id_pedido, 6, 1, 18, 18))

con.commit()
con.close()

print("Pedido de teste criado:", id_pedido)