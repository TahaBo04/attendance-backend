# Render will build this Docker image and run it
FROM python:3.11-slim

# dlib/face_recognition dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake pkg-config \
    libopenblas-dev liblapack-dev \
    libx11-dev libgtk-3-dev \
    libboost-all-dev \
    libjpeg-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Expose (Render sets $PORT)
ENV PORT=10000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
