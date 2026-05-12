FROM python:3.12-slim

WORKDIR /app

# Build tools needed by pycairo (pulled in by xhtml2pdf → svglib → rlpycairo)
# ffmpeg is required by pydub for MP3 encoding (gemini-audio-gen.py line 196: audio.export(..., format="mp3"))
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libcairo2-dev \
    pkg-config \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so this layer caches independently of source changes
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent package (skills live inside backend/)
COPY backend/ ./backend/

# Copy generation data snapshot (baked in at build time) and shared tool libraries
COPY generation/units/ ./generation/units/
COPY generation/tools/paths.py ./generation/tools/paths.py
COPY generation/tools/text_utils.py ./generation/tools/text_utils.py
COPY generation/tools/script_tool.py ./generation/tools/script_tool.py

# Copy FastAPI entry point
COPY main.py .

# Create non-root user and own everything AFTER all copies so appuser can write at runtime
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

USER appuser

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
