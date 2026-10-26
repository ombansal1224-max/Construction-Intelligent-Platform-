FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt requirements-api.txt ./
RUN pip install -r requirements-api.txt
COPY . .
# Streamlit UI on 8501.  For the API instead:  docker run ... uvicorn backend.main:app --host 0.0.0.0 --port 8000
EXPOSE 8501 8000
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
