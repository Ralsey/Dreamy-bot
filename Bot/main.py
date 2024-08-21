# discord imports
from discord.ext import commands
import discord

# python imports 
from dotenv import load_dotenv
from typing import Final
import asyncio
import time
import os

# local imports
from functions import send_message_to_user, get_video_urls

# 3rd party imports
import yt_dlp


# Load the environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# owner ID for private update messages
owner_id: int = 529007366365249546

# role IDs
sancturary_keeper_role_id: int = 1239651704476143766
sky_guardians_role_id: int = 1242514956058890240
tech_oracle_role_id: int = 1274673142153084928
event_luminary_role_id: int = 1240725491099631717

allowed_roles: list[int] = [sancturary_keeper_role_id, event_luminary_role_id, sky_guardians_role_id, tech_oracle_role_id, 1266201501924331552] # last one is for testing purpeses

# channel/category IDs
support_category_id: int = 1250699865621794836
general_category_id: int = 1239651600205873324
music_voice_id: int = 1268856363866652784

# channel names
bot_channel: str = "🤖bot-spam"
music_channel: str = "🎼music-bot"
ticket_channel: str = "🎫query-corner"
ticket_logs_channel: str = "🎟ticket-logs"

# music player settings
yt_dlp_options: dict[str, str] = {"format": "bestaudio/best", 'noplaylist': False, "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]}
ffmpeg_options: dict[str, str] = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

# team settings
max_teams: int = 4
cooldown_period: int = 60

# youtube variables
youtube_base_url: str = 'https://www.youtube.com/'
youtube_results_url: str = youtube_base_url + 'results?'
youtube_watch_url: str = youtube_base_url + 'watch?v='
ytdl: yt_dlp.YoutubeDL = yt_dlp.YoutubeDL(yt_dlp_options)

# Initialize the dictionaries and lists
tickets: dict = {}
teams: dict = {}
update_queue: list = []
full_team_cooldowns: dict = {}
voice_clients: dict[int, discord.VoiceChannel] = {}
queues: dict = {}

# Create a bot instance
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client: commands.Bot = commands.Bot(command_prefix="/", intents=intents)


# Startup of the bot
@client.event
async def on_ready() -> None:
    print(f"\n[info] Bot is ready as {client.user}\n")
    
    # Set Rich Presence (Streaming)
    activity = discord.Activity(type=discord.ActivityType.streaming, name="PixelPoppyTV", url="https://www.twitch.tv/pixelpoppytv", details="PixelPoppyTV", state="Sky: Children of The Light")
    await client.change_presence(status=discord.Status.online, activity=activity)
    
    # Under Development (Do not disturb)
    # activity = discord.Activity(type=discord.ActivityType.playing, name="Do not disturb, im getting tested")
    # await client.change_presence(status=discord.Status.do_not_disturb, activity=activity)
    await client.tree.sync()  # Sync slash commands

# dev commands
@client.tree.command(name="dev", description="create a dev channel")
async def dev(interaction: discord.Interaction, name: str) -> None:
    await interaction.response.defer()  # Defer the response to get more time
    if not any(role.id in [tech_oracle_role_id] for role in interaction.user.roles):
        await interaction.followup.send("```fix\nYou do not have permission to create a team.```")
        return
    
    general_category = discord.utils.get(interaction.guild.categories, id=general_category_id)
    if not general_category:
        print("[error][tickets] general category not found. Please provide a valid category ID.")
        await interaction.followup.send("```fix\ngeneral category not found. Please provide a valid category ID.```")
        return
    
    tech_oracle = interaction.guild.get_role(tech_oracle_role_id)
    if not tech_oracle:
        print("[error][tickets] Tech Oracle role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nTech Oracle not found. Please provide a valid role ID.```")
        return
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
        interaction.user: discord.PermissionOverwrite(read_messages=True),
        tech_oracle: discord.PermissionOverwrite(read_messages=True, manage_channels=True)
    }

    def_channel = await interaction.guild.create_text_channel(name=name, category=general_category, overwrites=overwrites, reason="Created a channel for tech oracle def")
    
    print(f"[def] Ticket created for user {interaction.user.name} in channel {def_channel.name}")
    
    await interaction.followup.send("a dev channel has been created!")
    # Send DM to Femboipet (replace with actual user ID) and the user
    femboipet = await client.fetch_user(owner_id)
    ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{def_channel.id}"
    await send_message_to_user(client, interaction.user.id, f"Your def channel has been created: {ticket_url}")

    await femboipet.send(f"There has been created an def channel named `{def_channel.name}` by {interaction.user.mention}: {ticket_url}")


