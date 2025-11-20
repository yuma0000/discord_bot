FROM python:3.12-slim
# 必要な OS パッケージをインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    unzip \
    wget \
    curl \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /app

# Python ライブラリ（llama_cpp などを先にインストール）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ZIP と bot のコードをコピー
COPY libs1.zip .
COPY libs2.zip .
COPY discord_bot.py .

# libs を展開
RUN mkdir libs && \
    unzip libs1.zip -d libs && \
    unzip libs2.zip -d libs

# 環境変数でトークン・モデル・システムプロンプトを設定
ENV MODEL_URL="https://huggingface.co/yustudiojp/gguf-models/resolve/main/mania-model.tq2_0_K_M.gguf"
ENV SYSTEM_PROMPT="あなたはウェブマニアです。適切に答えて下さい。"

# モデルをダウンロード
RUN wget -O mania-model.gguf $MODEL_URL

# 作業ディレクトリに libs を追加した Python パスを通す
ENV PYTHONPATH="/app/libs:$PYTHONPATH"

# 起動コマンド
CMD ["python", "discord_bot.py", "mania-model.gguf", "$SYSTEM_PROMPT"]
