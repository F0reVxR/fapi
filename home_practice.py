#python -m uvicorn home_practice:app --reload
import os
import io
import time
from PIL import Image, ImageOps, UnidentifiedImageError

import bcrypt
import pandas as pd
from pathlib import Path
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
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
    same_site='lax',
    https_only=True
)

templates = Jinja2Templates(directory="templates")

USER_DATA_FILE = "user_data.csv"
SESSION_LIFETIME = 120
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@app.get("/", response_class=HTMLResponse)
def main_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="based_main.html",
    )


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    username = request.session.get("username")
    session_starttime = request.session.get("session_starttime")
    avatar = request.session.get('avatar')
    current_time = time.time()

    try:

        if (current_time - session_starttime) or not session_starttime> SESSION_LIFETIME:
            request.session.clear()

    except TypeError:
        return RedirectResponse(url="/login", status_code=303)

    if not username:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": username, 'avatar': avatar},
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
    request.session["session_starttime"]= time.time()

    return RedirectResponse(url="/home", status_code=303)

@app.post("/logout", response_class=HTMLResponse)
def log_out(request: Request):
    request.session.clear()
    return RedirectResponse(
        url='/login',
        status_code=303
    )

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
    request.session["session_starttime"]= time.time()

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

@app.post("/home")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Пользователь не авторизован")

    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Недопустимый формат файла")

    contents = await file.read()

    try:
        img = Image.open(io.BytesIO(contents))
        
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
            
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Файл поврежден или не является изображением")

    img = ImageOps.fit(img, (300, 300), Image.Resampling.LANCZOS)

    upload_dir = Path(f"static/pics/{username}/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / "avatar.webp"
    img.save(file_path, format="WEBP", quality=85)
    
    return RedirectResponse(url="/", status_code=303)