@client.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"Pong! that took me {round(client.latency * 1000)}ms to respond")
    print(f"[info] {interaction.user.name} requested the bot's latency, it's {round(client.latency * 1000)}ms")


# info commands
@client.tree.command(name="timers", description="Get the url to the timers channel")
async def timers(interaction: discord.Interaction) -> None:
    timer_channel_url = "https://discord.com/channels/1239651599480127649/1252324353115291849/1252324488901824556"
    response = "Here is the url to the channel with all the timers:\n" + timer_channel_url
    print(f"[info] {interaction.user.name} requested the timer")
    await interaction.response.send_message(response)


# Music commands
@client.tree.command(name="play", description="Play a song or playlist from a YouTube URL")
async def play(interaction: discord.Interaction, url: str) -> None:
    await interaction.response.defer()  # Defer to allow time for processing
    guild_id = interaction.guild.id

    # Specify the channel ID or name you want the bot to join
    # You can use the channel ID directly for accuracy, or fetch it by name
    music_channel = discord.utils.get(interaction.guild.voice_channels, id=music_voice_id)

    if music_channel is None:
        await interaction.followup.send("```fix\nThe specified voice channel does not exist. please update the channel ID.```")
        return
    
    if client.voice_clients and guild_id in voice_clients:
        voice_client = voice_clients[guild_id]
    else:
        try:
            # Connect to the specific voice channel
            voice_client = await music_channel.connect()
            voice_clients[guild_id] = voice_client
        except TypeError as e:
            print(f"[error][player] Error connecting to the voice channel: {e}")
            await interaction.followup.send("```fix\nAn error occurred while trying to connect to the voice channel.```")
            return

    # Get video or playlist URLs
    video_urls = get_video_urls(url)
    if video_urls == []:
        await interaction.followup.send("```fix\nInvalid URL or no video(s) were found.```")
        return
    if video_urls == "radio":
        await interaction.followup.send("```fix\nThis is a radio URL and cannot be processed.")
        return

    # If there's no queue for this guild, create one
    if guild_id not in queues:
        queues[guild_id] = []

    # If the bot is not already playing music, play the first song in the queue
    if not voice_clients[guild_id].is_playing():
        # Add video URLs to the queue
        queues[guild_id].extend(video_urls)
        await interaction.followup.send("Now playing in the music channel.")
        await play_next(interaction)
    else:
        # Add video URLs infront of the queue
        queues[guild_id] = [*video_urls, *queues[guild_id]]
        voice_client.stop()
        await interaction.followup.send(f"Added {len(video_urls)} to the front of the queue.")


@client.tree.command(name="queue", description="Queue the next song or playlist from a YouTube URL")
async def queue(interaction: discord.Interaction, url: str) -> None:
    guild_id = interaction.guild.id
    
    # Get video or playlist URLs
    video_urls = get_video_urls(url)
    if not video_urls:
        await interaction.response.send_message("```fix\nInvalid URL or no videos found.```")
        return

    # If there's no queue for this guild, create one
    if guild_id not in queues:
        queues[guild_id] = []
    
    # Add the video(s) to the queue
    queues[guild_id].extend(video_urls)
    await interaction.response.send_message(f"Added {len(video_urls)} song(s) to the queue.")
    
    # If nothing is currently playing, play the first song in the queue
    if not voice_clients[guild_id].is_playing():
        await play_next(interaction)


