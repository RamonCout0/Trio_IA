import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('Selena_Token')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# --- CONFIGURAÇÕES DO YT-DLP ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0', 
    'nocheckcertificate': True,
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# --- O SEGREDO MULTI-SERVER ---
# Cada servidor terá sua própria "ficha" guardada aqui pelo ID
server_data = {} 

def get_server(guild_id):
    """Cria ou recupera a ficha do servidor"""
    if guild_id not in server_data:
        server_data[guild_id] = {
            'queue': [],           # Fila específica deste server
            'current': None,       # Música atual deste server
            'radio': False         # Modo rádio deste server
        }
    return server_data[guild_id]

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name="Ao seu comando !play"
    ))
    print(f"🌑 Selena V4 (Multi-Server) Online: {bot.user}")


async def search_related_song(ctx, last_song):
    data = get_server(ctx.guild.id)
    try:
        clean_title = last_song.replace("(Official Video)", "").strip()
        search_query = f"ytsearch5:{clean_title} official audio"
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(search_query, download=False))
        
        video = None
        if 'entries' in info and len(info['entries']) > 1:
            video = info['entries'][1] # Tenta pegar a segunda
        elif 'entries' in info and len(info['entries']) > 0:
            video = info['entries'][0]
        else:
            video = info

        if video:
            data['queue'].append((video['url'], video['title']))
            play_next(ctx)
            await ctx.send(f"♾️ **Modo Eterna:** Invoquei `{video['title']}`.")
        else:
            raise Exception("Sem sugestões")
            
    except Exception:
        data['radio'] = False
        await ctx.send("🌑 *Silêncio... (Modo Eterna desligado)*")

# --- TOCADOR (PLAY NEXT) ---
def play_next(ctx):
    # Pega os dados EXCLUSIVOS deste servidor
    data = get_server(ctx.guild.id)
    
    if len(data['queue']) > 0:
        url, title = data['queue'].pop(0)
        data['current'] = title
        
        voice_client = ctx.voice_client
        if voice_client:
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            voice_client.play(source, after=lambda e: play_next(ctx))
            
            asyncio.run_coroutine_threadsafe(
                ctx.send(f"🎵 **Dedilhando:** `{title}`"), bot.loop
            )
    else:
        if data['radio'] and data['current']:
            asyncio.run_coroutine_threadsafe(search_related_song(ctx, data['current']), bot.loop)
        else:
            data['current'] = None
            asyncio.run_coroutine_threadsafe(ctx.send("🌑 *Fim do repertório.*"), bot.loop)

# --- COMANDOS ---

@bot.command(name="play", aliases=["p"])
async def play(ctx, *, busca: str):
    if not ctx.author.voice:
        return await ctx.send("🌑 *Entre no canal de voz.*")
    
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    
    msg = await ctx.send("🔎 *Buscando...*")
    data = get_server(ctx.guild.id) # Pega a gaveta deste server
    
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(f"ytsearch:{busca}", download=False))
        
        if 'entries' in info and len(info['entries']) > 0:
            video = info['entries'][0]
        else:
            video = info

        url = video['url']
        title = video['title']
        
        if ctx.voice_client.is_playing():
            data['queue'].append((url, title))
            await msg.edit(content=f"📜 **Adicionado:** `{title}`")
        else:
            data['queue'].append((url, title))
            await msg.delete()
            play_next(ctx)

    except Exception as e:
        await msg.edit(content="❌ *Erro ao buscar.*")

@bot.command(name="eterna", aliases=["radio"])
async def radio_toggle(ctx):
    data = get_server(ctx.guild.id)
    data['radio'] = not data['radio']
    
    status = "ATIVADO" if data['radio'] else "DESATIVADO"
    await ctx.send(f"♾️ **Modo Eterna:** {status}")
    
    if data['radio'] and not ctx.voice_client.is_playing() and data['current']:
        await search_related_song(ctx, data['current'])

@bot.command(name="skip", aliases=["s"])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("💨 *Pulando...*")

@bot.command(name="fila", aliases=["q"])
async def queue(ctx):
    data = get_server(ctx.guild.id)
    if not data['queue']:
        return await ctx.send("📜 *Fila vazia.*")
    
    lista = "\n".join([f"{i+1}. {t[1]}" for i, t in enumerate(data['queue'][:10])])
    await ctx.send(f"**📜 Fila:**\n{lista}")

@bot.command(name="stop")
async def stop(ctx):
    data = get_server(ctx.guild.id)
    data['queue'] = []
    data['current'] = None
    data['radio'] = False
    
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋")

bot.run(TOKEN)