# config.py

from pyrogram import Client

class Config:
    # Bot credentials
    BOT_TOKEN = "7613999995:AAGg32yec_D8sn19QBhMsBYoGnvssPaSLZ0"
    API_ID = 9479563
    API_HASH = "1026ce5ebbbe86081a0511769e4e0eff"

    # Database
    DB_PATH = "waifu_bot.db"

    # Owner & Support details
    OWNER_ID = 7606646849
    ADMINS = [7606646849, 6398668820]
    OWNER_USERNAME = "@Professornikhil"
    SUPPORT_GROUP = "https://t.me/Alisabotsupport"
    SUPPORT_CHAT_ID = -1002669919337  # Group chat ID for logging & notifications
    UPDATE_CHANNEL = "https://t.me/AlisaMikhailovnaKujoui"
    
    BOT_USERNAME = "Waifusscollectionbot"

    # Crystal Rewards
    DAILY_CRYSTAL = 5000
    WEEKLY_CRYSTAL = 25000
    MONTHLY_CRYSTAL = 50000

# Create Pyrogram Client here so every handler can import and use it
app = Client(
    "waifu_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
)

# expose important constants at top level
OWNER_ID = Config.OWNER_ID
ADMINS = Config.ADMINS
