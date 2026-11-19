
from fastapi import FastAPI

from app.api.auth import router as auth_router

from app.api.unidades import router as unidades_router


app = FastAPI(title="Raízes do Nordeste API")

app.include_router(auth_router)
app.include_router(unidades_router)


@app.get("/")
def raiz():
    return {"mensagem": "API no ar"}
