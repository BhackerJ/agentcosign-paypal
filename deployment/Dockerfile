# Local-reviewed image; publication and Render activation require owner approval.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && python -m playwright install --with-deps chromium
COPY third-party ./third-party
COPY LICENSE THIRD_PARTY.md PUBLIC-RESOURCES.md ./
COPY app ./app
COPY fixtures ./fixtures
COPY tools/run_channel3_recovery.py ./tools/run_channel3_recovery.py
COPY deployment/bundle/replay ./replay
COPY deployment/bundle/evidence ./evidence
COPY deployment/bundle/manifest.json ./deployment-manifest.json
ENV PORT=10000 STATE_DIR=/var/data/judges REPLAY_DIR=/app/replay MAX_LIVE_RUNS=40 MAX_ACTIVE_SESSIONS=200
EXPOSE 10000
CMD ["python", "app/experience.py", "--host", "0.0.0.0"]
