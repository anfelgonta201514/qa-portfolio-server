from flask import Flask

app = Flask(__name__)


@app.get("/")
def index():
    return {"status": "ok", "message": "qa-portfolio-server: hello world"}
