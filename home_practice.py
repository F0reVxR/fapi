#python -m uvicorn home_practice:app --reload
import os
import time
import uuid
import shutil
from typing import Annotated
from PIL import Image, ImageOps

import bcrypt
import pandas as pd
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
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
    same_site='lax',
    https_only=True
)

templates = Jinja2Templates(directory="templates")

USER_DATA_FILE = "user_data.csv"
SESSION_LIFETIME = 120
ROLES = {
    "COMMON": 1,
    "SILVER": 2,
    "GOLD": 3
}


@app.get("/", response_class=RedirectResponse)
def main_page(request: Request):
    return RedirectResponse(url="/login", status_code=303)


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    username = request.session.get("username")
    session_starttime = request.session.get("session_starttime")
    avatar = request.session.get('pfp_url')
    role = request.session.get('role')
    current_time = time.time()

    try:

        if (current_time - session_starttime) or not session_starttime > SESSION_LIFETIME:
            request.session.clear()

    except TypeError:
        return RedirectResponse(url="/login", status_code=303)

    if not username:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": username, 'pfp_url': avatar, "role": role},
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
    pfp_url = user_rows["pfp"].iloc[0]
    role = user_rows["role"].iloc[0]
    
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
    request.session["pfp_url"] = pfp_url
    request.session["role"] = role
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
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    avatar_file: Annotated[UploadFile | None, File()] = None
):
    if not os.path.isfile(USER_DATA_FILE) or os.path.getsize(USER_DATA_FILE) == 0:
        existing = pd.DataFrame(columns=["username", "password", "pfp", "role"])
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
            existing = pd.DataFrame(columns=["username", "password", "pfp", "role"])
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

    if avatar_file and avatar_file.filename:
        file_extension = os.path.splitext(avatar_file.filename)[1] or ".webp"
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        upload_dir = os.path.join("static", "avatars")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)

        with Image.open(avatar_file.file) as img:
            img = ImageOps.exif_transpose(img)

            if file_extension.lower() in (".jpg", ".jpeg") and img.mode in (
                "RGBA",
                "P",
            ):
                img = img.convert("RGB")

            cropped = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)
            cropped.save(file_path)

        avatar_url = f"/static/avatars/{unique_filename}"
    else:
        avatar_url = "/static/avatars/default.webp"

    new_user = pd.DataFrame(
        [{
            "username": username, 
            "password": password_hash,
            "pfp": avatar_url,
            "role": "COMMON"
        }]
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
    request.session["role"] = "COMMON"
    request.session["session_starttime"] = time.time()
    
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "username": username, 
            "pfp_url": avatar_url, 
            "role": "COMMON"
            },
    )


@app.get("/404", response_class=HTMLResponse)
def error_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
    )

@app.get('/main', response_class=HTMLResponse)
def main_page_load(request: Request):
    role = request.session.get('role')
    news = pd.read_csv('articles.csv', encoding="utf-8").fillna('')
    newslist = news.to_dict(orient="records")

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "news_list": newslist,
            'role':role,
            }
    )

@app.get('/create-news', response_class=HTMLResponse)
def news_page_load(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="create-news.html"
    )

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post('/create-news', response_class=HTMLResponse)
def news_page_load(
    request: Request,
    title: str = Form(...),
    annotation: str = Form(default=""),
    published_at: str = Form(default=""),
    body: str = Form(default=""),
    preview_image: UploadFile | None = File(default=None),
    article_images: list[UploadFile] = File(default=[]),
):

    preview_path = ""
    if preview_image and preview_image.filename:
        preview_path = os.path.join(UPLOAD_DIR, preview_image.filename)
        with open(preview_path, "wb") as buffer:
            shutil.copyfileobj(preview_image.file, buffer)

    saved_images = []
    for img in article_images:
        if img and img.filename:
            img_path = os.path.join(UPLOAD_DIR, img.filename)
            with open(img_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)
            saved_images.append(img_path)

    file_exists = os.path.isfile('articles.csv') and os.path.getsize('articles.csv') > 0

    article = pd.DataFrame({
        'title': [title],
        'annotation': [annotation],
        'body': [body],
        'preview_image': [preview_path],
        'article_images': [",".join(saved_images)]
    })

    article.to_csv(
        'articles.csv',
        index=False,
        mode="a",
        header=not file_exists,
        encoding="utf-8",
    )

    return RedirectResponse(url="/main", status_code=303)

@app.get("/article.html", response_class=HTMLResponse)
def get_article(request: Request, id: int):
    df = pd.read_csv("articles.csv")
    
    if id < 0 or id >= len(df):
        raise HTTPException(status_code=404, detail="Новость не найдена")
    
    article = df.iloc[id].fillna("").to_dict()
    
    return templates.TemplateResponse(
        request=request,
        name="article.html", 
        context={"article": article}
    )