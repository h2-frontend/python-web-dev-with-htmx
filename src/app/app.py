from typing import Any

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.app.auth_router import auth_router
from src.app.chat_router import chat_router
from src.app.example_router import example_router
from src.app.utils import templates

from langchain.globals import set_debug, set_verbose
set_debug(True)
set_verbose(True)

from src.app.rag.config import CONFIG
from src.app.rag.chain import build_history_chain_LECL

security = HTTPBearer()

app = FastAPI()
#app.state.chain = build_history_chain(**CONFIG)
app.state.chain, app.state.retriever = build_history_chain_LECL(**CONFIG)

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(auth_router, prefix="/auth")
app.include_router(chat_router, prefix="/chat")
app.include_router(example_router, prefix="/example")


@app.get("/")
def home() -> RedirectResponse:
    """
    Redirects the user to the '/chat' endpoint.
    """
    return RedirectResponse("/chat")


@app.get("/login", response_class=HTMLResponse)
def login(
    request: Request,
) -> HTMLResponse:
    """
    Renders the login page.

    Parameters:
        - request: The incoming request.

    Returns:
        - HTMLResponse: The rendered login page.
    """
    res: HTMLResponse = templates.TemplateResponse(
        request=request,
        name="login.html",
    )

    return res


@app.get("/signup", response_class=HTMLResponse)
def signup(
    request: Request,
) -> HTMLResponse:
    """
    Renders the signup page.

    Parameters:
        - request: The incoming request.

    Returns:
        - HTMLResponse: The rendered signup page.
    """
    res: HTMLResponse = templates.TemplateResponse(
        request=request,
        name="signup.html",
    )
    return res


@app.exception_handler(401)
async def custom_404_handler(_: Any, __: Any) -> RedirectResponse:
    """
    Handles the 401 exception and redirects the user to the '/login' endpoint.

    Parameters:
        - _: The exception.
        - __: The exception details.

    Returns:
        - RedirectResponse: The redirect response to the '/login' endpoint.
    """
    return RedirectResponse("/login")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)