@echo off
uvicorn api.server:app --host 0.0.0.0 --port 1000 --reload
pause