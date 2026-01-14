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
        # 슬래시 명령어 전역 동기화
        await self.tree.sync()

bot = MyClient()

# 봇 준비 완료
@bot.event
async def on_ready():
    print(f"✅ 로그인 완료: {bot.user}")

# 메시지 자동 삭제 처리 (on_message 이벤트)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 자동 삭제 기능이 켜져 있을 때만 작동 (5초 후 삭제)
    if bot.auto_delete_enabled:
        await asyncio.sleep(5)
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            print("🚫 메시지 삭제 권한이 없습니다.")

    # 일반 명령어도 처리할 수 있도록 추가
    await bot.process_commands(message)

# --- 슬래시 명령어 영역 ---

# 1. /purge (메시지 일괄 삭제 - 최대 100개)
@bot.tree.command(
    name="purge",
    description="메시지를 일괄 삭제합니다 (최대 100개)"
)
@app_commands.describe(amount="삭제할 메시지의 개수를 입력하세요 (1~100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message(
            "⚠️ 1개에서 100개 사이의 숫자를 입력해주세요.",
            ephemeral=True
        )
        return

    # 삭제 작업은 시간이 걸릴 수 있으므로 응답 대기 처리
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"✅ {len(deleted)}개의 메시지를 삭제했습니다.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ '메시지 관리' 권한이 부족합니다.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ 오류 발생: {e}", ephemeral=True)

# 2. /auto_delete_on
@bot.tree.command(name="auto_delete_on", description="5초 후 메시지 자동 삭제를 켭니다")
async def auto_delete_on(interaction: discord.Interaction):
    bot.auto_delete_enabled = True
    await interaction.response.send_message("🟢 모든 메시지 자동 삭제 모드 활성화!", ephemeral=True)

# 3. /auto_delete_off
@bot.tree.command(name="auto_delete_off", description="자동 메시지 삭제를 끕니다")
async def auto_delete_off(interaction: discord.Interaction):
    bot.auto_delete_enabled = False
    await interaction.response.send_message("🔴 자동 삭제 모드 비활성화됨.", ephemeral=True)

# 4. /disconnect_after
@bot.tree.command(
    name="disconnect_after",
    description="입력한 초 뒤에 본인의 음성 연결을 끊습니다"
)
@app_commands.describe(seconds="몇 초 후 연결을 끊을지 (1~600)")
async def disconnect_after(interaction: discord.Interaction, seconds: int):
    if seconds <= 0 or seconds > 600:
        await interaction.response.send_message("⚠️ 1~600초 사이로 입력해주세요.", ephemeral=True)
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
                await interaction.user.send(f"⏱ {seconds}초가 지나 음성 연결이 끊겼어요 👋")
            else:
                await interaction.user.send("ℹ️ 음성 채널에 연결되어 있지 않아 종료합니다.")
        except asyncio.CancelledError:
            pass
        finally:
            bot.disconnect_tasks.pop(user_id, None)

    bot.disconnect_tasks[user_id] = asyncio.create_task(disconnect_task())
    await interaction.response.send_message(f"⏱ {seconds}초 후 음성 연결을 끊을게요!", ephemeral=True)

# 5. /cancel_disconnect
@bot.tree.command(name="cancel_disconnect", description="예약된 음성 연결 끊기를 취소합니다")
async def cancel_disconnect(interaction: discord.Interaction):
    user_id = interaction.user.id
    task = bot.disconnect_tasks.get(user_id)

    if task:
        task.cancel()
        del bot.disconnect_tasks[user_id]
        await interaction.response.send_message("❎ 연결 끊기 예약이 취소되었습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ 예약된 작업이 없어요.", ephemeral=True)

# 6. /sync (강제 동기화)
@bot.tree.command(name="sync", description="이 서버에 슬래시 명령어를 강제 동기화합니다")
async def sync(interaction: discord.Interaction):
    await bot.tree.sync(guild=interaction.guild)
    await interaction.response.send_message("✅ 현재 서버 명령어 동기화 완료!", ephemeral=True)

# 권한 에러 처리 (purge 전용)
@purge.error
async def purge_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("🚫 '메시지 관리' 권한이 있는 사용자만 사용할 수 있습니다.", ephemeral=True)

# 봇 실행
if __name__ == "__main__":
    bot.run(TOKEN)
