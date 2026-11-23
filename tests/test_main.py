def test_api_esta_no_ar(client):
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert resposta.json() == {"mensagem": "API no ar"}