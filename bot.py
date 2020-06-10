import discord
from discord.ext import commands, tasks
from typing import Dict
import asyncio
import configparser
from copy import deepcopy
import datetime

config = configparser.ConfigParser()
config.read('config.ini')
login = config['Login']
settings = config['Settings']
loginID = login.get('Login Token')
current_channels={} # Type: Dict[int, int]
loop_active=False

bot = commands.Bot(command_prefix=settings.get('prefix', '!'),
                   description=settings.get('Bot Description', 'Temporary Voice Channel Bot'), pm_help=True)


@bot.event
async def on_ready():
    global category
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    category = bot.get_channel(int(settings.get('Category', None)))


@bot.command(aliases=['vc', 'tempvc',])
async def newtempvc(ctx, player_limit: int = 4, *, name: str = ""):
    """This creates a temporary voice channel.
    The optional parameters are:
    :param player_limit The player limit of the voice channel, limited to 20.
    :param name The name of the voice channel.
    You must specify a player limit if you want to specify a custom name."""
    global loop_active
    await ctx.message.delete()
    if name is None or len(name) < 4 or len(name) > 16:
        final_name = ctx.author.name
    else:
        final_name = name

    if player_limit > 20:
        final_limit = 20
    elif player_limit < 2:
        await ctx.send(
            "The amount of users for the voice channel has to be at least 2.\nDie Menge der Benutzer des Sprachkanals muss mindestens 2 sein.", delete_after=30)
        return
    else:
        final_limit = player_limit

    if ctx.author.id in current_channels:
        channel= bot.get_channel(current_channels[ctx.author.id])
        if channel is None:
            del current_channels[ctx.author.id]
            print("A voice channel was deleted by a moderator without using commands!")
        else:
            await ctx.send(
            f"You already have a temporary voice channel. It is `{channel.name}`.\nDu hast bereits einen temporären Sprachkanal erstellt. Er heißt `{channel.name}`.", delete_after=30)
            return

    try:
        channel = await ctx.guild.create_voice_channel(name=final_name, user_limit=final_limit, category=category, reason=
        f"{ctx.author} created a temporary voice channel for {final_limit} players.")
        await ctx.send(f"A voice channel with the name `{final_name}` was created.\nEin Sprachkanal mit dem Namen `{final_name}` wurde erstellt.", delete_after=60)

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
    current_channels[ctx.author.id]=channel.id
    if not loop_active:
        clean_up_channels.start()
        print("Started cleanup loop.")
        loop_active=True


@tasks.loop(minutes=5)
async def clean_up_channels():
    global loop_active
    min_difference = datetime.timedelta(minutes=2)
    print("Cleaning up.")
    if len(current_channels) == 0:
        loop_active = False
        clean_up_channels.cancel()
        return print("Loop is running but no channels are left.")
    tempdict=deepcopy(current_channels)
    for userid, channelid in tempdict.items():
        channel = bot.get_channel(channelid)
        user = bot.get_user(userid)
        if channel is None:
            del current_channels[userid]
            print("A voice channel was deleted by a moderator without using commands!")
            continue

        if len(channel.members)==0:
            difference=datetime.datetime.utcnow() - channel.created_at
            if difference < min_difference:
                continue
            try:
                await channel.delete(reason=f"The temporary voice channel {channel.name} created by {user.name} is empty.")
            except:
                continue

            del current_channels[userid]


@bot.command(aliases=['rmvcs', 'removevcs', 'delalltempvcs'])
@commands.has_permissions(manage_channels=True)
async def removealltempvcs(ctx):
    """This command can be used to remove all temporary voice channels.
    It can only be used by moderators."""
    global loop_active
    await ctx.message.delete()
    while len(current_channels) > 0:
        userid, channelid = current_channels.popitem()
        user = bot.get_user(userid)
        channel = bot.get_channel(channelid)
        try:
            await channel.delete(reason=f'The remove all voice channels command was used by {ctx.author.name}.')
        except:
            pass
        print(f"The channel {channel.name}, made by {user.name} was deleted by a moderator.")
    clean_up_channels.cancel()
    loop_active=False
    print("Stopped the loop")
    ctx.senc("Done!", delete_after=10)


try:
    bot.run(loginID, reconnect=True)
except:
    raise ValueError(
        "Couldn't log in with the given credentials, please check those in config.ini"
        " and your connection and try again!")