import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
from flask import Flask
from threading import Thread
import os

# --- 7/24 AKTİF TUTMA SİSTEMİ (WEB SERVER) ---
app = Flask('')

@app.route('/')
def home():
    return "Montana Guard 7/24 Aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT AYARLARI ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# --- VERİLER VE ID'LER ---
# Token'ı Secrets kısmından çeker
TOKEN = os.environ.get('TOKEN')

# Yetkili Rolleri
ALLOWED_ROLES = [1488290441903341701, 1494318335138074684, 1492142878334386186]
MUTE_STAFF_ROLE = 1495366525576806480 # Mute/Unmute yetkilisi

# İşlem Rolleri ve Kanalları
MUTE_ROLE_ID = 1495134542724337834
VER_ROLE_ID = 1495132680222801950
RESTRICTED_CHANNELS = [1495110127932411954, 1494733890672398506]

# Guard Sistemi Takibi
ban_counter = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Developed By Montana"))
    print(f'--- {bot.user.name} Giriş Yaptı ---')

# Yetki Kontrolleri
def is_staff(ctx):
    return any(role.id in ALLOWED_ROLES for role in ctx.author.roles)

def can_mute(ctx):
    return any(role.id == MUTE_STAFF_ROLE for role in ctx.author.roles)

# --- MUTE (TIMEOUT) SİSTEMİ ---
@bot.command()
async def mute(ctx, member: discord.Member = None):
    if not can_mute(ctx):
        return await ctx.reply("yetkin yok.")

    target = None
    if ctx.message.reference:
        referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        target = referenced_msg.author
    elif member:
        target = member

    if target:
        try:
            duration = timedelta(days=27)
            await target.timeout(duration, reason="Montana Guard tarafından susturuldu.")
            await ctx.reply(f"{target.display_name} susturdum.")
        except discord.Forbidden:
            await ctx.reply(f"{ctx.author.mention} yüksek.")
        except Exception as e:
            await ctx.send(f"Hata: {e}")
    else:
        await ctx.send("Lütfen birini etiketle veya bir mesajı yanıtla.")

@bot.command()
async def unmute(ctx, member: discord.Member = None):
    if not can_mute(ctx):
        return await ctx.reply("yetkin yok.")

    target = None
    if ctx.message.reference:
        referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        target = referenced_msg.author
    elif member:
        target = member

    if target:
        try:
            await target.timeout(None)
            await ctx.reply(f"{target.display_name} kullanıcısının susturulması kaldırıldı.")
        except discord.Forbidden:
            await ctx.reply(f"{ctx.author.mention} yüksek.")
        except Exception as e:
            await ctx.send(f"Hata: {e}")
    else:
        await ctx.send("Kimin susturulmasını açacağımı belirtmedin.")

# --- VER KOMUTU ---
@bot.command()
async def ver(ctx):
    if not is_staff(ctx):
        return await ctx.reply("yetkin yok.")
    
    role = ctx.guild.get_role(VER_ROLE_ID)
    if not role:
        return await ctx.send("Hata: Rol bulunamadı.")

    await ctx.send(f"**{role.name}** rolü dağıtılıyor...")
    
    success_count = 0
    for member in ctx.guild.members:
        if not member.bot and role not in member.roles:
            try:
                await member.add_roles(role)
                success_count += 1
                await ctx.send(f"✅ **Log:** {member.display_name} kişisine **{role.name}** verildi.")
                await asyncio.sleep(0.6) # Rate limit koruması
            except:
                continue
    
    await ctx.send(f"İşlem bitti! Toplam {success_count} kişi rol aldı.")

# --- KANAL AYARLARI ---
@bot.command()
async def ayar(ctx):
    if not is_staff(ctx):
        return await ctx.reply("yetkin yok.")
    
    mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
    for channel_id in RESTRICTED_CHANNELS:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.set_permissions(mute_role, send_messages=False)
    
    await ctx.send("Kanal erişim ayarları güncellendi.")

# --- BAN VE GUARD ---
@bot.command()
async def ban(ctx, member: discord.Member = None, *, reason="Guard Koruması"):
    if not is_staff(ctx):
        return await ctx.reply("yetkin yok.")
    
    if member:
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.display_name} başarıyla banlandı.")
            
            author_id = ctx.author.id
            ban_counter[author_id] = ban_counter.get(author_id, 0) + 1
            
            if ban_counter[author_id] >= 3:
                await ctx.guild.ban(ctx.author, reason="Guard: 3 kişi banlama limiti.")
                await ctx.send(f"⚠️ **GUARD:** {ctx.author.name} ban limitini aştığı için sunucudan atıldı.")
                ban_counter[author_id] = 0
        except discord.Forbidden:
             await ctx.reply(f"{ctx.author.mention} yüksek.")
        except Exception as e:
            await ctx.send(f"Ban hatası: {e}")
    else:
        await ctx.send("Lütfen bir kullanıcıyı etiketleyin.")

async def reset_counter():
    while True:
        await asyncio.sleep(60)
        ban_counter.clear()

# --- ANA ÇALIŞTIRICI ---
async def start_bot():
    async with bot:
        keep_alive()
        bot.loop.create_task(reset_counter())
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except Exception as e:
        print(f"Bot başlatılamadı: {e}")