@client.tree.command(name="clear_queue", description="Clear the current set queue")
async def clear_queue(interaction: discord.Interaction) -> None:
    if interaction.guild.id in queues:
        queues[interaction.guild.id].clear()
        await interaction.response.send_message("Queue cleared!")
    else:
        await interaction.response.send_message("There is no queue to clear")


@client.tree.command(name="pause", description="Pause the currently playing song")
async def pause(interaction: discord.Interaction) -> None:
    try:
        voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Paused the song.")
        else:
            await interaction.response.send_message("No song is currently playing.")
    except Exception as e:
        print(f"[error][player] Error pausing the song: {e}")
        await interaction.response.send_message(f"```fix\nI'm unable to pause the song at the moment```")


@client.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction) -> None:
    try:
        voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Resumed the song.")
        else:
            await interaction.response.send_message("No song is currently paused.")
    except Exception as e:
        print(f"[error][player] Error resuming the song: {e}")
        await interaction.response.send_message(f"```fix\nI'm unable to resume the song at the moment```")


@client.tree.command(name="skip", description="Skip the currently playing song and play the next one in the queue")
async def skip(interaction: discord.Interaction) -> None:
    guild_id = interaction.guild.id
    
    # Get the voice client for the guild
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    try:
        if voice_client and voice_client.is_playing():
            # Stop the current song
            voice_client.stop()

            # Inform the user that the song was skipped
            await interaction.response.send_message("Skipped the song.")
        else:
            await interaction.response.send_message("No song is currently playing.")
    except Exception as e:
        print(f"[error][player] Error skipping the song: {e}")
        await interaction.response.send_message(f"```fix\nI'm unable to skip the song at the moment```")


@client.tree.command(name="stop", description="Stop the currently playing song and disconnect")
async def stop(interaction: discord.Interaction) -> None:
    try:
        guild_id = interaction.guild_id
        voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
        if voice_client:
            queues[guild_id] = []  # Clear the queue
            voice_client.stop()
            await voice_client.disconnect()
            await interaction.response.send_message("Stopped the song and disconnected.")
        else:
            await interaction.response.send_message("No song is currently playing.")
    except Exception as e:
        print(f"[error][player] Error stopping the song: {e}")
        await interaction.response.send_message(f"```fix\nI'm unable to stop the song at the moment```")


