# python -m uvicorn fastapi_lect:app --reload
# static - для css

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount(
    path = "/static",
    app = StaticFiles(directory="static"),
    name="static"
    )
# app.mount(
#     path = "/sources",
#     app = StaticFiles(directory="sources"),
#     name="sources"
#     )

templates = Jinja2Templates(directory="templates")

white_urls = ["/", "/login", "/logout", "/register"]

@app.get(
    path = '/',
    response_class= HTMLResponse
)
def main_page(req: Request):
    return templates.TemplateResponse(
        name = 'home.html',
        request= {'request':req}
    )

