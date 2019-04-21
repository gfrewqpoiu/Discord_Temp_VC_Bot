import discord
from discord.ext import commands
import tasks
from typing import Dict
import asyncio
import configparser

config = configparser.ConfigParser('config.ini')
login = config['Login']
settings = config['Settings']
loginID = login.get('Login Token')
current_channels={} # Type: Dict[discord.Member, discord.VoiceChannel]
category = settings.get('Category', None)
loop_active=False

bot = commands.Bot(command_prefix=settings.get('prefix', '!'),
                   description=settings.get('Bot Description', 'Temporary Voice Channel Bot'), pm_help=True)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)

@bot.command(aliases=['newvc', 'vc', 'tempvc', 'neuvc'])
async def newtempvc(ctx, player_limit: int = 4, *, name: str = ""):
    """This creates a temporary voice channel.
    The optional parameters are:
    :param player_limit The player limit of the voice channel, limited to 20.
    :param name The name of the voice channel."""
    if name is None or len(name) < 4 or len(name) > 20:
        final_name = ctx.author.name
    else:
        final_name = name

    if player_limit > 20:
        final_limit = 20
    elif player_limit < 2:
        await ctx.send(
            """The amount of users for the voice channel has to be at least 2.
            Die Menge der Benutzer des Sprachkanals muss mindestens 2 sein.""")
        return
    else:
        final_limit = player_limit

    if ctx.author in current_channels:
        await ctx.send(
            f"""You already have a temporary voice channel. It is {current_channels[ctx.author].name}
            Du hast bereits einen temporären Sprachkanal erstellt. Er heißt {current_channels[ctx.author].name}""")
        return

    try:
        channel = await ctx.guild.create_voice_channel(name=final_name, category=category, reason=
        f"{ctx.author} created a temporary voice channel for {final_limit} players.")

    except discord.Forbidden:
        await ctx.send(
            """The creation of the voice channel failed because I have no rights to create a voice channel.
            Ich konnte keinen Sprachkanal erstellen weil mir dazu die Rechte fehlen."""
        )
        return
    except discord.HTTPException:
        await ctx.send(
            "The creation of the voice channel failed."
        )
        return
    current_channels[ctx.author]=channel
    if not loop_active:
        await asyncio.sleep(120)
        clean_up_channels.start()

@tasks.loop(minutes=10)
async def clean_up_channels():
    for user, channel in current_channels:
        if channel not in channel.guild.voice_channels:
            del current_channels[user]
            print("A voice channel was deleted by a moderator without using commands!")
            continue

        if len(channel.members)==0:
            try:
                channel.delete(reason=
                               f"The temporary voice channel {channel.name} created by {user.name} is empty.")
            except:
                continue

            del current_channels[user]

@bot.command(aliases=['rmvcs', 'removevcs'], hidden=True)
@commands.has_permissions(manage_channels=True)
async def removeallvcs(ctx):
    """This command can be used to remove all temporary voice channels."""
    while len(current_channels) > 0:
        user, channel = current_channels.popitem()
        try:
            await channel.delete(reason=f'The remove all voice channels command was used by {ctx.author.name}.')
        except:
            pass
        print(f"The channel {channel.name}, made by {user.name} was deleted by a moderator.")


try:
    bot.run(loginID, reconnect=True)
except:
    raise ValueError(
        "Couldn't log in with the given credentials, please check those in config.ini"
        " and your connection and try again!")