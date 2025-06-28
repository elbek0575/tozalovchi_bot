FROM python:3.10-slim

# Tesseract ва керакли пакетлар
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Python requirements
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Иссиқлик (бир хил ишчи фолдера ўтиш)
COPY . .

# Heroku ишлаши учун .apt ичидаги путьни белгилаб қўямиз
ENV ON_HEROKU=1

# Bot ни ишга туширамиз
CMD ["python", "bot.py"]
