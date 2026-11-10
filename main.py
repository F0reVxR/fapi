#python -m uvicorn main:app --reload
import os
import pandas as pd
import bcrypt
import itsdangerous

from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

salt = bcrypt.gensalt()

app = FastAPI()

app.mount(
    path=r'/static',
    app=StaticFiles(directory='static'),
    name='static'
)
app.add_middleware(SessionMiddleware, secret_key='spinach')
templates = Jinja2Templates(directory="templates")

white_urls = ["/", "/login", "/logout", "/register"]

@app.get(path = '/', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'based_main.html')

@app.get(path = '/home', response_class= HTMLResponse)
def home_page(req: Request):
    username = req.session.get('username')
    password = req.session.get('password')
    if not username:
        return RedirectResponse(request=req, name = '/login.html', status_code=402)
    context = {'request':req, 'username':username, 'password':password}
    return templates.TemplateResponse(request=req, name = 'home.html', context=context)

@app.get(path = '/login', response_class= HTMLResponse)
def login_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'login.html')

@app.get("/login", response_class=HTMLResponse)
def show_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"error": None},
    )

@app.post("/login", response_class=HTMLResponse)
def submit_form(
    request: Request, username: str = Form(...), password: str = Form(...)
):
  filename = "user_data.csv"
  file_status = os.path.isfile(filename) and os.path.getsize(filename) > 0

  if not file_status:
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": "No such file"}
    )

  try:
    existing = pd.read_csv(
        filename, dtype=str, keep_default_na=False, encoding="utf-8"
    )

    user_rows = existing[existing["username"] == username]

    # Вся логика проверки должна быть строго ЗДЕСЬ
    if not user_rows.empty:
      # Достаем строку (тип str), взяв самый первый элемент серии (.values[0])
      stored_hash_str = user_rows["password"].values[0]

      password_bytes = password.encode("utf-8")
      stored_hash_bytes = stored_hash_str.encode("utf-8")

      try:
        if bcrypt.checkpw(password_bytes, stored_hash_bytes):
          request.session["username"] = username
          redirect_url = f"/home?username={username}"
          return RedirectResponse(url=redirect_url, status_code=303)
      except ValueError:
        # Защита на случай, если в CSV лежит обычный текст вместо bcrypt-хеша
        print(f"Критическая ошибка: невалидный хеш в БД для {username}")

    # Сюда код попадет, если пользователя нет, пароль не подошел или хеш поврежден
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Incorrect username or password"},
    )

  except pd.errors.EmptyDataError:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Database file is empty"},
    )
  
@app.get(path='/register', response_class=HTMLResponse)
def register_page(req: Request):
    return templates.TemplateResponse(request=req, name='register.html', context={"error": None})

@app.post(path='/register', response_class=HTMLResponse)
def get_user(req: Request, username: str = Form(...), password: str = Form(...)):
    hp = bcrypt.hashpw(password.encode('utf-8'), salt)
    req.session['username'] = username
    req.session['password'] = hp
    dictionary = {'username': req.session.get(username), 'password': req.session.get('password')}
    filename = "user_data.csv"

    file_status = os.path.isfile(filename) and os.path.getsize(filename) > 0

    if file_status:
        try:
            existing = pd.read_csv(filename, dtype=str, keep_default_na=False, encoding="utf-8")
            if "username" in existing.columns:
                is_duplicate = (existing["username"] == dictionary["username"]).any()
            else:
                is_duplicate = False
                    
            if is_duplicate:
                return templates.TemplateResponse(request=req, name='register.html', context={"error": "User already exists"})
        except pd.errors.EmptyDataError:
            file_status = False

    dictionary = {'username': username, 'password': (req.session.get('password')).decode('utf-8')}
    df_1 = pd.DataFrame([dictionary])
    
    try:
        df_1.to_csv(filename, index=False, mode="a", sep=",", header=not file_status, encoding='utf-8')
        print(f"Файл {filename} успешно обновлен/создан!")
    except Exception as e:
        print(f"Ошибка при записи файла: {e}")
        return HTMLResponse(content=f"Ошибка сервера при записи данных: {e}", status_code=500)

    return templates.TemplateResponse(request=req, name='home.html', context={"username": username})

@app.get(path = '/404', response_class= HTMLResponse)
def error_page(req: Request):
    return templates.TemplateResponse(request=req, name = '404.html')