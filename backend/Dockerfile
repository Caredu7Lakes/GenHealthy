FROM python:3.12-slim
WORKDIR /app

# Dependências de sistema para compilar cyvcf2 (htslib).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libcurl4-openssl-dev zlib1g-dev libbz2-dev liblzma-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Baixa o modelo de embedding no build, embutindo-o na imagem.
ENV HF_HOME=/app/.hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', backend='onnx', model_kwargs={'file_name': 'onnx/model_qint8_avx512.onnx'})"
COPY . .

# Registra app/ e genrisk_agent/ como pacotes (resolve imports de forma limpa).
RUN pip install --no-cache-dir -e .

# Constrói o índice FAISS no build (corpus estático, ~0.06 MB).
RUN python -m app.rag.ingest

RUN python -c "from app.whatsapp_mock.ecg_sintetico import gerar; from pathlib import Path; p = Path('data/ecg'); p.mkdir(parents=True, exist_ok=True); (p/'ficticio_DB_0001_ecg.png').write_bytes(gerar(conforme=False))"

RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]