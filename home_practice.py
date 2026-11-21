# python -m uvicorn home_practice:app --reload

import os
import time
import uuid
import shutil
from pathlib import Path
from typing import Annotated

import bcrypt
import pandas as pd
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
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
    secret_key=os.environ.get("SESSION_SECRET_KEY", "spinach"),
    same_site="lax",
    https_only=False,
)

templates = Jinja2Templates(directory="templates")

USER_DATA_FILE = "user_data.csv"
ARTICLES_FILE = "articles.csv"
COMMENTS_FILE = "comments.csv"
LIKES_FILE = "likes.csv"

SESSION_LIFETIME = 240

ROLES = {
    "COMMON": 1,
    "SILVER": 2,
    "GOLD": 3,
}

AVATAR_DIR = os.path.join("static", "avatars")
UPLOAD_DIR = os.path.join("static", "uploads")

os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


def is_session_active(request: Request) -> bool:
    username = request.session.get("username")
    session_starttime = request.session.get("session_starttime")

    if not username or session_starttime is None:
        return False

    if time.time() - session_starttime > SESSION_LIFETIME:
        request.session.clear()
        return False

    return True


def save_image(
    upload_file: UploadFile,
    upload_dir: str,
) -> str:
    original_extension = Path(upload_file.filename or "").suffix.lower()

    if original_extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Разрешены только изображения JPG, JPEG, PNG, WEBP и GIF",
        )

    unique_filename = f"{uuid.uuid4().hex}{original_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return unique_filename


@app.get("/")
def main_page(request: Request):
    return RedirectResponse(url="/login", status_code=303)


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    if not is_session_active(request):
        return RedirectResponse(url="/login", status_code=303)

    username = request.session.get("username")
    avatar = request.session.get("pfp_url")
    role = request.session.get("role")

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "username": username,
            "pfp_url": avatar,
            "role": role,
        },
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )

from fastapi.responses import StreamingResponse
from fast_captcha import img_captcha

captcha_store: dict[str, str] = {}


@app.get("/captcha")
def get_captcha(request: Request):
    img, text = img_captcha()
    
    # Получаем или создаем ID сессии пользователя
    captcha_id = str(uuid.uuid4())
    captcha_store[captcha_id] = text.lower()
    
    response = StreamingResponse(content=img, media_type="image/jpeg")
    response.set_cookie(key="captcha_id", value=captcha_id, httponly=True)
    return response


@app.post("/verify")
def verify_form(request: Request, user_captcha: str = Form(...)):
    captcha_id = request.cookies.get("captcha_id")
    real_text = captcha_store.pop(captcha_id, None)

    if not real_text or user_captcha.strip().lower() != real_text:
        raise HTTPException(status_code=400, detail="Неверная капча")

    {"status": "ok", "message": "Проверка пройдена!"}

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
    request.session["session_starttime"] = time.time()

    return RedirectResponse(url="/home", status_code=303)


@app.post("/logout")
def log_out(request: Request):
    request.session.clear()

    return RedirectResponse(url="/login", status_code=303)


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
    avatar_file: Annotated[UploadFile | None, File()] = None,
):
    if not os.path.isfile(USER_DATA_FILE) or os.path.getsize(USER_DATA_FILE) == 0:
        existing = pd.DataFrame(
            columns=["username", "password", "pfp", "role"]
        )
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
            existing = pd.DataFrame(
                columns=["username", "password", "pfp", "role"]
            )
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

    avatar_url = "/static/avatars/default.webp"

    if avatar_file and avatar_file.filename:
        avatar_filename = save_image(avatar_file, AVATAR_DIR)
        avatar_url = f"/static/avatars/{avatar_filename}"

    new_user = pd.DataFrame([{
        "username": username,
        "password": password_hash,
        "pfp": avatar_url,
        "role": "COMMON",
    }])

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
    request.session["pfp_url"] = avatar_url
    request.session["role"] = "COMMON"
    request.session["session_starttime"] = time.time()

    return RedirectResponse(url="/home", status_code=303)


