web: flask db upgrade; flask translate compile; gunicorn gsonline:app
worker: rq worker gsonline-tasks
