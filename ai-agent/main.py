from fastapi import FastAPI
# FastAPI is a Python framework for building HTTP/REST APIs
# Think of it as the Python equivalent of what Spring Boot is doing for our Java services.

from graph import graph

# Java                         Python
# ────────────────────────────────────────
# Spring Boot                  FastAPI
# @RestController              @app.get()
# @GetMapping                  @app.get()
# POST endpoint                @app.post()


# This creates our FastAPI application object.
app = FastAPI()

# define health endpoint
# "When an HTTP GET request comes to /health, execute the function immediately below this decorator @app.get."
@app.get("/health")
def health():
    return {"status": "UP"}

@app.post("/analyze")
def analyze(incident: dict):
    # The incoming HTTP request becomes the graph's initial state:
    result = graph.invoke({
        "incident": incident,
        "analysis": {}
    })

    return result




# we run following in terminal:
# uvicorn main:app --reload --port 8000
# Uvicorn is basically being told:
# "Open main.py, find the app object, and use it as the web application."