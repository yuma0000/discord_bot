#!/usr/bin/env bash
mkdir libs
cd libs
unzip ../libs1.zip
unzip ../libs2.zip
cd ./..
pip install audioop
wget https://huggingface.co/yustudiojp/gguf-models/resolve/main/mania-model.Q8_K_M.gguf
python discord_bot.py mania-model.Q8_K_M.gguf "あなたはウェブマニアです。適切に答えて下さい。"
