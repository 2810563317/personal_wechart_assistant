from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.debug import router as debug_router


app = FastAPI(title="Personal WeChat Assistant API")

app.include_router(chat_router)
app.include_router(debug_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Personal WeChat Assistant backend is running."}
