from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"msg": "PCI 用药管理后端已启动"}