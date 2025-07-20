import discord
from discord.ext import commands
import datetime
import json
import os
from dotenv import load_dotenv
import requests

dotenv_path = r'C:\Users\jo429\Desktop\GNR\.env'
load_dotenv(dotenv_path)

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("❌ Não foi possível carregar o TOKEN.")
else:
    print("✅ TOKEN carregado com sucesso")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

FICHEIRO_REGISTOS = "registos_bot.json"

if os.path.exists(FICHEIRO_REGISTOS):
    with open(FICHEIRO_REGISTOS, "r") as f:
        registos = json.load(f)
        if not isinstance(registos, dict):
            registos = {}
else:
    registos = {}

@bot.event
async def on_ready():
    print(f"✅ Bot está online como {bot.user}")

class PontoView(discord.ui.View):
    def __init__(self, user_id, user_avatar_url):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_avatar_url = user_avatar_url
        self.pausa_ativa = False

    async def criar_embed(self, interaction, status="Serviço em aberto", pausa_msg=None):
        uid = str(self.user_id)
        dados = registos.get(uid, {"nome": "Desconhecido", "dias": [], "pausas": []})
        nome = dados.get("nome", "Desconhecido")
        dias = dados.get("dias", [])

        if not dias:
            entrada_fmt = "N/A"
            saida_fmt = "N/A"
            duracao_str = "0:00:00"
            total_horas = 0
            data_ini = "N/A"
            data_fim = "N/A"
            hora_fim = "N/A"
        else:
            dia_atual = dias[-1]
            entrada = dia_atual.get("entrada")
            saida = dia_atual.get("saida")
            entrada_dt = datetime.datetime.strptime(entrada, "%Y-%m-%d %H:%M:%S") if entrada else None
            saida_dt = datetime.datetime.strptime(saida, "%Y-%m-%d %H:%M:%S") if saida else None

            entrada_fmt = entrada_dt.strftime("%A, %d de %B de %Y %H:%M") if entrada_dt else "N/A"
            saida_fmt = saida_dt.strftime("%A, %d de %B de %Y %H:%M") if saida_dt else "Em aberto"

            duracao = (saida_dt - entrada_dt) if (entrada_dt and saida_dt) else datetime.datetime.now() - entrada_dt if entrada_dt else None
            duracao_str = str(duracao).split(".")[0] if duracao else "N/A"
            total_horas = round(duracao.total_seconds() / 3600, 2) if duracao else 0

            data_ini = entrada_dt.strftime("%d/%m/%Y") if entrada_dt else "N/A"
            data_fim = saida_dt.strftime("%d/%m/%Y") if saida_dt else datetime.datetime.now().strftime("%d/%m/%Y")
            hora_fim = saida_dt.strftime("%H:%M") if saida_dt else datetime.datetime.now().strftime("%H:%M")

        icon_url = self.user_avatar_url  

        embed = discord.Embed(
            title=status,
            color=discord.Color.green() if "Iniciado" in status else
                  discord.Color.orange() if "Pausa" in status else
                  discord.Color.red() if "Finalizado" in status else
                  discord.Color.blue()
        )

        embed.set_author(name=nome)
        embed.set_thumbnail(url=icon_url)

        embed.add_field(name="👤 Utilizador", value=f"@{nome}", inline=False)
        embed.add_field(name="▶️ Início", value=entrada_fmt, inline=True)
        embed.add_field(name="⏹️ Término", value=saida_fmt, inline=True)
        embed.add_field(name="⏱️ Tempo total", value=duracao_str, inline=False)

        resumo_texto = (
            f"• Duração: {duracao_str}\n"
            f"• Horas totais: {total_horas}h\n"
            f"• Data: {data_ini} a {data_fim}\n"
            f"Versão 1.0 - Smurf • {data_fim} {hora_fim}"
        )
        if pausa_msg:
            resumo_texto += f"\n\n⚠️ {pausa_msg}"

        embed.add_field(name="📊 Resumo", value=resumo_texto, inline=False)
        embed.set_footer(text=f"ID: {uid}")

        return embed

    @discord.ui.button(label="🚪 Entrar em Serviço", style=discord.ButtonStyle.success, row=0)
    async def entrar_servico(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(self.user_id)
        nome = interaction.user.name
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id not in registos:
            registos[user_id] = {"nome": nome, "dias": [], "pausas": []}

        dias = registos[user_id]["dias"]
        if dias and "entrada" in dias[-1] and "saida" not in dias[-1]:
            await interaction.response.send_message(f"❌ **{nome}**, você já está em serviço!", ephemeral=True)
            return

        dias.append({"entrada": agora})
        with open(FICHEIRO_REGISTOS, "w") as f:
            json.dump(registos, f, indent=4)

        self.pausa_ativa = False
        # Atualizar botão Pausar para estado inicial
        for child in self.children:
            if child.custom_id == "pausar_button":
                child.label = "☕ Iniciar Pausa"
                child.style = discord.ButtonStyle.primary
                break

        embed = await self.criar_embed(interaction, status="▶️ Serviço Iniciado")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="☕ Iniciar Pausa", style=discord.ButtonStyle.primary, row=0, custom_id="pausar_button")
    async def pausar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(self.user_id)
        nome = interaction.user.name
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id not in registos or not registos[user_id]["dias"]:
            await interaction.response.send_message(f"❌ **{nome}**, você não está em serviço para pausar!", ephemeral=True)
            return

        dias = registos[user_id]["dias"]
        if "saida" in dias[-1]:
            await interaction.response.send_message(f"❌ **{nome}**, o serviço já foi fechado.", ephemeral=True)
            return

        pausas = registos[user_id]["pausas"]

        if not self.pausa_ativa:
            pausas.append({"inicio": agora})
            with open(FICHEIRO_REGISTOS, "w") as f:
                json.dump(registos, f, indent=4)

            self.pausa_ativa = True
            button.label = "⏯️ Retomar Trabalho"
            button.style = discord.ButtonStyle.secondary
            embed = await self.criar_embed(interaction, status="☕ Pausa Iniciada", pausa_msg=f"Pausa iniciada às {agora}.")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            if not pausas or "fim" in pausas[-1]:
                await interaction.response.send_message(f"❌ **{nome}**, você não iniciou uma pausa!", ephemeral=True)
                return

            pausas[-1]["fim"] = agora
            with open(FICHEIRO_REGISTOS, "w") as f:
                json.dump(registos, f, indent=4)

            inicio = datetime.datetime.strptime(pausas[-1]["inicio"], "%Y-%m-%d %H:%M:%S")
            fim = datetime.datetime.strptime(agora, "%Y-%m-%d %H:%M:%S")
            duracao_pausa = fim - inicio

            self.pausa_ativa = False
            button.label = "☕ Iniciar Pausa"
            button.style = discord.ButtonStyle.primary
            embed = await self.criar_embed(interaction, status="✅ Pausa Finalizada", pausa_msg=f"Pausa finalizada às {agora}. Duração: {duracao_pausa}.")
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⏹️ Fechar Serviço", style=discord.ButtonStyle.danger, row=0)
    async def fechar_servico(self, interaction: discord.Interaction, button: discord.ui.Button):
        nome_clicou = interaction.user.name
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        user_id = str(self.user_id)

        if user_id not in registos or not registos[user_id]["dias"]:
            await interaction.response.send_message(f"❌ **{nome_clicou}**, o serviço não está aberto para fechar.", ephemeral=True)
            return

        dias = registos[user_id]["dias"]
        if "saida" in dias[-1]:
            await interaction.response.send_message(f"❌ **{nome_clicou}**, o serviço já foi fechado.", ephemeral=True)
            return

        dias[-1]["saida"] = agora
        with open(FICHEIRO_REGISTOS, "w") as f:
            json.dump(registos, f, indent=4)

        self.clear_items()

        mensagem_extra = None
        if interaction.user.id != self.user_id:
            mensagem_extra = f"⚠️ Serviço fechado por outro utilizador: {interaction.user.display_name}"

        embed = await self.criar_embed(interaction, status="⏹️ Serviço Finalizado", pausa_msg=mensagem_extra)
        await interaction.response.edit_message(embed=embed, view=None)

        api_url = "http://localhost:5000/registrar_servico"

        inicio_dt = datetime.datetime.strptime(dias[-1]["entrada"], "%Y-%m-%d %H:%M:%S")
        fim_dt = datetime.datetime.strptime(agora, "%Y-%m-%d %H:%M:%S")
        duracao_servico = fim_dt - inicio_dt

        payload = {
            "usuario": registos[user_id]["nome"],
            "entrada": dias[-1]["entrada"],
            "saida": agora,
            "duracao_servico": str(duracao_servico)
        }

        headers = {
            "Authorization": f"Bearer {os.getenv('API_KEY', 'chave_padrao')}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)
            if interaction.user.guild_permissions.administrator:
                if response.status_code == 200:
                    await interaction.followup.send(f"✅ **{nome_clicou}**, dados enviados com sucesso!", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ **{nome_clicou}**, erro ao enviar dados: {response.status_code}", ephemeral=True)
        except Exception as e:
            if interaction.user.guild_permissions.administrator:
                await interaction.followup.send(f"❌ **{nome_clicou}**, erro ao enviar para o site: {str(e)}", ephemeral=True)

@bot.tree.command(name="ponto", description="Abre a interface de ponto com os botões.")
async def ponto_command(interaction: discord.Interaction):
    descricao = (
        "🟢 **Bot de Gestão de Ponto**\n\n"
        "Use os botões abaixo para:\n"
        "🚪 **Entrar em Serviço** - Começar o seu turno.\n"
        "☕ **Iniciar Pausa** - Fazer uma pausa durante o serviço.\n"
        "⏹️ **Fechar Serviço** - Terminar o seu turno e enviar o registo.\n\n"
        "Clique no botão 'Entrar em Serviço' para começar."
    )

    embed_inicial = discord.Embed(
        title="🕒 Gestão de Ponto - Instruções",
        description=descricao,
        color=discord.Color.blurple()
    )
    embed_inicial.set_footer(text="Versão 1.0 - Smurf")

    view = PontoView(user_id=interaction.user.id, user_avatar_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed_inicial, view=view, ephemeral=False)
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot está online como {bot.user}")

bot.run(TOKEN)