# Ticket commands
@client.tree.command(name="openticket", description="Open a ticket")
async def openticket(interaction: discord.Interaction, name: str = "Open Ticket", description: str = "Command to open a ticket!") -> None:
    await interaction.response.defer()  # Defer the response to get more time
    if not interaction.channel.name == ticket_channel:
        await interaction.followup.send(f"Please use this command in the {ticket_channel} channel.")
        return
    
    support_category = discord.utils.get(interaction.guild.categories, id=support_category_id)
    if not support_category:
        print("[error][tickets] Support category not found. Please provide a valid category ID.")
        await interaction.followup.send("```fix\nSupport category not found. Please provide a valid category ID.```")
        return
    
    sky_guardians_role = interaction.guild.get_role(sky_guardians_role_id)
    if not sky_guardians_role:
        print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nSky Guardians role not found. Please provide a valid role ID.```")
        return
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
        interaction.user: discord.PermissionOverwrite(read_messages=True),
        sky_guardians_role: discord.PermissionOverwrite(read_messages=True),
        tech_oracle_role_id: discord.PermissionOverwrite(read_messages=True)
    }

    ticket_name = f"ticket-{interaction.user.name}" if not name else f"{name}'s ticket"
    ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
    tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
    
    print(f"[tickets] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
    
    await interaction.followup.send("A ticket has been created!")
    # Send DM to Femboipet (replace with actual user ID) and the user
    femboipet = await client.fetch_user(owner_id) 
    ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
    await send_message_to_user(client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
    
    # Notify user and ping Sky Guardians role
    await ticket_channel.send(f"{sky_guardians_role.mention}, {interaction.user.mention} needs assistance. Please wait until a Sky Guardian is on the case <3\n\nThe ticket is called '{str(name)}' and is about '{str(description)}'")

    await femboipet.send(f"A ticket has been created by {interaction.user.mention}: {ticket_url}")


@client.tree.command(name="closeticket", description="Close the current ticket")
async def closeticket(interaction: discord.Interaction) -> None:
    await interaction.response.defer()  # Defer the response to get more time
    sky_guardians_role = interaction.guild.get_role(sky_guardians_role_id)
    
    # Check if the channel is indeed a ticket channel
    if not interaction.channel.id in tickets:
        await interaction.followup.send("No open ticket found in this channel or you do not have permission to close this ticket.")
        print(f"[tickets] No open ticket found in channel {interaction.channel.name}")
        return
    
    ticket_info = tickets[interaction.channel.id]
    
    # Check if the author is the ticket creator or in Sky Guardians role
    if interaction.user.id == ticket_info["user_id"] or sky_guardians_role in interaction.user.roles:
        ticket_logs = f""
        async for message in interaction.channel.history(limit=None):
            ticket_logs = f"{message.author.name}: {message.content}\n" + str(ticket_logs)
        ticket_logs = f"Transcript for ticket-{interaction.user.name}:\n" + str(ticket_logs)

        ticket_logs_channel = discord.utils.get(interaction.guild.text_channels, name="ticket_logs_channel")
        if ticket_logs_channel:
            await ticket_logs_channel.send(ticket_logs)
        
        print(f"[tickets] Ticket closed by user {interaction.user.name} in channel {interaction.channel.name}")

        await interaction.followup.send(f"Your ticket has been closed successfully. Transcript saved in {ticket_logs_channel} channel.")
        await interaction.channel.delete()
        del tickets[interaction.channel.id]
        await interaction.user.send(f"Your ticket has been closed successfully. Transcript saved in {ticket_logs_channel} channel.")
        await interaction.user.send(ticket_logs)


# Team commands
@client.tree.command(name="createteam", description="Create a team")
async def createteam(interaction: discord.Interaction, member: discord.Member, emoji: str) -> None:
    await interaction.response.defer()  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to create a team.")
        return
    
    if member.id in teams:
        await interaction.followup.send("This user already leads a team.")
        return

    if len(teams) >= max_teams:
        await interaction.followup.send("The maximum number of teams has been reached. Cannot create a new team.")
        return
    
    emoji = emoji.strip(":") # Remove the colons from the emoji if present
    print(f"[teams] Creating a team with {member.name}:{member.id} as the leader and {emoji} as the emoji.")
    # emoji_id = int(emoji.split(":")[2].strip(">"))
    # print(emoji_id)
    # emoji = client.get_emoji(emoji_id)
    await interaction.followup.send(f"Team {emoji} has been created!")
    team_message = f"__**Group Leader**__\n{member.mention} {emoji}\n\n__**Members**__\n"
    # Defer the interaction, so we can send the message and add the reaction later
    # await interaction.response.defer(ephemeral=True, thinking=True)
    message = await interaction.channel.send(team_message)

    # Add the bot's reaction
    await message.add_reaction(emoji)

    # Save team information
    teams[member.id] = {
        "message_id": message.id,
        "emoji": emoji,
        "members": [],
        "max_members": 8,  # assigns max members of team
        "leader_id": member.id,
        "reaction_count": 1,  # Start with 1 to count the team leader
        "last_locked_message_time": 0,
        "locked": False,  # Initialize the locked state
        "channel_id": interaction.channel.id,  # Track the channel ID
        "resetting": False  # Track if the team is currently resetting
    }


@client.tree.command(name="closeteam", description="Close the team")
async def closeteam(interaction: discord.Interaction, member: discord.Member) -> None:
    await interaction.response.defer()  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to close a team.")
        return
    
    if not member.id in teams:
        await interaction.followup.send(f"A team lead by {member.mention} not found.")
        return
    
    team_data = teams[member.id]
    
    # Check if the team is already locked
    if team_data["locked"] == False: 
        await interaction.followup.send(f"Team {team_data['emoji']} led by {member.mention} is not currently locked. Please lock the team first.")
        return
    team_data["closed"] = True  # Set the closed flag
    channel = client.get_channel(team_data["channel_id"])  # Get the team's channel
    message = await channel.fetch_message(team_data["message_id"])  # Fetch the message
    await message.delete()  # Delete the message

    del teams[member.id]  # Remove the team from the dictionary

    await interaction.followup.send(f"Team {team_data['emoji']} led by {member.mention} has been closed.")


@client.tree.command(name="lockteam", description="Lock a team")
async def lockteam(interaction: discord.Interaction, member: discord.Member) -> None:
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to lock a team.")
        return
        
    if member.id not in teams:
        await interaction.followup.send(f"A team lead by {member.mention} not found.")
        return
        
    team_data = teams[member.id]
    message_id = team_data["message_id"]
    
    if team_data["locked"] == True: 
        await interaction.followup.send(f"Team {team_data['emoji']} is already locked.")
        return
    
    # Retrieve the team message
    message = await interaction.channel.fetch_message(message_id)
    
    # Update the message to indicate the team is locked
    updated_message = message.content + "\n\n__**Team Full**__ - This team has been locked ^^"
    update_queue.append((message_id, updated_message))

    # Set the locked flag for the team
    teams[member.id]["locked"] = True
    await interaction.followup.send(f"Team {team_data['emoji']} has been locked.")


@client.tree.command(name="unlockteam", description="Unlock a team")
async def unlockteam(interaction: discord.Interaction, member: discord.Member) -> None:
    await interaction.response.defer(ephemeral=True)  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to unlock a team.")
        return
    
    if member.id not in teams:
        await interaction.followup.send("Team not found.")
        return
    
    team_data = teams[member.id]
    message_id = team_data["message_id"]

    if team_data["locked"] == False:
        await interaction.followup.send("Team is not locked.")
        return
        
    # Prevent modifications during the reset phase
    teams[member.id]["resetting"] = True

    # Retrieve the team message
    message = await interaction.channel.fetch_message(message_id)

    # Update the message to indicate the reset procedure
    reset_message = f"__**Group Leader**__\n{client.get_user(team_data['leader_id']).mention} :{team_data['emoji']}:\n\n__**Members**__\n<> The bot is currently Resetting the player list, give it a few seconds to refresh <>"
    await message.edit(content=reset_message)
    
    wait_message = await interaction.channel.send("Please wait for the team to unlock...")
    await interaction.followup.send(f"Team {team_data['emoji']} will be unlocked")
    # Adding a delay to simulate the refresh time
    await asyncio.sleep(2)

    # Capture all users who currently have the reaction
    current_reactors = set()
    for reaction in message.reactions:
        if str(reaction.emoji) == team_data["emoji"]:
            async for user in reaction.users():
                if user.id != client.user.id and user.id != team_data["leader_id"]:
                    current_reactors.add(user.id)

    # Rebuild the team members list
    team_data["members"] = []  # Start with an empy list
    for user_id in current_reactors:
        if len(team_data["members"]) < team_data["max_members"]:
            team_data["members"].append(user_id)
            print(f"[teams] Added user {user_id} to team {team_data['leader_id']} after unlocking.")

    # Inform the channel if the team is full again
    if len(team_data["members"]) >= team_data["max_members"]:
        teams[member.id]["locked"] = True

    # Update the team message to reflect the current state
    member_mentions = [
        client.get_user(member_id).mention for member_id in team_data["members"] if member_id != team_data["leader_id"]
    ]
    member_names_str = "\n".join(member_mentions)
    final_message = f"__**Group Leader**__\n{client.get_user(team_data['leader_id']).mention} :{team_data['emoji']}:\n\n__**Members**__\n<*> Yup... I see now, I shaw be on the case! Fixing the memba list UwU <*>"

    if member_names_str:
        final_message += f"\n\n{member_names_str}"
    await message.edit(content=final_message)

    # Remove resetting status and unlock the team
    teams[member.id]["resetting"] = False
    teams[member.id]["locked"] = False

    await wait_message.delete()


# Reaction handling for team creation
@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    message_id = payload.message_id
    user_id = payload.user_id

    for team_id, team in teams.items():
        if message_id == team["message_id"]:
            emoji = payload.emoji.name

            if user_id != client.user.id and emoji == team["emoji"]:
                team_leader_id = team["leader_id"]
                print(f"[teams] User {user_id} reacted with {emoji} to team {team_leader_id}")
                channel = client.get_channel(payload.channel_id)

                # Skip updating members list if team is resetting
                if team["resetting"] == True:
                    return
                
                # Skip updating members list if team is locked
                if team["locked"] == True: 
                    return

                user = await client.fetch_user(user_id)  # Fetch the user who reacted

                if user_id != team_leader_id:
                    if user_id not in team["members"]:  # Only add if not already in the team
                        team["reaction_count"] += 1

                        # Check if team is full and not locked yet
                        if len(team["members"]) < team["max_members"]:
                            team["members"].append(user_id)  # Add member to the list
                            print(f"[teams] Added user {user_id} to team {team_leader_id}")
                        else:
                            # If team is full, apply cooldown
                            team_leader = client.get_user(team_leader_id)
                            if team_leader is not None:
                                if team_leader_id not in full_team_cooldowns or time.time() - full_team_cooldowns[team_leader_id] > cooldown_period:
                                    await channel.send(
                                        f"The team of {team_leader.mention} :{team['emoji']}:\n"
                                        f"is full - Consider joining another team! {user.mention}"
                                    )
                                    full_team_cooldowns[team_leader_id] = time.time()
                            else:
                                print(f"[teams] Could not find user with ID {team_leader_id}")
                            return  # Do not add user if team is full

                        # Update the team message
                        member_mentions = []
                        for member_id in team["members"]:
                            try:
                                print(f"[teams] Fetching user with ID {member_id}")
                                member = await client.fetch_user(member_id)  # Fetches the user from the Discord API
                                member_mentions.append(member.mention)
                            except discord.NotFound:
                                # Handle the case where the user cannot be found
                                print(f"[teams] User with ID {member_id} not found.")
                            except Exception as e:
                                print(f"[teams] An error occurred while fetching user {member_id}: {e}")

                        member_names_str = "\n".join(member_mentions)

                        # Safely get the team leader user and handle the case where it might return None
                        try:
                            team_leader = await client.fetch_user(team_leader_id)
                        except discord.NotFound:
                            print(f"[teams] Team leader with ID {team_leader_id} not found.")
                            team_leader = None
                        except Exception as e:
                            print(f"[teams] An error occurred while fetching team leader {team_leader_id}: {e}")
                            team_leader = None

                        if team_leader is not None:
                            updated_message = (
                                f"__**Group Leader**__\n{team_leader.mention} :{team['emoji']}:\n\n"
                                f"__**Members**__\n{member_names_str}"
                            )
                        else:
                            print(f"[teams] Could not find user with ID {team_leader_id}")
                            updated_message = (
                                f"__**Group Leader**__\n(Unknown user) :{team['emoji']}:\n\n"
                                f"__**Members**__\n{member_names_str}"
                            )


                        # Update the message
                        message = await channel.fetch_message(message_id)
                        print(f"[teams] Updating message {message_id}")
                        await message.edit(content=updated_message)

                        # Lock the team if it's full
                        if len(team["members"]) == team["max_members"]:
                            team["locked"] = True
                            await channel.send(f"{client.get_user(team_leader_id).mention} group is now locked!")

                    else:
                        # User is already in the team
                        team["reaction_count"] -= 1

                        # Update the team message if a user leaves
                        member_mentions = []
                        for member_id in team["members"]:
                            if member_id != team["leader_id"]:
                                try:
                                    member = await client.fetch_user(member_id)
                                    member_mentions.append(member.mention)
                                except discord.NotFound:
                                    # Handle the case where the user cannot be found
                                    print(f"[teams] User with ID {member_id} not found.")
                                except Exception as e:
                                    print(f"[teams] An error occurred while fetching user {member_id}: {e}")
                        
                        member_names_str = "\n".join(member_mentions)
                        updated_message = (
                            f"__**Group Leader**__\n{client.get_user(team_leader_id).mention} :{team['emoji']}:\n\n"
                            f"__**Members**__\n{member_names_str}"
                        )
                        
                        # Update the message
                        message = await channel.fetch_message(message_id)
                        print(f"[teams] Updating message {message_id}")
                        await message.edit(content=updated_message)

                        # Unlock the team if it's not full anymore
                        if len(team["members"]) < team["max_members"]:
                            team["locked"] = False
                            await channel.send(f"{client.get_user(team_leader_id).mention} group is now unlocked!")


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    message_id = payload.message_id
    user_id = payload.user_id

    for team_id, team in teams.items():
        if message_id == team["message_id"]:
            if user_id in team["members"]:
                
                # Skip updating members list if team is locked
                if team["locked"] == True: 
                    return
                
                team["members"].remove(user_id)  # Remove member from the list
                print(f"[teams] Removed user {user_id} from team {team_id}")

                # Update the message
                member_mentions = []
                for member_id in team["members"]:
                    if member_id != team["leader_id"]:
                        try:
                            member = await client.fetch_user(member_id)
                            member_mentions.append(member.mention)
                        except discord.NotFound:
                            # Handle the case where the user cannot be found
                            print(f"[teams] User with ID {member_id} not found.")
                        except Exception as e:
                            print(f"[teams] An error occurred while fetching user {member_id}: {e}")
                            
                member_names_str = "\n".join(member_mentions)
                updated_message = (
                    f"__**Group Leader**__\n{client.get_user(team['leader_id']).mention} :{team['emoji']}:\n\n"
                    f"__**Members**__\n{member_names_str}"
                )

                # Add update to queue
                try:
                    # Find the channel from the message ID
                    for team in teams.values():
                        if message_id == team["message_id"]:
                            channel_id = team["channel_id"]
                            break
                    else:
                        # If we do not find the message ID in our tracked teams, skip processing
                        continue

                    channel = client.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)
                    await message.edit(content=updated_message)
                    print(f"[teams] Updated message {message_id}")
                except Exception as e:
                    print(f"[teams] Failed to update message {message_id}: {e}")


# player functions for music
async def play_next(interaction: discord.Interaction) -> None:
    guild_id = interaction.guild.id
    music_spam_channel = discord.utils.get(interaction.guild.text_channels, name=music_channel)

    # Check if there are songs in the queue
    if guild_id in queues and queues[guild_id]:
        next_url = queues[guild_id].pop(0)  # Get the next song from the queue
        loop = asyncio.get_event_loop()

        try:
            # Extract song info
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(next_url, download=False))
            song_url = data['url']
            player = discord.FFmpegOpusAudio(song_url, **ffmpeg_options)

            # Play the song and set the after callback to play the next song in the queue
            voice_clients[guild_id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction), client.loop))

            await music_spam_channel.send(f"Now playing: **{data['title']}**")
        except yt_dlp.DownloadError as e:
            print(f"[error][play_next] Error downloading the song: {e}")
            await music_spam_channel.send(f"```fix\nAn error occurred while trying to download the song. Skipping to the next song.```")
            await play_next(interaction)  # Automatically attempt to play the next song
        except Exception as e:
            print(f"[error][play_next] Error playing the song: {e}")
            await music_spam_channel.send(f"```fix\nAn error occurred while trying to play the song. Skipping to the next song.```")

            # If an error occurs, skip to the next song
            await play_next(interaction)  # Automatically attempt to play the next song
    else:
        # No more songs in the queue
        await music_spam_channel.send("The queue is empty, no more songs to play.")


def main() -> None:
    client.run(TOKEN)


if __name__ == "__main__":
    main()