# ========= IMPORTAÇÕES =========
import discord
from discord.ext import commands
import ollama
import os
import json
import random
import atexit
import requests
from bs4 import BeautifulSoup
import re
import asyncio
from datetime import datetime
from discord import FFmpegPCMAudio

ffmpeg_path = r"C:\Users\Hajik\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"

# ========= CONFIGURAÇÕES =========
TOKEN = 'coloque aqui o seu token do bot'
PREFIX = '!'

# ========= VERIFICAÇÃO DE DEPENDÊNCIAS =========
print("=== VERIFICAÇÃO DE DEPENDÊNCIAS ===")

dependencias_instaladas = False

try:
    import yt_dlp
    import nacl
    print("Todas as dependências carregadas")
    dependencias_instaladas = True
except ImportError as e:
    print(f"Dependências faltando: {e}")
    print("Tentando instalar automaticamente...")
    
    try:
        import subprocess
        import sys
        
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyNaCl"])
        
        import yt_dlp
        import nacl
        print("Dependências instaladas e carregadas!")
        dependencias_instaladas = True
    except Exception as install_error:
        print(f"Falha na instalação automática: {install_error}")
        print("Instale manualmente: pip install yt-dlp PyNaCl")

# ========= INICIALIZAÇÃO DO BOT =========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ========= CARREGAMENTO DE DADOS =========
caminho_pasta = os.path.dirname(__file__)
caminho_json = os.path.join(caminho_pasta, 'personalidade.json')
caminho_historico = os.path.join(caminho_pasta, 'historico.json')
caminho_eventos = os.path.join(caminho_pasta, 'eventos.json')

try:
    with open(caminho_json, 'r', encoding='utf-8') as f:
        personalidade = json.load(f)
    print(f"Personalidade carregada: {personalidade['nome']}")
except Exception as e:
    print(f"ERRO: personalidade.json não encontrado! → {e}")
    exit()

historico = {}
try:
    with open(caminho_historico, 'r', encoding='utf-8') as f:
        data = json.load(f)
        historico = {str(k): v for k, v in data.items()}
    print(f"Histórico carregado: {len(historico)} usuários")
except:
    historico = {}

# ========= CONFIGURAÇÕES =========
MODEL = 'llama3.2:3b'  # Modelo atualizado para llama3
PALAVRAS_BUSCA = [
    'como instalar', 'como baixar', 'tutorial', 'guia', 'passo a passo',
    'o que é', 'quem é', 'quando foi', 'onde fica', 
    'atual', 'notícia', 'pesquisa', 'documentação',
    'pip install', 'npm install', 'comando', 'terminal',
    'configurar', 'setup', 'instalação', 'download',
    'django', 'python', 'framework', 'programação'
]

# ========= SISTEMA DE CACHE (50% CHANCE) =========
CACHE_RESPOSTAS = {
    "oi": "Oi! Tô aqui pra te ajudar! ❤️",
    "tudo bem": "Tô ótima, e tu? 😊",
    "quem é você": "Sou Alice, sua IA fofa e rápida! 🤖",
    "obrigado": "De boa, amor! 😍",
    "tchau": "Tchau, volta sempre! 👋",
    "oq sobra para o betinha?": "SOBROU NADA KKKKKKKKKKKKKKKKKKKKKKKK ❤️"
}

# ========= SISTEMA DE MÚSICA REAL =========
fila_musica = {}

if dependencias_instaladas:
    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'
    }

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

    class YTDLSource(discord.PCMVolumeTransformer):
        def __init__(self, source, *, data, volume=0.5):
            super().__init__(source, volume)
            self.data = data
            self.title = data.get('title')
            self.url = data.get('url')

        @classmethod
        async def from_url(cls, url, *, loop=None, stream=True):
            loop = loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            
            if 'entries' in data:
                data = data['entries'][0]
            
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(FFmpegPCMAudio(filename, executable=ffmpeg_path, **ffmpeg_options), data=data)

# ========= SISTEMA DE EVENTOS =========
eventos_ativos = {}

