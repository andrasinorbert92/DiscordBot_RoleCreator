import os
import re

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Discord Scope:
#   * bot
#   * applications.command
# bot permissions:
#   * Administrator



def slugify(name: str, max_len: int = 90) -> str:
    s = name.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-_]", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:max_len] if s else "channel"


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user} (id: {bot.user.id})")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global commands")
    except Exception as exc:
        print("Sync error:", exc)


@bot.tree.command(
    name="createspace",
    description="Category + text + voice + role letrehozasa, kulon jogosultsagokkal.",
)
@app_commands.describe(name="A kozos nev (pl. Projekt Alfa)")
async def createspace(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    if guild is None:
        await interaction.followup.send("Ezt csak szerveren lehet futtatni.", ephemeral=True)
        return

    user_perms = interaction.user.guild_permissions
    if not (user_perms.manage_channels and user_perms.manage_roles):
        await interaction.followup.send(
            "Ehhez `Manage Channels` es `Manage Roles` jogosultsag kell.",
            ephemeral=True,
        )
        return

    bot_member = guild.me
    if bot_member is None:
        await interaction.followup.send("Nem talalom a botot mint szervertagot.", ephemeral=True)
        return

    bot_perms = bot_member.guild_permissions
    if not (bot_perms.manage_channels and bot_perms.manage_roles):
        await interaction.followup.send(
            "A botnak `Manage Channels` es `Manage Roles` jogosultsag kell.",
            ephemeral=True,
        )
        return

    app_perms = interaction.app_permissions
    if app_perms and not (app_perms.manage_channels and app_perms.manage_roles):
        await interaction.followup.send(
            "Ebben a csatornaban a botnak nincs eleg joga (`Manage Channels` + `Manage Roles`).",
            ephemeral=True,
        )
        return

    base_name = name.strip()
    if not base_name:
        await interaction.followup.send("Adj meg ervenyes nevet.", ephemeral=True)
        return

    existing_role = discord.utils.get(guild.roles, name=base_name)
    if existing_role:
        await interaction.followup.send(
            f"Mar letezik ilyen nevvel role: **{existing_role.name}**. Adj masik nevet.",
            ephemeral=True,
        )
        return

    role = None
    try:
        role = await guild.create_role(
            name=base_name,
            reason=f"createspace command by {interaction.user} ({interaction.user.id})",
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
                mention_everyone=True,
                send_messages_in_threads=True,
                create_public_threads=True,
                create_private_threads=True,
                connect=True,
                speak=True,
                stream=True,
                use_voice_activation=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True,
                manage_channels=True,
            ),
        }

        category = await guild.create_category(
            name=base_name,
            overwrites=overwrites,
            reason=f"createspace command by {interaction.user} ({interaction.user.id})",
        )

        base_slug = slugify(base_name)
        text_channel = await guild.create_text_channel(
            name=f"{base_slug}-text",
            category=category,
            reason=f"createspace command by {interaction.user} ({interaction.user.id})",
        )
        voice_channel = await guild.create_voice_channel(
            name=f"{base_slug}-voice",
            category=category,
            reason=f"createspace command by {interaction.user} ({interaction.user.id})",
        )

        await interaction.followup.send(
            "Kesz ✅\n"
            f"- Role: **{role.name}**\n"
            f"- Kategoria: **{category.name}**\n"
            f"- Text: {text_channel.mention}\n"
            f"- Voice: **{voice_channel.name}**\n"
            "A ket csatornahoz alapbol csak a letrehozott role fer hozza.",
            ephemeral=True,
        )
    except discord.Forbidden:
        if role is not None:
            try:
                await role.delete(reason="createspace rollback after missing permissions")
            except discord.HTTPException:
                pass
        await interaction.followup.send(
            "403 Missing Permissions: nincs eleg jogom a letrehozashoz.\n"
            "Ellenorizd, hogy a bot role-ja eleg magasan van, es van `Manage Channels` + `Manage Roles` joga.",
            ephemeral=True,
        )
    except discord.HTTPException as exc:
        if role is not None:
            try:
                await role.delete(reason="createspace rollback after HTTP error")
            except discord.HTTPException:
                pass
        await interaction.followup.send(f"Discord API hiba tortent: `{exc}`", ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("A DISCORD_TOKEN nincs beallitva.")
    bot.run(TOKEN)
