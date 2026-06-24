FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.14 uvicorn==0.34.3 python-multipart==0.0.20 faster-whisper==1.1.1 requests==2.32.4
COPY whisper_service ./whisper_service
EXPOSE 8001
CMD ["uvicorn","whisper_service.app:app","--host","0.0.0.0","--port","8001"]
