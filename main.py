#python -m uvicorn main:app --reload

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
def main_page(req: Request):
    context = {'request':req, 'username':'Mikola', 'password_hash':'fhvadvbasxbq7rq76fvq7qcdc3q2c'}
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

@app.post("/submit", response_class=HTMLResponse)
def submit_form(request: Request, username: str = Form(...)):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"username": username}
    )

@app.get(path = '/register', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'register.html')

@app.get(path = '/404', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = '404.html')
