FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    HF_HOME=/opt/hf \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# download BAAI/bge-m3 into the image so cold starts do not hit the network
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3', device='cpu')"
ENV HF_HUB_OFFLINE=1

COPY app.py style.css ./
COPY data ./data

# app.py reads PORT (Cloud Run sets it) and binds to 0.0.0.0
CMD ["python", "app.py"]
