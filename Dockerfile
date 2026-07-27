FROM python:3.11-slim

# FFmpeg ni o'rnatish
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Qolgan fayllarni ko'chirish
COPY . .

# Botni ishga tushirish
CMD ["python", "main.py"]
