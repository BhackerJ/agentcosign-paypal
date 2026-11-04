# Build from the repository root. Local scaffold; not deployed or verified on Render yet.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && python -m playwright install --with-deps chromium
COPY app ./app
COPY fixtures ./fixtures
ENV PORT=10000
EXPOSE 10000
CMD ["python", "app/judge.py", "--host", "0.0.0.0", "--state", "/var/data/judges"]
