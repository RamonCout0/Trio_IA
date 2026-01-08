import discord
from discord.ext import commands
from discord.ui import Button, View
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime, timedelta

# Carrega Token
load_dotenv()
TOKEN = os.getenv('ADMIN_TOKEN')

# Configurações
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True 

bot = commands.Bot(command_prefix='.', intents=intents)
bot.remove_command('help') # Remove o help feio original para criarmos um bonito

# --- CONFIGURAÇÃO DA CATEGORIA ---
TARGET_CATEGORY_NAME = "ADMIN" 
LOG_CHANNEL_NAME = "logs-gerais"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="A porta 404 é a solução."
    ))
    print(f"🛡️ Admin Supremo V3 (Completo) Online: {bot.user}")

# --- FUNÇÃO ÚTIL: ACHA OU CRIA A CATEGORIA ADMIN ---
async def get_admin_category(guild):
    category = discord.utils.get(guild.categories, name=TARGET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(TARGET_CATEGORY_NAME)
    return category

# ==============================================================================
# 1. MODERAÇÃO (BAN, KICK, LOCK) - ELES VOLTARAM!
# ==============================================================================

@bot.command(name="kick", aliases=["expulsar"])
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Expulsa um membro"""
    if member == ctx.author:
        return await ctx.send("❌ Você não pode se expulsar.")
    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member.name}** foi expulso. Motivo: {reason or 'Não informado'}")

@bot.command(name="ban", aliases=["banir"])
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """Bane um membro"""
    if member == ctx.author:
        return await ctx.send("❌ Você não pode se banir.")
    await member.ban(reason=reason)
    await ctx.send(f"🚫 **{member.name}** levou BAN! Motivo: {reason or 'Não informado'}")

@bot.command(name="unban", aliases=["desbanir"])
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_name):
    """Desbane pelo nome ou ID"""
    banned_users = [entry async for entry in ctx.guild.bans()]
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == user_name or str(user.id) == user_name:
            await ctx.guild.unban(user)
            await ctx.send(f"✅ **{user.name}** foi perdoado.")
            return
    await ctx.send(f"❌ Não achei `{user_name}` na lista de banidos.")

@bot.command(name="lock", aliases=["trancar"])
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Tranca o canal"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 **Canal TRANCADO.**")

@bot.command(name="unlock", aliases=["destrancar"])
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Destranca o canal"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 **Canal DESTRANCADO.**")

@bot.command(name="limpar", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Limpa mensagens"""
    await ctx.channel.purge(limit=amount+1)

# ==============================================================================
# 2. SISTEMA DE TICKETS (DENTRO DO ADMIN)
# ==============================================================================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="📩 Abrir Ticket", style=discord.ButtonStyle.green, custom_id="criar_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = await get_admin_category(guild)

        channel_name = f"ticket-{interaction.user.name.lower()}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if existing_channel:
            await interaction.response.send_message(f"❌ Já existe: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        await interaction.response.send_message(f"✅ Ticket criado: {channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="🎫 Suporte", description="Explique seu caso. A staff já vem.", color=0x00ff00)
        await channel.send(f"{interaction.user.mention}", embed=embed, view=CloseTicketView())

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.red, custom_id="fechar_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⚠️ Fechando...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="Central de Ajuda", description="Clique abaixo para falar com a Staff.", color=0x2f3136)
    await ctx.send(embed=embed, view=TicketView())

# ==============================================================================
# 3. SISTEMA DE LOGS (DENTRO DO ADMIN)
# ==============================================================================

async def get_log_channel(guild):
    category = await get_admin_category(guild)
    channel = discord.utils.get(category.text_channels, name=LOG_CHANNEL_NAME)
    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        channel = await guild.create_text_channel(LOG_CHANNEL_NAME, category=category, overwrites=overwrites)
    return channel

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    channel = await get_log_channel(message.guild)
    if channel:
        embed = discord.Embed(title="🗑️ Apagou Mensagem", color=0xff0000)
        embed.add_field(name="Quem", value=message.author.mention, inline=True)
        embed.add_field(name="Onde", value=message.channel.mention, inline=True)
        embed.add_field(name="O que", value=message.content or "Arquivo", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot: return
    if before.content == after.content: return
    channel = await get_log_channel(before.guild)
    if channel:
        embed = discord.Embed(title="✏️ Editou Mensagem", color=0xffa500)
        embed.add_field(name="Quem", value=before.author.mention, inline=True)
        embed.add_field(name="Onde", value=before.channel.mention, inline=True)
        embed.add_field(name="Antes", value=before.content, inline=False)
        embed.add_field(name="Depois", value=after.content, inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    channel = await get_log_channel(member.guild)
    if not channel: return
    if before.channel is None and after.channel is not None:
        await channel.send(embed=discord.Embed(description=f"🔊 **{member.name}** entrou em `{after.channel.name}`", color=0x00ff00))
    elif before.channel is not None and after.channel is None:
        await channel.send(embed=discord.Embed(description=f"🔇 **{member.name}** saiu de `{before.channel.name}`", color=0xff0000))

# ==============================================================================
# 4. EXTRAS (EVENTO, SAY, HELP)
# ==============================================================================

@bot.command()
@commands.has_permissions(manage_events=True)
async def evento(ctx):
    """Cria evento interativo"""
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        await ctx.send("📅 **Criar Evento**\n1. Nome?")
        nome = (await bot.wait_for('message', check=check, timeout=60)).content
        await ctx.send("2. Descrição?")
        desc = (await bot.wait_for('message', check=check, timeout=60)).content
        await ctx.send("3. Daqui a quantas horas? (Número)")
        horas = int((await bot.wait_for('message', check=check, timeout=60)).content)
        
        start = datetime.now().astimezone() + timedelta(hours=horas)
        # Cria evento silencioso (sem everyone)
        event = await ctx.guild.create_scheduled_event(
            name=nome, description=desc, start_time=start, end_time=start + timedelta(hours=2),
            channel=ctx.guild.voice_channels[0] if ctx.guild.voice_channels else None,
            entity_type=discord.EntityType.voice, privacy_level=discord.PrivacyLevel.guild_only
        )
        await ctx.send(f"✅ Evento criado: {event.url}")
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, mensagem):
    await ctx.message.delete()
    if "|" in mensagem:
        titulo, conteudo = mensagem.split("|", 1)
        embed = discord.Embed(title=titulo.strip(), description=conteudo.strip(), color=0x2f3136)
        embed.set_footer(text=f"Enviado por: {ctx.author.name}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(mensagem)

@bot.command(name="help", aliases=["ajuda"])
async def help_command(ctx):
    embed = discord.Embed(title="🛡️ Central de Comando", description="Lista de ordens disponíveis:", color=0x000000)
    
    embed.add_field(name="🔨 Moderação", value="`.ban @user` - Banir\n`.kick @user` - Expulsar\n`.unban nome` - Desbanir\n`.lock` / `.unlock` - Trancar canal\n`.limpar 10` - Limpar chat", inline=False)
    
    embed.add_field(name="⚙️ Sistemas", value="`.setup_ticket` - Criar painel de suporte\n`.evento` - Criar evento agendado\n`.say Texto` - Bot fala (use | para título)", inline=False)
    
    embed.set_footer(text="Logs e Tickets ficam na categoria ADMIN")
    await ctx.send(embed=embed)

bot.run(TOKEN)