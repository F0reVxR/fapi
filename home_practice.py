import os

import bcrypt
import pandas as pd
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()

app.mount(
    path="/static",
    app=StaticFiles(directory="static"),
    name="static",
)

app.add_middleware(
    SessionMiddleware,
    secret_key="spinach",
)

templates = Jinja2Templates(directory="templates")

USER_DATA_FILE = "user_data.csv"


@app.get("/", response_class=HTMLResponse)
def main_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="based_main.html",
    )


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    username = request.session.get("username")

    if not username:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": username},
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )


@app.post("/login", response_class=HTMLResponse)
def submit_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not os.path.isfile(USER_DATA_FILE) or os.path.getsize(USER_DATA_FILE) == 0:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Database file is empty"},
        )

    try:
        users = pd.read_csv(
            USER_DATA_FILE,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8",
        )
    except pd.errors.EmptyDataError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Database file is empty"},
        )

    user_rows = users[users["username"] == username]

    if user_rows.empty:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Incorrect username or password"},
        )

    stored_hash = user_rows["password"].iloc[0]

    try:
        password_is_correct = bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Incorrect username or password"},
        )

    if not password_is_correct:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Incorrect username or password"},
        )

    request.session["username"] = username

    return RedirectResponse(url="/home", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"error": None},
    )


@app.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not os.path.isfile(USER_DATA_FILE) or os.path.getsize(USER_DATA_FILE) == 0:
        existing = pd.DataFrame(columns=["username", "password"])
        file_exists = False
    else:
        try:
            existing = pd.read_csv(
                USER_DATA_FILE,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8",
            )
            file_exists = True
        except pd.errors.EmptyDataError:
            existing = pd.DataFrame(columns=["username", "password"])
            file_exists = False

    if not existing.empty and (existing["username"] == username).any():
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "User already exists"},
        )

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    new_user = pd.DataFrame(
        [{"username": username, "password": password_hash}]
    )

    try:
        new_user.to_csv(
            USER_DATA_FILE,
            index=False,
            mode="a",
            header=not file_exists,
            encoding="utf-8",
        )
    except Exception as exc:
        return HTMLResponse(
            content=f"Ошибка сервера при записи данных: {exc}",
            status_code=500,
        )

    request.session["username"] = username

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": username},
    )


@app.get("/404", response_class=HTMLResponse)
def error_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
    )