#python -m uvicorn main:app --reload
import os
import pandas as pd
import bcrypt

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

templates = Jinja2Templates(directory="templates")

white_urls = ["/", "/login", "/logout", "/register"]

@app.get(path = '/', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'based_main.html')

@app.get(path = '/home', response_class= HTMLResponse)
def main_page(req: Request, username: str):
    context = {'request':req, 'username':username}
    return templates.TemplateResponse(request=req, name = 'home.html', context=context)

@app.get(path = '/login', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'login.html')

@app.get("/login", response_class=HTMLResponse)
def show_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": ""},
    )

@app.post("/login", response_class=HTMLResponse)
def submit_form(request: Request, username: str = Form(...), password: str = Form(...)):
    hp = bcrypt.hashpw(password.encode('utf-8'), salt)
    filename = "user_data.csv"

    file_status = os.path.isfile(filename) and os.path.getsize(filename) > 0

    if file_status:
        try:
            existing = pd.read_csv(filename, dtype=str, keep_default_na=False, encoding="utf-8")
            is_authenticated = ((existing["username"] == username) & (existing["password"] == hp.decode('utf-8'))).any()
            print(is_authenticated)
            redirect_url = f"/home?username={username}"
            if is_authenticated:
                return RedirectResponse(url=redirect_url, status_code=303)
            else: return templates.TemplateResponse(request=request, name='login.html', context={"error": "Incorrect password"})
        except pd.errors.EmptyDataError:
            file_status = False

    return templates.TemplateResponse(request=request, name='login.html', context={"error": 'No such file'})

@app.get(path='/register', response_class=HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name='register.html', context={"error": None})

@app.post(path='/register', response_class=HTMLResponse)
def get_user(req: Request, username: str = Form(...), password: str = Form(...)):
    hp = bcrypt.hashpw(password.encode('utf-8'), salt)
    dictionary = {'username': username, 'password': hp}
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

    dictionary = {'username': username, 'password': hp.decode('utf-8')}
    df_1 = pd.DataFrame([dictionary])
    
    try:
        df_1.to_csv(filename, index=False, mode="a", sep=",", header=not file_status, encoding='utf-8')
        print(f"Файл {filename} успешно обновлен/создан!")
    except Exception as e:
        print(f"Ошибка при записи файла: {e}")
        return HTMLResponse(content=f"Ошибка сервера при записи данных: {e}", status_code=500)

    return templates.TemplateResponse(request=req, name='register.html', context={"error": None})

@app.get(path = '/404', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = '404.html')