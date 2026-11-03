from fastapi import FastAPI, Request
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
    return templates.TemplateResponse(request=req, name = 'main.html')

@app.get(path = '/home', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'home.html')

@app.get(path = '/login', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'login.html')

@app.get(path = '/register', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = 'register.html')

@app.get(path = '/404', response_class= HTMLResponse)
def main_page(req: Request):
    return templates.TemplateResponse(request=req, name = '404.html')
