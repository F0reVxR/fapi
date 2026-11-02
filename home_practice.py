# python -m uvicorn home_practice:app --reload
# static - для css

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title='First API')

#Added static files
app.mount(
    path=r'/static',
    app=StaticFiles(directory='static'),
    name='static'
)

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
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
        context={"username": username},
    )