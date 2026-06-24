FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml requirements.lock README.md ./
RUN pip install --no-cache-dir -r requirements.lock
COPY hub ./hub
COPY config ./config
COPY locales ./locales
COPY workflows ./workflows
RUN pip install --no-cache-dir --no-deps .
EXPOSE 8000
CMD ["uvicorn","hub.app:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
