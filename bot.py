import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# .env에서 토큰 불러오기
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 봇 클래스 정의
class MyClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.auto_delete_enabled = False
        self.disconnect_tasks = {}  # 유저별 예약 로그아웃

    async def setup_hook(self):
        await self.tree.sync()

bot = MyClient()

# 봇 준비 완료
@bot.event
async def on_ready():
    print(f"✅ 로그인 완료: {bot.user}")

# 메시지 자동 삭제 처리 (슬래시 명령어와 무관)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.auto_delete_enabled:
        await asyncio.sleep(5)
        try:
            await message.delete()
        except discord.NotFound:
            pass

# /auto_delete_on
@bot.tree.command(name="auto_delete_on", description="5초 후 메시지 자동 삭제를 켭니다")
async def auto_delete_on(interaction: discord.Interaction):
    bot.auto_delete_enabled = True
    await interaction.response.send_message(
        "🟢 자동 삭제 활성화됨!",
        ephemeral=True
    )

# /auto_delete_off
@bot.tree.command(name="auto_delete_off", description="자동 메시지 삭제를 끕니다")
async def auto_delete_off(interaction: discord.Interaction):
    bot.auto_delete_enabled = False
    await interaction.response.send_message(
        "🔴 자동 삭제 비활성화됨!",
        ephemeral=True
    )

# /disconnect_after
@bot.tree.command(
    name="disconnect_after",
    description="입력한 초 뒤에 본인의 음성 연결을 끊습니다"
)
@app_commands.describe(seconds="몇 초 후 연결을 끊을지 (1~600)")
async def disconnect_after(interaction: discord.Interaction, seconds: int):
    if seconds <= 0 or seconds > 600:
        await interaction.response.send_message(
            "⚠️ 1~600초 사이로 입력해주세요.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id

    if user_id in bot.disconnect_tasks:
        bot.disconnect_tasks[user_id].cancel()

    async def disconnect_task():
        try:
            await asyncio.sleep(seconds)
            voice_state = interaction.user.voice
            if voice_state and voice_state.channel:
                await interaction.user.move_to(None)
                await interaction.user.send(
                    f"⏱ {seconds}초가 지나 음성 연결이 끊겼어요 👋"
                )
            else:
                await interaction.user.send(
                    "ℹ️ 음성 채널에 연결되어 있지 않아요."
                )
        except asyncio.CancelledError:
            await interaction.user.send(
                "⛔ 연결 끊기가 취소되었습니다."
            )

    bot.disconnect_tasks[user_id] = asyncio.create_task(disconnect_task())
    await interaction.response.send_message(
        f"⏱ {seconds}초 후 음성 연결을 끊을게요!",
        ephemeral=True
    )

# /cancel_disconnect
@bot.tree.command(
    name="cancel_disconnect",
    description="예약된 음성 연결 끊기를 취소합니다"
)
async def cancel_disconnect(interaction: discord.Interaction):
    user_id = interaction.user.id
    task = bot.disconnect_tasks.get(user_id)

    if task:
        task.cancel()
        del bot.disconnect_tasks[user_id]
        await interaction.response.send_message(
            "❎ 연결 끊기 예약이 취소되었습니다.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "ℹ️ 예약된 작업이 없어요.",
            ephemeral=True
        )

# /sync (관리용)
@bot.tree.command(
    name="sync",
    description="이 서버에 슬래시 명령어를 강제 동기화합니다"
)
async def sync(interaction: discord.Interaction):
    await bot.tree.sync(guild=interaction.guild)
    await interaction.response.send_message(
        "✅ 이 서버에 명령어를 동기화했어요!",
        ephemeral=True
    )

# 봇 실행
if __name__ == "__main__":
    bot.run(TOKEN)
