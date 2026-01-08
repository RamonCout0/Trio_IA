import discord
from discord.ext import commands
import ollama
import os
import json
import random
import asyncio
import atexit
from dotenv import load_dotenv

# ========= CONFIGURAÇÃO GERAL =========
load_dotenv()
TOKEN = os.getenv('ALICE_TOKEN')
RAMON_USER_ID = "657972622809759745"

# --- A DUPLA DINÂMICA (Seus Modelos) ---
# O Cérebro: Inteligente, sabe programar, personalidade forte (3B para caber na RAM)
MODELO_CEREBRO = 'qwen2.5-coder:3b'

# O Secretário: Leve, rápido, só serve para resumir textos em background
MODELO_SECRETARIO = 'llama3.2:1b'

CHANCE_DE_FALAR = 0.02 

# Configuração do Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)

# ========= CAMINHOS DOS ARQUIVOS =========
caminho_pasta = os.path.dirname(__file__)
caminho_json_pers = os.path.join(caminho_pasta, 'personalidade.json')
caminho_cache = os.path.join(caminho_pasta, 'cache_inteligente.json')

# ========= SISTEMA DE PERSONALIDADE =========
def carregar_personalidade_json():
    """Lê o arquivo personalidade.json e monta o prompt do sistema."""
    try:
        with open(caminho_json_pers, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Monta um prompt robusto para o Qwen
        prompt = f"""
        ### INSTRUÇÕES DO SISTEMA
        NOME: {dados.get('nome', 'Alice')}
        CRIADO POR: {dados.get('criador', 'Ramon')}
        
        ### PERSONALIDADE (SOCIAL)
        {dados.get('identidade', {}).get('tom', 'Seja direta.')}
        {dados.get('identidade', {}).get('estilo', 'Engenheira Sênior.')}
        Interesses: {dados.get('identidade', {}).get('hobbies', 'Tech e Code.')}
        
        ### REGRAS TÉCNICAS (IMPORTANTÍSSIMO)
        {dados.get('regras_tecnicas', {}).get('foco', 'Clean Code.')}
        {dados.get('regras_tecnicas', {}).get('proibicoes', 'Não invente código.')}
        
        ### OBJETIVO FINAL
        {dados.get('sistema', 'Priorize a precisão técnica.')}
        """
        return prompt
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível ler personalidade.json ({e}). Usando padrão.")
        return "Você é Alice, uma assistente de programação Sênior e irônica."

# Carrega o prompt ao iniciar
SYSTEM_PROMPT = carregar_personalidade_json()

# ========= MEMÓRIA E CACHE (HÍBRIDO) =========
class CacheInteligente:
    def __init__(self):
        self.cache = self.carregar_cache()
    
    def carregar_cache(self):
        try:
            if os.path.exists(caminho_cache):
                with open(caminho_cache, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"resumo_global": "Nada conversado ainda."}
        except: return {"resumo_global": ""}
    
    def salvar_cache(self):
        try:
            with open(caminho_cache, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cache: {e}")
    
    def buscar_exata(self, pergunta):
        """Procura respostas prontas (ex: 'oi', 'quem é voce')"""
        chave = pergunta.lower().strip()
        # Ignora a chave de memória interna
        if chave in self.cache and chave != "resumo_global":
            return self.cache[chave]
        return None

    def atualizar_resumo(self, resumo):
        """Atualiza apenas a memória de longo prazo"""
        self.cache["resumo_global"] = resumo
        self.salvar_cache()
    
    def adicionar_resposta(self, pergunta, resposta):
        """Salva nova resposta no cache (opcional)"""
        self.cache[pergunta.lower().strip()] = resposta
        self.salvar_cache()

cache = CacheInteligente()

class HistoricoCiclico:
    """Gerencia o histórico de curto prazo (últimas mensagens da conversa atual)"""
    def __init__(self):
        self.historico = {}
    
    def adicionar(self, user_id, role, content):
        if user_id not in self.historico: self.historico[user_id] = []
        self.historico[user_id].append({'role': role, 'content': content})
        # Mantém apenas as últimas 10 trocas para não estourar o contexto da IA
        self.historico[user_id] = self.historico[user_id][-10:]

    def obter(self, user_id):
        return self.historico.get(user_id, [])

historico = HistoricoCiclico()

# ========= FUNÇÕES AUXILIARES =========
def tratar_usuario(user_id):
    if str(user_id) == RAMON_USER_ID:
        return {"eh_ramon": True, "tratamento": "Chefe", "emoji": "❤️"}
    return {"eh_ramon": False, "tratamento": "Usuário", "emoji": "😊"}

async def enviar_com_smart_split(ctx_ou_message, texto):
    """Divide mensagens maiores que 2000 caracteres para o Discord aceitar"""
    LIMITE = 1950
    if len(texto) <= LIMITE:
        await ctx_ou_message.reply(texto)
    else:
        partes = []
        while len(texto) > 0:
            if len(texto) > LIMITE:
                corte = texto[:LIMITE].rfind(' ')
                if corte == -1: corte = LIMITE
                partes.append(texto[:corte])
                texto = texto[corte:]
            else:
                partes.append(texto)
                texto = ""
        
        await ctx_ou_message.reply(partes[0])
        for parte in partes[1:]:
            await asyncio.sleep(1) # Pausa pequena para não flodar
            await ctx_ou_message.channel.send(parte)

# --- TAREFA DE BACKGROUND (O SECRETÁRIO) ---
async def processar_memoria_background(conversa_recente):
    """
    Usa o modelo LEVE (Llama 3.2) para resumir a conversa e salvar no JSON.
    Roda sem travar a resposta principal.
    """
    try:
        memoria_antiga = cache.cache.get("resumo_global", "")
        
        prompt_resumo = f"""
        Tarefa: Atualizar o resumo da memória da IA com base na nova conversa.
        Memória Antiga: {memoria_antiga}
        Nova Conversa: {conversa_recente}
        
        Saída (Apenas o resumo atualizado em Português, 1 parágrafo):
        """
        
        resposta = await asyncio.to_thread(
            ollama.chat,
            model=MODELO_SECRETARIO,
            messages=[{'role': 'user', 'content': prompt_resumo}],
            options={'num_predict': 100, 'temperature': 0.2} 
        )
        
        novo_resumo = resposta['message']['content'].strip()
        cache.atualizar_resumo(novo_resumo)
        print(f"💾 [Secretário] Memória atualizada no JSON.")
        
    except Exception as e:
        print(f"⚠️ Erro no Secretário: {e}")

# ========= EVENTO PRINCIPAL (CÉREBRO) =========
@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.content.startswith(('!', '.', '-', '/')): return

    foi_mencionada = bot.user in message.mentions
    vai_falar_sozinha = random.random() < CHANCE_DE_FALAR
    
    if foi_mencionada or vai_falar_sozinha:
        
        # Limpa o texto da mensagem
        pergunta = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if not pergunta: return 

        user_info = tratar_usuario(message.author.id)
        
        async with message.channel.typing():
            try:
                # === 1. TENTA O CACHE EXATO (JSON) ===
                # Prioridade máxima: Se tiver resposta pronta, usa ela.
                resposta_pronta = cache.buscar_exata(pergunta)
                
                if resposta_pronta:
                    await enviar_com_smart_split(message, resposta_pronta)
                    return # Encerra aqui, não gasta GPU

                # === 2. SE NÃO ACHOU, CHAMA O CÉREBRO (QWEN) ===
                user_id = str(message.author.id)
                historico.adicionar(user_id, 'user', pergunta)
                
                # Pega a memória longa do JSON
                memoria_longa = cache.cache.get("resumo_global", "Sem memória prévia.")
                
                # Prepara o contexto
                msgs = [{
                    'role': 'system', 
                    'content': f"{SYSTEM_PROMPT}\n\n[MEMÓRIA DE LONGO PRAZO]: {memoria_longa}"
                }]
                msgs.extend(historico.obter(user_id))

                # Gera a resposta com Qwen
                resposta = await asyncio.to_thread(
                    ollama.chat, 
                    model=MODELO_CEREBRO, 
                    messages=msgs,
                    options={'num_predict': -1, 'temperature': 0.7} # 0.7 para ser criativa mas não maluca
                )

                texto = resposta['message']['content'].strip()
                
                # Adiciona o emoji do criador se necessário, mas não estraga código
                if user_info['eh_ramon'] and "```" not in texto: 
                    texto += f" {user_info['emoji']}"
                
                historico.adicionar(user_id, 'assistant', texto)
                
                # Envia a resposta inteligente
                await enviar_com_smart_split(message, texto)

                # === 3. ACORDA O SECRETÁRIO (LLAMA) ===
                # A cada 4 mensagens, pede pro modelo leve resumir tudo
                if len(historico.obter(user_id)) % 4 == 0:
                    conversa_recente = str(historico.obter(user_id)[-4:])
                    asyncio.create_task(processar_memoria_background(conversa_recente))

            except Exception as e:
                print(f"🔥 Erro Crítico: {e}")
                if foi_mencionada:
                    await message.reply("Minha GPU fritou... Tenta de novo? 😵‍💫")

@atexit.register
def salvar_antes_de_sair():
    cache.salvar_cache()

@bot.event
async def on_ready():
    print(f"🚀 Alice Iniciada!")
    print(f"🧠 Cérebro (Lógica): {MODELO_CEREBRO}")
    print(f"📝 Secretário (Memória): {MODELO_SECRETARIO}")
    print(f"💾 Cache carregado de: {caminho_cache}")

bot.run(TOKEN)