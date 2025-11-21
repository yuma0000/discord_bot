# ==========================================================
#  Discord Bot (GGUF / llama.cpp 高速版)
# ==========================================================

import os
import re
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "libs"))

import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands
from llama_cpp import Llama
from http.server import SimpleHTTPRequestHandler
import socketserver

# ====== 設定 ======
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GGUF_PATH = sys.argv[1]

MAX_NEW_TOKENS = 100
STREAM_DELAY = 0.3
MAX_DISCORD_LENGTH = 1800

# ====== 生成パラメータ設定 ======
GEN_CONFIG = {
    "max_tokens": 256,
    "temperature": 1.0,
    "top_p": 0.70,
    "top_k": 40,
    "repeat_penalty": 1.05,
    "stop": ["</s>"],
}

RUNTIME_CONFIG = {
    "n_threads": 8,
    "n_gpu_layers": 32,
    "n_ctx": 4096
}

NUMERIC_PARAMS = {
    "max_tokens": int,
    "temperature": float,
    "top_p": float,
    "top_k": int,
    "repeat_penalty": float,
    "stop": list,
}

# ====== ログ設定 ======
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
    force=True
)
log = logging.getLogger("LLM-Bot")

#webserver
with socketserver.TCPServer(("", 8080), SimpleHTTPRequestHandler) as httpd:
    print("webserver start")
    httpd.serve_forever()

# ====== llama.cpp モデルロード ======
log.info(f"Loading GGUF model from: {GGUF_PATH}")

llm = Llama(
    model_path=GGUF_PATH,
    n_ctx=RUNTIME_CONFIG["n_ctx"],
    n_threads=RUNTIME_CONFIG["n_threads"],
    n_gpu_layers=RUNTIME_CONFIG["n_gpu_layers"],
    verbose=False,
    low_vram=True
)

log.info("GGUF model loaded successfully!")

# ====== ストリーミング生成 ======
async def generate_stream(prompt: str, match_cat):
    output = llm(
        prompt,
        max_tokens=GEN_CONFIG["max_tokens"],
        temperature=GEN_CONFIG["temperature"],
        top_p=GEN_CONFIG["top_p"],
        top_k=GEN_CONFIG["top_k"],
        repeat_penalty=GEN_CONFIG["repeat_penalty"],
        stop=GEN_CONFIG["stop"]
    )

    text = output["choices"][0]["text"]

    if match_cat and text.startswith(prompt):
        text = text[len(prompt):].lstrip()

    if text == "":
        msg = "空の文字が生成されてしまった このメッセージは消えます"
        msg.delete(delay=5)

    for i in range(0, len(text), 80):
        yield text[i:i+80]
        await asyncio.sleep(STREAM_DELAY)


# ====== Discord Bot ======
class ManiaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guild_messages = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            log.info(f"Commands synced globally ({len(synced)} commands).")
        except Exception:
            log.exception("Command sync failed")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        log.info("mania bot is ready.")

bot = ManiaBot()

async def discord_generate(interaction: discord.Interaction, prompt: str, is_base: bool = True):
    await interaction.response.send_message("生成中です…")
    msg = await interaction.original_response()

    collected = ""
    async for chunk in generate_stream(prompt, is_base):
        collected += chunk
        await msg.edit(
            content=(collected[:MAX_DISCORD_LENGTH] + "…")
            if len(collected) > MAX_DISCORD_LENGTH else collected
        )

    if reply_to:
        channel = interaction.channel
        try:
            target = await channel.fetch_message(int(reply_to))
            await target.reply(collected)
        except:
            await msg.edit(content=collected + "\n⚠️返信対象メッセージが見つかりませんでした。")
    else:
        await msg.edit(content=collected)
 
# ====== /mania ======
@bot.tree.command(name="mania", description="ウェブマニアとして回答します。")
@app_commands.describe(prompt="質問内容を入力してください。", reply_to="返信したいメッセージID")
async def mania_slash(interaction: discord.Interaction, prompt: str, reply_to: str = None):
    text = f"""system:{sys.argv[2]}
user:{prompt}
ウェブマニア:"""
    await discord_generate(interaction, text, True)

#======= アプリコマンド =======
@bot.tree.context_menu(name="mania")
async def mania_app(interaction: discord.Interaction, prompt: discord.Message):
    await discord_generate(interaction, f"""system:{sys.argv[3]}
user:{prompt}
ウェブマニア:""", True)

@bot.tree.context_menu(name="free")
async def mania_app(interaction: discord.Interaction, prompt: discord.Message):
    await discord_generate(interaction, prompt, False)

# ====== !mania プレフィックス ======
@bot.command(name="mania")
async def mania_prefix(ctx, *, prompt: str):
    await ctx.send("生成中です…")
    text = f"""system:ユーザーの内容を見てウェブマニアとして個性を活かして回答して下さい。
user:{prompt}
assistant:
    """
    async for chunk in generate_stream(text, False):
        await ctx.send(chunk)

# ====== bot 実行 ======
if __name__ == "__main__":
    try:
        log.info("Starting Discord bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        log.info("Bot manually stopped.")
    except Exception:
        log.exception("Bot failed to start")
