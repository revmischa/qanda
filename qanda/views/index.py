from qanda import app
from flask import request


@app.errorhandler(404)
def page_not_found(e):
    return f"im so sorry... the URL {request.url} (with path {request.path}) wasn't found", 404