@app.get("/main", response_class=HTMLResponse)
def main_page_load(request: Request):
    if not is_session_active(request):
        return RedirectResponse(url="/login", status_code=303)
    
    role = request.session.get("role", "COMMON")

    if not os.path.isfile(ARTICLES_FILE):
        newslist = []
    else:
        try:
            news = pd.read_csv(
                ARTICLES_FILE,
                encoding="utf-8",
            ).fillna("")

            newslist = news.to_dict(orient="records")
        except pd.errors.EmptyDataError:
            newslist = []

    return templates.TemplateResponse(
        request=request,
        name="main.html",
        context={
            "news_list": newslist,
            "role": role,
            "pfp_url": request.session.get("pfp_url"),
            "username": request.session.get('username')
        },
    )


@app.get("/create-news", response_class=HTMLResponse)
def create_news_page(request: Request):
    if not is_session_active(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="create-news.html",
    )


@app.post("/create-news")
def create_news(
    request: Request,
    title: str = Form(...),
    annotation: str = Form(default=""),
    published_at: str = Form(default=""),
    body: str = Form(default=""),
    preview_image: UploadFile | None = File(default=None),
    article_images: list[UploadFile] = File(default=[]),
):
    if not is_session_active(request):
        return RedirectResponse(url="/login", status_code=303)

    preview_path = ""

    if preview_image and preview_image.filename:
        preview_filename = save_image(preview_image, UPLOAD_DIR)
        preview_path = f"/static/uploads/{preview_filename}"

    saved_images = []

    for image in article_images:
        if image and image.filename:
            image_filename = save_image(image, UPLOAD_DIR)
            saved_images.append(f"/static/uploads/{image_filename}")

    file_exists = (
        os.path.isfile(ARTICLES_FILE)
        and os.path.getsize(ARTICLES_FILE) > 0
    )

    article = pd.DataFrame([{
        "title": title,
        "annotation": annotation,
        "body": body,
        "published_at": published_at,
        "preview_image": preview_path,
        "article_images": "|".join(saved_images),
    }])

    try:
        article.to_csv(
            ARTICLES_FILE,
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

    return RedirectResponse(url="/main", status_code=303)


@app.get("/article/{article_id}", response_class=HTMLResponse)
def get_article(request: Request, article_id: int):
    if not is_session_active(request):
        return RedirectResponse(url="/login", status_code=303)

    if not os.path.isfile(ARTICLES_FILE):
        raise HTTPException(status_code=404, detail="Новость не найдена")

    try:
        df = pd.read_csv(ARTICLES_FILE, encoding="utf-8").fillna("")
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    if article_id < 0 or article_id >= len(df):
        raise HTTPException(status_code=404, detail="Новость не найдена")
    
    article = df.iloc[article_id].to_dict()
    article_images_raw = article.get("article_images", "")
    article["article_images"] = article_images_raw.split("|") if article_images_raw else []

    # Безопасная загрузка комментариев
    comments_list = []
    if os.path.isfile(COMMENTS_FILE):
        try:
            comments_df = pd.read_csv(COMMENTS_FILE, encoding="utf-8").fillna("")
            if not comments_df.empty and "article_id" in comments_df.columns:
                # Приводим столбец к int на случай, если pandas прочитал его как float или str
                article_comments = comments_df[comments_df["article_id"].astype(int) == article_id]
                comments_list = article_comments.to_dict(orient="records")
        except (pd.errors.EmptyDataError, ValueError):
            comments_list = []

    return templates.TemplateResponse(
        request=request,
        name="article.html",
        context={
            "article_id": article_id,
            "article": article,
            "username": request.session.get("username"),
            "pfp_url": request.session.get("pfp_url"),
            "comments": comments_list,
        },
    )

@app.post("/article/{article_id}/comment")
def add_comment(
    request: Request,
    article_id: int,
    comment: str = Form(...),
):
    if not is_session_active(request):
        return RedirectResponse(url="/login", status_code=303)

    comment = comment.strip()

    if not comment:
        return RedirectResponse(
            url=f"/article/{article_id}",
            status_code=303,
        )

    comment_df = pd.DataFrame(
        [{
            "article_id": article_id,
            "username": request.session["username"],
            "comment": comment,
        }]
    )
    comment_df.to_csv(
        COMMENTS_FILE,
        index=False,
        mode='a',
        header=not comment,
        encoding="utf-8")

    return RedirectResponse(
        url=f"/article/{article_id}",
        status_code=303,
    )

@app.get("/404", response_class=HTMLResponse)
def error_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
    )