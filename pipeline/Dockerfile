FROM python:3.12-slim

# ffmpeg for RTSP decode; libgl/glib for OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV ANPR_PIPELINE_SPOOL_DIR=/data/spool
CMD ["python", "-m", "anpr_pipeline.main"]