def carregar_eventos():
    try:
        with open(caminho_eventos, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def salvar_eventos():
    try:
        with open(caminho_eventos, 'w', encoding='utf-8') as f:
            json.dump(eventos_ativos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar eventos: {e}")

# ========= FUNÇÕES AUXILIARES =========
def aplicar_estilo(texto):
    emoji_map = {
        'smile': '😊', 'heart': '❤️', 'sparkles': '✨', 'fire': '🔥',
        'robot': '🤖', 'bulb': '💡', 'star': '⭐', 'thumbsup': '👍',
        'clap': '👏', 'rocket': '🚀'
    }

    for nome, emoji in emoji_map.items():
        texto = texto.replace(f':{nome}:', emoji)

    if random.random() < 0.50:
        emojis_finais = ['😊', '❤️', '✨', '🔥', '🤖']
        texto += " " + random.choice(emojis_finais)

    return texto

def buscar_no_cache_inteligente(pergunta):
    pergunta_lower = pergunta.lower().strip()
    
    if random.random() > 0.50:
        return None
    
    if pergunta_lower in CACHE_RESPOSTAS:
        return CACHE_RESPOSTAS[pergunta_lower]
    
    return None

def deve_pesquisar(pergunta):
    pergunta_lower = pergunta.lower()
    
    palavras_tecnicas = [
        'como instalar', 'pip install', 'baixar', 'download', 'tutorial',
        'configurar', 'setup', 'instalação', 'comando', 'terminal'
    ]
    
    if any(palavra in pergunta_lower for palavra in palavras_tecnicas):
        return True
    
    return random.random() < 0.90

# Funções de corte removidas para evitar "continuação"

def buscar_google(pergunta):
    try:
        query = pergunta.replace(' ', '+')
        
        url = f"https://www.google.com/search?q={query}+site:docs.djangoproject.com+OR+site:stackoverflow.com+OR+site:realpython.com+OR+site:python.org+OR+site:pypi.org+OR+site:github.com&hl=pt-BR&num=6"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        resultados = []
        
        for link in soup.find_all('a', href=re.compile(r'^/url\?q='))[:6]:
            try:
                url_real = re.findall(r'q=(.*?)&', link['href'])[0]
                
                dominios_confiaveis = [
                    'docs.djangoproject.com', 'stackoverflow.com', 
                    'realpython.com', 'python.org', 'pypi.org',
                    'github.com', 'w3schools.com', 'geeksforgeeks.org'
                ]
                
                if any(dominio in url_real for dominio in dominios_confiaveis):
                    titulo_element = link.find('h3') or link
                    titulo = titulo_element.get_text().strip() if titulo_element else "Sem título"
                    
                    if titulo and len(titulo) > 10:
                        resultados.append({
                            'titulo': titulo,
                            'url': url_real,
                            'fonte': next((d for d in dominios_confiaveis if d in url_real), 'outra')
                        })
            except Exception as e:
                continue
        
        if resultados:
            ordem_fontes = ['docs.djangoproject.com', 'python.org', 'pypi.org', 'stackoverflow.com', 'realpython.com']
            resultados_ordenados = sorted(
                resultados, 
                key=lambda x: ordem_fontes.index(x['fonte']) if x['fonte'] in ordem_fontes else 999
            )
            
            formatados = []
            for resultado in resultados_ordenados[:3]:
                emoji = {
                    'docs.djangoproject.com': '📚',
                    'python.org': '🐍', 
                    'pypi.org': '📦',
                    'stackoverflow.com': '💡',
                    'realpython.com': '🎯'
                }.get(resultado['fonte'], '🔗')
                
                formatados.append(f"{emoji} **{resultado['titulo']}**\n{resultado['url']}")
            
            return "\n\n".join(formatados)
        else:
            return "🔍 **Pesquisa:** Não encontrei resultados em fontes confiáveis."
            
    except Exception as e:
        print(f"Erro na busca Google: {e}")
        return "❌ **Pesquisa:** Erro temporário na busca."

async def enviar_resposta_longa(message, texto):
    if len(texto) <= 1900:
        await message.reply(texto)
        return
    
    partes = []
    texto_restante = texto
    
    while texto_restante:
        if len(texto_restante) <= 1900:
            partes.append(texto_restante)
            break
        
        parte = texto_restante[:1900]
        ultimo_ponto = parte.rfind('.')
        ultima_quebra = parte.rfind('\n')
        
        ponto_quebra = max(ultimo_ponto, ultima_quebra)
        
        if ponto_quebra != -1:
            partes.append(texto_restante[:ponto_quebra + 1])
            texto_restante = texto_restante[ponto_quebra + 1:]
        else:
            ultimo_espaco = parte.rfind(' ')
            if ultimo_espaco != -1:
                partes.append(texto_restante[:ultimo_espaco])
                texto_restante = texto_restante[ultimo_espaco + 1:]
            else:
                partes.append(parte)
                texto_restante = texto_restante[1900:]
    
    for i, parte in enumerate(partes):
        if i == 0:
            await message.reply(parte)
        else:
            if i < len(partes) - 1:
                await message.channel.send(parte + "\n\n**...**")
            else:
                await message.channel.send(parte)

# ========= COMANDOS BÁSICOS =========
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command(name='ajuda')
async def ajuda(ctx):
    musica_status = "✅" if dependencias_instaladas else "❌"
    
    embed = discord.Embed(
        title=f"🤖 COMANDOS DA {personalidade['nome'].upper()}",
        description=f"Olá! Eu sou a **{personalidade['nome']}** 😊\nAqui estão meus comandos:",
        color=0x00ff00
    )
    
    embed.add_field(
        name="⚙️ BÁSICOS",
        value=(
            "`!ping` - Teste de conexão\n"
            "`!info` - Minhas informações\n" 
            "`!ajuda` - Esta mensagem\n"
            "`!reset` - Reinicia IA (emergência)\n"
            "`Mencione @Alice` - Chat com IA"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛡️ MODERAÇÃO", 
        value=(
            "`!expulsar @user [motivo]` - Expulsa usuário\n"
            "`!banir @user [motivo]` - Bane usuário\n"
            "`!clear [quantidade]` - Limpa mensagens (max 100)"
        ),
        inline=False
    )
    
    if dependencias_instaladas:
        embed.add_field(
            name=f"🎵 MÚSICA {musica_status}",
            value=(
                "`!play <música/url>` - Toca música no canal\n"
                "`!pause` - Pausa a música\n" 
                "`!resume` - Continua a música\n"
                "`!stop` - Para a música\n"
                "`!fila` - Mostra fila de músicas"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name=f"🎵 MÚSICA {musica_status}",
            value=(
                "Sistema de música indisponível\n"
                "Instale: `pip install yt-dlp PyNaCl`"
            ),
            inline=False
        )
    
    embed.add_field(
        name="🎉 EVENTOS",
        value=(
            "`!evento <nome> <data> <hora> [desc]` - Cria evento\n"
            "`!eventos` - Lista eventos ativos\n"
            "Ex: `!evento Festa 25/12 20:00 Confraternização`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="😂 DIVERSÃO", 
        value=(
            "`!meme <texto1> | <texto2>` - Gera meme\n"
            "`!fun <comando>` - Comandos engraçados\n"
            "Comandos: `dado`, `moeda`, `piada`, `abraço`, `danca`"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='info')
async def info(ctx):
    embed = discord.Embed(
        title=f"🤖 {personalidade['nome']}",
        description=personalidade['personalidade'],
        color=0x0099ff
    )
    
    embed.add_field(name="🎭 Personalidade", value=personalidade['tom'], inline=True)
    embed.add_field(name="🎵 Música", value="✅ Disponível" if dependencias_instaladas else "❌ Instale dependências", inline=True)
    embed.add_field(name="💾 Histórico", value=f"{len(historico)} usuários", inline=True)
    
    if 'gírias' in personalidade.get('estilo_escrita', {}):
        gírias = ', '.join(personalidade['estilo_escrita']['gírias'][:3])
        embed.add_field(name="🗣️ Gírias", value=gírias, inline=True)
    
    embed.set_footer(text="Desenvolvida para trazer diversão e utilidade!")
    
    await ctx.send(embed=embed)

@bot.command(name='reset')
async def reset(ctx):
    user_id = str(ctx.author.id)
    if user_id in historico:
        del historico[user_id]
    await ctx.send("🔄 Sistema de IA reiniciado! Histórico limpo.")

# ========= COMANDOS DE MODERAÇÃO =========
@bot.command(name='expulsar')
@commands.has_permissions(kick_members=True)
async def expulsar(ctx, membro: discord.Member, *, motivo="Motivo não especificado"):
    try:
        await membro.send(f"⚡ Você foi expulso do servidor **{ctx.guild.name}**\n**Motivo:** {motivo}")
        await membro.kick(reason=motivo)
        await ctx.send(f"✅ {membro.mention} foi expulso!\n**Motivo:** {motivo}")
    except Exception as e:
        await ctx.send(f"❌ Erro ao expulsar: {e}")

@bot.command(name='banir')
@commands.has_permissions(ban_members=True)
async def banir(ctx, membro: discord.Member, *, motivo="Motivo não especificado"):
    try:
        await membro.send(f"🔨 Você foi banido do servidor **{ctx.guild.name}**\n**Motivo:** {motivo}")
        await membro.ban(reason=motivo, delete_message_days=0)
        await ctx.send(f"✅ {membro.mention} foi banido!\n**Motivo:** {motivo}")
    except Exception as e:
        await ctx.send(f"❌ Erro ao banir: {e}")

@bot.command(name='clear')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, quantidade: int = 5):
    quantidade = min(quantidade, 100)
    deleted = await ctx.channel.purge(limit=quantidade + 1)
    msg = await ctx.send(f"🗑️ {len(deleted) - 1} mensagens foram deletadas!")
    await asyncio.sleep(3)
    await msg.delete()

# ========= COMANDOS DE MÚSICA REAL =========
@bot.command(name='play')
async def play(ctx, *, query):
    if not dependencias_instaladas:
        await ctx.send("❌ Sistema de música não disponível. Instale: `pip install yt-dlp PyNaCl`")
        return
    
    if not ctx.author.voice:
        await ctx.send("❌ Você precisa estar em um canal de voz!")
        return
    
    try:
        voice_channel = ctx.author.voice.channel
        voice_client = ctx.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)
        
        if ctx.guild.id not in fila_musica:
            fila_musica[ctx.guild.id] = []
        
        loading_msg = await ctx.send("🔄 Carregando música...")
        
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        
        fila_musica[ctx.guild.id].append(player)
        
        await loading_msg.delete()
        
        if not voice_client.is_playing():
            await tocar_proxima(ctx, voice_client)
        else:
            await ctx.send(f"🎵 Adicionado à fila: **{player.title}**")
            
    except Exception as e:
        await ctx.send(f"❌ Erro ao tocar música: {e}")

async def tocar_proxima(ctx, voice_client=None):
    if not dependencias_instaladas:
        return
        
    if voice_client is None:
        voice_client = ctx.guild.voice_client
    
    guild_id = ctx.guild.id
    
    if guild_id not in fila_musica or not fila_musica[guild_id]:
        return
    
    player = fila_musica[guild_id].pop(0)
    
    def after_playing(error):
        if error:
            print(f'Erro no player: {error}')
        if bot.loop.is_running():
            asyncio.run_coroutine_threadsafe(tocar_proxima(ctx, voice_client), bot.loop)
    
    try:
        voice_client.play(player, after=after_playing)
        await ctx.send(f"🎶 **Tocando agora:** {player.title}")
    except Exception as e:
        await ctx.send(f"❌ Erro ao tocar: {e}")
        if bot.loop.is_running():
            asyncio.run_coroutine_threadsafe(tocar_proxima(ctx, voice_client), bot.loop)

@bot.command(name='pause')
async def pause(ctx):
    if not dependencias_instaladas:
        await ctx.send("❌ Sistema de música não disponível")
        return
        
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ Música pausada!")

@bot.command(name='resume')
async def resume(ctx):
    if not dependencias_instaladas:
        await ctx.send("❌ Sistema de música não disponível")
        return
        
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ Música continuando!")

@bot.command(name='stop')
async def stop(ctx):
    if not dependencias_instaladas:
        await ctx.send("❌ Sistema de música não disponível")
        return
        
    voice_client = ctx.guild.voice_client
    if voice_client:
        if ctx.guild.id in fila_musica:
            fila_musica[ctx.guild.id].clear()
        voice_client.stop()
        await ctx.send("⏹️ Música parada e fila limpa!")

@bot.command(name='fila')
async def fila(ctx):
    if not dependencias_instaladas:
        await ctx.send("❌ Sistema de música não disponível")
        return
        
    guild_id = ctx.guild.id
    
    if guild_id not in fila_musica or not fila_musica[guild_id]:
        await ctx.send("📭 Fila vazia! Use `!play <música>` para adicionar músicas.")
        return
    
    embed = discord.Embed(title="📋 Fila de Músicas", color=0x9B59B6)
    
    lista_musicas = ""
    for i, player in enumerate(fila_musica[guild_id][:10], 1):
        lista_musicas += f"`{i}.` {player.title}\n"
    
    embed.description = lista_musicas
    embed.set_footer(text=f"Total: {len(fila_musica[guild_id])} músicas na fila")
    
    await ctx.send(embed=embed)

@bot.command(name='sair')
async def sair(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        if ctx.guild.id in fila_musica:
            fila_musica[ctx.guild.id].clear()
        await voice_client.disconnect()
        await ctx.send("👋 Saindo do canal de voz!")

@bot.command(name='fixmusic')
async def fixmusic(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        voice_client.stop()
        if ctx.guild.id in fila_musica:
            fila_musica[ctx.guild.id].clear()
        await voice_client.disconnect()
        await ctx.send("🔧 Música reiniciada!")

# ========= COMANDOS DE EVENTOS =========
@bot.command(name='evento')
async def evento(ctx, nome, data, hora, *, descricao="Sem descrição"):
    try:
        data_hora = datetime.strptime(f"{data} {hora}", "%d/%m %H:%M")
        data_hora = data_hora.replace(year=datetime.now().year)
        
        evento_id = str(len(eventos_ativos) + 1)
        eventos_ativos[evento_id] = {
            "nome": nome,
            "data": data_hora.isoformat(),
            "descricao": descricao,
            "criador": ctx.author.id,
            "participantes": []
        }
        
        salvar_eventos()
        
        embed = discord.Embed(
            title=f"🎉 Novo Evento: {nome}",
            description=descricao,
            color=0x00ff00
        )
        embed.add_field(name="📅 Data", value=data_hora.strftime("%d/%m às %H:%M"), inline=True)
        embed.add_field(name="👥 Participantes", value="0", inline=True)
        embed.set_footer(text=f"ID: {evento_id} • Criado por {ctx.author.display_name}")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        
    except ValueError:
        await ctx.send("❌ Formato de data/hora inválido! Use: DD/MM HH:MM")

@bot.command(name='eventos')
async def eventos(ctx):
    if not eventos_ativos:
        await ctx.send("📭 Não há eventos ativos no momento!")
        return
    
    embed = discord.Embed(title="📅 Eventos Ativos", color=0x0099ff)
    
    for evento_id, evento in eventos_ativos.items():
        data = datetime.fromisoformat(evento['data'])
        embed.add_field(
            name=f"{evento_id}. {evento['nome']}",
            value=f"📅 {data.strftime('%d/%m às %H:%M')}\n👥 {len(evento['participantes'])} participantes",
            inline=False
        )
    
    await ctx.send(embed=embed)

# ========= COMANDOS DE DIVERSÃO =========
@bot.command(name='meme')
async def meme(ctx, *, texto):
    if '|' not in texto:
        await ctx.send("❌ Separe os textos com |")
        return
    
    texto_superior, texto_inferior = texto.split('|', 1)
    
    templates_meme = [
        "https://i.imgflip.com/30b1gx.jpg",
        "https://i.imgflip.com/1g8my4.jpg", 
        "https://i.imgflip.com/1bij.jpg",
    ]
    
    template = random.choice(templates_meme)
    
    embed = discord.Embed(title="😂 Meme Gerado!", color=0xff9900)
    embed.add_field(name="📝 Texto Superior", value=texto_superior.strip(), inline=False)
    embed.add_field(name="📝 Texto Inferior", value=texto_inferior.strip(), inline=False)
    embed.set_image(url=template)
    
    await ctx.send(embed=embed)

@bot.command(name='fun')
async def fun(ctx, comando="piada"):
    comandos_engracados = {
        "dado": f"🎲 {ctx.author.mention} rolou um **{random.randint(1, 6)}**",
        "moeda": f"🪙 {ctx.author.mention} {'**CARA**' if random.random() > 0.5 else '**COROA**'}",
        "piada": random.choice([
            "Por que o Python foi ao psicólogo? Porque tinha muitos complexos! 🐍",
            "Qual é o café mais rápido do mundo? O Java! ☕",
            "Por que os elétrons nunca são presos? Porque eles sempre conseguem um bom condutor! ⚡"
        ]),
        "abraço": f"🤗 {ctx.author.mention} deu um abraço coletivo! *abraços para todos*",
        "danca": f"💃 {ctx.author.mention} começou a dançar! *solta a batida*"
    }
    
    if comando in comandos_engracados:
        await ctx.send(comandos_engracados[comando])
    else:
        await ctx.send("❌ Comando engraçado não encontrado! Use: `dado`, `moeda`, `piada`, `abraço`, `danca`")

# ========= SISTEMA DE IA =========
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if bot.user in message.mentions:
        pergunta = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if not pergunta:
            await message.reply(aplicar_estilo(personalidade['frases_fixas']['saudacao']))
            return

        if len(pergunta) < 2 or pergunta.lower() in ['cade tu fia', 'alice?', '...', '?', '??', '???']:
            await message.reply("🤔 Oi? Fala direito comigo, amor! 😊")
            return

        resposta_cache = buscar_no_cache_inteligente(pergunta)
        if resposta_cache:
            await message.reply(aplicar_estilo(resposta_cache))
            return

        async def processar_ia():
            try:
                async with message.channel.typing():
                    user_id = str(message.author.id)
                    msgs = historico.get(user_id, [])
                    msgs.append({'role': 'user', 'content': pergunta})

                    contexto = ""
                    if deve_pesquisar(pergunta):
                        contexto = buscar_google(pergunta)
                        if contexto and "não encontrei" not in contexto.lower() and "erro" not in contexto.lower():
                            msgs.append({'role': 'system', 'content': f"CONTEXTO DA PESQUISA: {contexto}\n\nUse estas informações para responder de forma PRÁTICA e DIRETA. Inclua comandos exatos quando for sobre instalação ou programação."})

                    mensagens_ollama = [{
                        'role': 'system',
                        'content': f"""Você é {personalidade['nome']}, {personalidade['personalidade']}.

🚀 **SEJA SUPER PRÁTICA E DIRETA!**

**REGRA DE OURO:** Respostas COMPACTAS mas COMPLETAS!

- Para instalação: Apenas comandos essenciais em ```bash
- Para código: Apenas o necessário para funcionar
- Para tutoriais: Apenas passos críticos
- **COMPLETE SEMPRE** - não corte no meio de código!

Exemplo BOM (Java):
```java
public class Main {{
    public static void main(String[] args) {{
        System.out.println("Hello Java!");
    }}
}}
bash
javac Main.java
java Main
textExemplo RUIM:
"Primeiro você precisa baixar o JDK, depois criar uma classe..."
"""
                    }]
                    for msg in msgs[-4:]:
                        mensagens_ollama.append(msg)

                    try:
                        resposta = await asyncio.wait_for(
                            asyncio.to_thread(
                                ollama.chat,
                                model=MODEL,
                                messages=mensagens_ollama,
                                options={'num_predict': 800, 'temperature': 0.7}
                            ),
                            timeout=180.0
                        )
                        texto = resposta['message']['content'].strip()
                        texto = aplicar_estilo(texto)
                    except asyncio.TimeoutError:
                        texto = "⏰ Nossa, tô com a cabeça cheia hoje! Pode repetir? 😅"
                
                    # Sistema de continuação removido para evitar mensagens extras

                    msgs.append({'role': 'assistant', 'content': texto})
                    historico[user_id] = msgs[-6:]

                    resposta_final = texto
                    if contexto and "não encontrei" not in contexto.lower() and "erro" not in contexto.lower():
                        resposta_final = f"{texto}\n\n**🔍 Fontes pesquisadas:**\n{contexto}"

                    await enviar_resposta_longa(message, resposta_final)
                    
            except Exception as e:
                print(f"Erro no processamento da IA: {e}")
                await message.reply("❌ Oops, deu um erro aqui! Tenta de novo? 😅")

        asyncio.create_task(processar_ia())

@bot.event
async def on_ready():
    print(f"{aplicar_estilo(personalidade['frases_fixas']['saudacao'])}")
    print(f"ALICE IA ONLINE: {bot.user}")
    eventos_ativos.update(carregar_eventos())
    print(f"Eventos carregados: {len(eventos_ativos)}")

def salvar_historico():
    try:
        with open(caminho_historico, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
        print(f"Histórico salvo: {len(historico)} usuários")
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")

atexit.register(salvar_historico)
atexit.register(salvar_eventos)
print("Iniciando Alice IA...")
bot.run(TOKEN)