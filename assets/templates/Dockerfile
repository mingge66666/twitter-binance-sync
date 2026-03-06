FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p db logs tmp cookies && \
    chown -R pwuser:pwuser /app

USER pwuser

CMD ["python", "-u", "main.py"]
