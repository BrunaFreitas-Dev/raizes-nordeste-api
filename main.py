from fastapi import FastAPI

app = FastAPI(title="Raízes do Nordeste API")

@app.get("/")
def raiz():
    return {"mensagem": "API no ar"}