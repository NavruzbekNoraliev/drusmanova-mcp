FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir "fastmcp>=2.3.0,<4.0.0" "httpx>=0.27.0,<1.0.0"
COPY . .
EXPOSE 8090
CMD ["python", "server.py"]
