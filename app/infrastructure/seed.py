
from decimal import Decimal

from sqlalchemy import select

from app.infrastructure.database import SessionLocal
from app.infrastructure.models import (
    Unidade,
    Produto,
    ProdutoUnidade,
    Estoque,
    Usuario,
    UsuarioUnidade,
)
from app.infrastructure.seguranca import gerar_hash_senha


def executar_seed():
    db = SessionLocal()

    try:
        # 1. Criar unidades
        dados_unidades = [
            {
                "nome": "Unidade Recife",
                "endereco": "Rua do Comércio, 100",
                "cidade": "Recife",
                "estado": "PE",
                "telefone": "(81) 5000-2600",
                "regiao": "NORDESTE",
                "status": "ATIVA",
            },
            {
                "nome": "Unidade Salvador",
                "endereco": "Avenida Central, 200",
                "cidade": "Salvador",
                "estado": "BA",
                "telefone": "(71) 5000-1450",
                "regiao": "NORDESTE",
                "status": "ATIVA",
            },
        ]

        unidades = {}

        for dados in dados_unidades:
            unidade = db.scalar(
                select(Unidade).where(Unidade.nome == dados["nome"])
            )

            if unidade is None:
                unidade = Unidade(**dados)
                db.add(unidade)
                db.flush()

            unidades[dados["nome"]] = unidade

        # 2. Criar produtos
        dados_produtos = [
            {
                "nome": "Bolo de Rolo",
                "descricao": "Doce tradicional pernambucano.",
                "categoria": "DOCES",
                "status": "ATIVO",
            },
            {
                "nome": "Tapioca",
                "descricao": "Produto tradicional à base de mandioca.",
                "categoria": "LANCHES",
                "status": "ATIVO",
            },
            {
                "nome": "Castanha de Caju",
                "descricao": "Castanhas selecionadas.",
                "categoria": "SNACKS",
                "status": "ATIVO",
            },
            {
                "nome": "Rapadura",
                "descricao": "Doce tradicional de cana-de-açúcar.",
                "categoria": "DOCES",
                "status": "ATIVO",
            },
            {
                "nome": "Cocada",
                "descricao": "Doce tradicional à base de coco.",
                "categoria": "DOCES",
                "status": "ATIVO",
            },
        ]

        produtos = {}

        for dados in dados_produtos:
            produto = db.scalar(
                select(Produto).where(Produto.nome == dados["nome"])
            )

            if produto is None:
                produto = Produto(**dados)
                db.add(produto)
                db.flush()

            produtos[dados["nome"]] = produto

        # 3. Criar vínculos entre produtos e unidades
        dados_vinculos = [
            ("Unidade Recife", "Bolo de Rolo", "18.00"),
            ("Unidade Recife", "Tapioca", "12.00"),
            ("Unidade Recife", "Castanha de Caju", "15.00"),
            ("Unidade Recife", "Rapadura", "8.00"),
            ("Unidade Recife", "Cocada", "7.00"),
            ("Unidade Salvador", "Bolo de Rolo", "20.00"),
            ("Unidade Salvador", "Tapioca", "13.00"),
            ("Unidade Salvador", "Castanha de Caju", "16.00"),
            ("Unidade Salvador", "Rapadura", "9.00"),
            ("Unidade Salvador", "Cocada", "8.00"),
        ]

        vinculos = []

        for nome_unidade, nome_produto, preco in dados_vinculos:
            unidade = unidades[nome_unidade]
            produto = produtos[nome_produto]

            vinculo = db.scalar(
                select(ProdutoUnidade).where(
                    ProdutoUnidade.id_unidade == unidade.id_unidade,
                    ProdutoUnidade.id_produto == produto.id_produto,
                )
            )

            if vinculo is None:
                vinculo = ProdutoUnidade(
                    id_unidade=unidade.id_unidade,
                    id_produto=produto.id_produto,
                    preco=Decimal(preco),
                    disponivel=True,
                )
                db.add(vinculo)
                db.flush()

            vinculos.append(vinculo)

        # 4. Criar estoques
        for vinculo in vinculos:
            estoque = db.scalar(
                select(Estoque).where(
                    Estoque.id_produto_unidade
                    == vinculo.id_produto_unidade
                )
            )

            if estoque is None:
                estoque = Estoque(
                    id_produto_unidade=vinculo.id_produto_unidade,
                    quantidade_reservada=0,
                    quantidade_total=50,
                )
                db.add(estoque)

        db.flush()

        # 5. Criar usuários
        dados_usuarios = [
            {
                "nome": "Administrador Teste",
                "email": "admin@raizes.com",
                "perfil": "ADMINISTRADOR",
            },
            {
                "nome": "Gerente Teste",
                "email": "gerente@raizes.com",
                "perfil": "GERENTE",
            },
            {
                "nome": "Atendente Teste",
                "email": "atendente@raizes.com",
                "perfil": "ATENDENTE",
            },
            {
                "nome": "Cliente Teste",
                "email": "cliente@raizes.com",
                "perfil": "CLIENTE",
            },
        ]

        usuarios = {}

        for dados in dados_usuarios:
            usuario = db.scalar(
                select(Usuario).where(
                    Usuario.email == dados["email"]
                )
            )

            if usuario is None:
                usuario = Usuario(
                    nome=dados["nome"],
                    email=dados["email"],
                    senha_hash=gerar_hash_senha("Senha@123"),
                    perfil=dados["perfil"],
                    ativo=True,
                )
                db.add(usuario)
                db.flush()

            usuarios[dados["perfil"]] = usuario

        # 6. Vincular usuários à unidade Recife
        unidade_recife = unidades["Unidade Recife"]

        for perfil in ("ADMINISTRADOR", "GERENTE", "ATENDENTE"):
            usuario = usuarios[perfil]

            vinculo = db.scalar(
                select(UsuarioUnidade).where(
                    UsuarioUnidade.id_usuario == usuario.id_usuario,
                    UsuarioUnidade.id_unidade == unidade_recife.id_unidade,
                )
            )

            if vinculo is None:
                db.add(
                    UsuarioUnidade(
                        id_usuario=usuario.id_usuario,
                        id_unidade=unidade_recife.id_unidade,
                        ativo=True,
                    )
                )

        # Finalizar transação
        db.commit()

        print("Seed executado com sucesso!")
        print("2 unidades, 5 produtos, 10 vínculos e 10 estoques.")
        print("4 usuários cadastrados.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    executar_seed()
