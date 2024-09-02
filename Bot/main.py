# discord imports
from discord.ext import commands
from discord import app_commands
import discord
import discord.ui
from discord.ui import Select, Button, View

# python imports 
from dotenv import load_dotenv
from typing import Final
import asyncio
import time
import os
import json
import sys

# local imports
from functions import send_message_to_user
from help_menu import DeleteView

# 3rd party imports


bot_prefix: str = "/"

# owner ID for private update messages
owner_id: int = 529007366365249546

# role IDs
sancturary_keeper_role_id: int = 1239651704476143766
sky_guardians_role_id: int = 1242514956058890240
tech_oracle_role_id: int = 1274673142153084928
event_luminary_role_id: int = 1240725491099631717
assistaint_role_id: int = 1239681068047532125

allowed_roles: list[int] = [sancturary_keeper_role_id, event_luminary_role_id, sky_guardians_role_id, tech_oracle_role_id, 1266201501924331552] # last one is for testing purpeses

# channel/category IDs
support_category_id: int = 1250699865621794836
general_category_id: int = 1239651600205873324
music_voice_id: int = 1268856363866652784

# channel names
bot_channel_name: str = "🤖bot-spam"
music_channel_name: str = "🎼music-bot"
ticket_channel_name: str = "🎫query-corner"
ticket_logs_channel_name: str = "🎟ticket-logs"

# team settings
max_teams: int = 4
cooldown_period: int = 60

# Initialize the dictionaries and lists
tickets: dict = {}
teams: dict = {}
update_queue: list = []
full_team_cooldowns: dict = {}
voice_clients: dict[int, discord.VoiceChannel] = {}
queues: dict = {}
reaction_tracker: dict = {}

# Create a bot instance
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client: commands.Bot = commands.Bot(command_prefix=bot_prefix, intents=intents)


# Load the environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")
TESTING: Final[str] = os.getenv("TESTING")

# load the command whitelist
dir = os.path.dirname(__file__)
with open(f"{dir}/whitelist.json", "r") as file:
    command_whitelist = json.load(file)["no_error_commands"]
with open(f"{dir}/database.json", "r") as file:
    ticker_menu_url = json.load(file)["ticker_menu_url"]
    

# Startup of the bot
@client.event
async def on_ready() -> None:
    print(f"\n\n[info] Bot is ready as {client.user}\n")
    
    # Set Rich Presence (Streaming)
    if TESTING == "True":
        # Under Development (Do not disturb)
        activity = discord.Activity(type=discord.ActivityType.playing, name="Do not disturb, im getting tested")
        await client.change_presence(status=discord.Status.do_not_disturb, activity=activity)
    else:
        # Streaming PixelPoppyTV (streaming)
        activity = discord.Activity(type=discord.ActivityType.streaming, name="PixelPoppyTV", url="https://www.twitch.tv/pixelpoppytv", details="PixelPoppyTV", state="Sky: Children of The Light")
        await client.change_presence(status=discord.Status.online, activity=activity)
    
    await client.tree.sync()  # Sync slash commands
    
    if TESTING != "True":
        await update_ticket_menu(client, ticker_menu_url)  # Update the ticket menu


@client.tree.command(name="help", description="Lists all available commands.")
async def help_command(interaction: discord.Interaction):
    # Create an embed for displaying the commands
    embed = discord.Embed(title="Dreamy Commands 🍃", description="Here is everything I can do for you!", color=discord.Color.green())
    embed.set_image(url="https://i.postimg.cc/28LPZLBW/20240821214134-1.jpg")
    # Loop through all commands in the CommandTree and add them to the embed
    for command in client.tree.get_commands():
        embed.add_field(name=f"/{command.name}", value=f"```{command.description}```", inline=False)
        
    # Send the embed to the user
    await interaction.response.send_message(embed=embed, view=DeleteView(pages=[embed], timeout=60, allowed_user=interaction.user, ephemeral=True), ephemeral=True)


@client.tree.command(name="ping", description="Check the bot's current latency.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"Pong! that took me {round(client.latency * 1000)}ms to respond")
    print(f"[info] {interaction.user.name} requested the bot's latency, it's {round(client.latency * 1000)}ms")


# info commands
@client.tree.command(name="timers", description="Gives the link to all of the timers.")
async def timers(interaction: discord.Interaction) -> None:
    timer_channel_url = "https://discord.com/channels/1239651599480127649/1252324353115291849/1252324488901824556"
    response = "Here is the url to the channel with all the timers:\n" + timer_channel_url
    print(f"[info] {interaction.user.name} requested the timer")
    await interaction.response.send_message(response)


# ticket commands
async def ticket_callback(interaction: discord.Interaction) -> None:
    support_category = discord.utils.get(interaction.guild.categories, id=support_category_id)
    if not support_category:
        print("[error][tickets] Support category not found. Please provide a valid category ID.")
        await interaction.followup.send("```fix\nSupport category not found. Please provide a valid category ID.```", ephemeral=True)
        return
    
    sky_guardians_role = interaction.guild.get_role(sky_guardians_role_id)
    if not sky_guardians_role:
        print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nSky Guardians role not found. Please provide a valid role ID.```", ephemeral=True)
        return
    
    tech_oracle_role = interaction.guild.get_role(tech_oracle_role_id)
    if not tech_oracle_role:
        print("[error][tickets] Tech Oracle role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nTech Oracle role not found. Please provide a valid role ID.```", ephemeral=True)
        return
    
    owner = await client.fetch_user(owner_id) 
    if not owner:
        print("[error][tickets] owner user not found. Please provide a valid user ID.")
        await interaction.followup.send("```fix\nowner was not found. Please provide a valid user ID.```", ephemeral=True)
        return
    
    select = Select(options=[
        discord.SelectOption(label="Inappropriate Behavior", value="01", emoji="🚫", description="Report someone who is behaving inappropriately"),
        discord.SelectOption(label="Discord Server Issue", value="02", emoji="🛠️", description="Report a discord server issue or bug"),
        discord.SelectOption(label="Bot Issue", value="03", emoji="🤖", description="Report an issue with the Dreamy Assistant bot"),
        discord.SelectOption(label="Other Issue or Subject", value="04", emoji="❓", description="For any and all other issues or questions")
    ])
    
    async def callback(interaction: discord.Interaction):
        await interaction.response.defer()
        if interaction.data["values"][0] == "01": # Inappropriate Behavior
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                sky_guardians_role: discord.PermissionOverwrite(read_messages=True),
                tech_oracle_role: discord.PermissionOverwrite(read_messages=True, manage_messages=True, manage_channels=True)
            }
            
            ticket_name = f"User Report - {interaction.user.display_name}'s - {str(time.time_ns())[-6:]}"
            ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
            tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
            
            print(f"[tickets][inappropriate] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket for Inappropriate Behavior has been created!", ephemeral=True)
            
            # Send DM to Femboipet (replace with actual user ID) and the user
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            button = Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id="Close_ticket")
            button.callback = ticket_close_callback
            view = View(timeout=None)
            view.add_item(button)
            await ticket_channel.send("After you are done you can close this ticket via the button below!", view=view)
            
            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{sky_guardians_role.mention}, {interaction.user.mention} wants to report inappropriate behavior.\nPlease wait until a Sky Guardian is on the case <3\nIn the meantime, please provide as much detail as possible about the behaviour")

            await owner.send(f"A user report ticket has been created by {interaction.user.mention}: {ticket_url}")
            
        elif interaction.data["values"][0] == "02": # Discord Server Issue
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                sky_guardians_role: discord.PermissionOverwrite(read_messages=True),
                tech_oracle_role: discord.PermissionOverwrite(read_messages=True, manage_messages=True, manage_channels=True)
            }
            
            ticket_name = f"Server Issue - {interaction.user.display_name}'s - {str(time.time_ns())[-6:]}"
            ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
            tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
            
            print(f"[tickets][server] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket for an server issue has been created!", ephemeral=True)
            
            # Send DM to Femboipet (replace with actual user ID) and the user
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            button = Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id="Close_ticket")
            button.callback = ticket_close_callback
            view = View(timeout=None)
            view.add_item(button)
            await ticket_channel.send("After you are done you can close this ticket via the button below!", view=view)
            
            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{sky_guardians_role.mention}, {interaction.user.mention} wants to report a server issue.\nPlease wait until a Sky Guardian is on the case <3\nIn the meantime, please provide as much detail as possible about the issue")

            await owner.send(f"A server issue ticket has been created by {interaction.user.mention}: {ticket_url}")
            
        elif interaction.data["values"][0] == "03": # Bot Issues, no need for Sky Guardians
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                sky_guardians_role: discord.PermissionOverwrite(read_messages=False),
                tech_oracle_role: discord.PermissionOverwrite(read_messages=True, manage_messages=True, manage_channels=True)
            }
            
            ticket_name = f"Bot Issue - {interaction.user.display_name}'s - {str(time.time_ns())[-6:]}"
            ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
            tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
            
            print(f"[tickets][bot] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket about an issue with the bot has been created!", ephemeral=True)
            
            # Send DM to Femboipet (replace with actual user ID) and the user
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            button = Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id="Close_ticket")
            button.callback = ticket_close_callback
            view = View(timeout=None)
            view.add_item(button)
            await ticket_channel.send("After you are done you can close this ticket via the button below!", view=view)
            
            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{tech_oracle_role.mention}, {interaction.user.mention} wants to report a issue with the bot.\nPlease wait until an Tech Oracle is on the case <3\nIn the meantime, please provide as much detail as possible about the issue with the bot")

            await owner.send(f"A bot related issue ticket has been created by {interaction.user.mention}: {ticket_url}")
            
        elif interaction.data["values"][0] == "04": # Other Issue or Subject
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                sky_guardians_role: discord.PermissionOverwrite(read_messages=True),
                tech_oracle_role: discord.PermissionOverwrite(read_messages=True, manage_messages=True, manage_channels=True)
            }
            
            ticket_name = f"Other - {interaction.user.display_name}'s - {str(time.time_ns())[-6:]}"
            ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
            tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
            
            print(f"[tickets][other] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A general ticket has been created!", ephemeral=True)
            
            # Send DM to Femboipet (replace with actual user ID) and the user
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            button = Button(style=discord.ButtonStyle.danger, label="Close Ticket", custom_id="Close_ticket")
            button.callback = ticket_close_callback
            view = View(timeout=None)
            view.add_item(button)
            await ticket_channel.send("After you are done you can close this ticket via the button below!", view=view)
            
            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{sky_guardians_role.mention}, {interaction.user.mention} has an general issue or question.\nPlease wait until a Sky Guardian is on the case <3\nIn the meantime, please provide the context of the issue or question")
            
            await owner.send(f"An general ticket has been created by {interaction.user.mention}: {ticket_url}")
            
        else: # Invalid selection
            await interaction.followup.send("Invalid selection", ephemeral=True)
    select.callback = callback
    view = View(timeout=None)
    view.add_item(select)
    await interaction.response.send_message("Select the type of ticket you would like to create.", view=view, ephemeral=True)


async def ticket_close_callback(interaction: discord.Interaction) -> None:
    sky_guardians_role = interaction.guild.get_role(sky_guardians_role_id)
    if not sky_guardians_role:
        print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nSky Guardians role not found. Please provide a valid role ID.```", ephemeral=True)
        return
    
    tech_oracle_role = interaction.guild.get_role(tech_oracle_role_id)
    if not tech_oracle_role:
        print("[error][tickets] Tech Oracle role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nTech Oracle role not found. Please provide a valid role ID.```", ephemeral=True)
        return
    
    # Check if the channel is indeed a ticket channel
    # should not be needed
    if not interaction.channel.id in tickets:
        await interaction.followup.send("No open ticket found in this channel or you do not have permission to close this ticket.", ephemeral=True)
        print(f"[error][close_ticket_menu] No open ticket found in channel {interaction.channel.name}")
        return
    
    ticket_info = tickets[interaction.channel.id]
    
    select = Select(options=[
        discord.SelectOption(label="Yes, close this ticket", value="01", emoji="☑️", description="This closes the ticket and will mark it as solved"),
        discord.SelectOption(label="No, keep this ticket open", value="02", emoji="✖️", description="This will keep the ticket open and allow you to continue the conversation"),
    ])
    
    async def callback(interaction: discord.Interaction):
        await interaction.response.defer()
        if interaction.data["values"][0] == "01": # close the ticket
            # Check if the author is the ticket creator or in Sky Guardians role or Tech Oracle role
            if interaction.user.id == ticket_info["user_id"] or sky_guardians_role in interaction.user.roles or tech_oracle_role in interaction.user.roles:
                ticket_logs = f""
                async for message in interaction.channel.history(limit=None):
                    ticket_logs = f"{message.author.name}: {message.content}\n" + str(ticket_logs)
                ticket_logs = f"Transcript for {interaction.channel.name}:\n" + "```\n"+ str(ticket_logs) + "```"

                ticket_logs_channel = discord.utils.get(interaction.guild.text_channels, name=ticket_logs_channel_name)
                if ticket_logs_channel:
                    await ticket_logs_channel.send(ticket_logs)
                
                print(f"[tickets] Ticket closed by user {interaction.user.name} in channel {interaction.channel.name}")
                user = await client.fetch_user(ticket_info["user_id"])
                await interaction.followup.send(f"Your ticket has been closed successfully. Transcript saved in {ticket_logs_channel} channel.")
                await interaction.channel.delete()
                await user.send(f"Your ticket has been closed successfully. The Transcript of the ticket has been saved.")
                await user.send(ticket_logs)
                del tickets[interaction.channel.id]
            else:
                print(f"[warning][tickets] {interaction.user.name} does not have prems to close ticket {interaction.channel.name}")
        elif interaction.data["values"][0] == "02": # keep the ticket open
            await interaction.followup.send("Ticket will remain open.", ephemeral=True)
        else: # Invalid selection
            await interaction.followup.send("Invalid selection", ephemeral=True)
    select.callback = callback
    view = View(timeout=None)
    view.add_item(select)
    await interaction.response.send_message("Do you really want to close the ticket?", view=view, ephemeral=True)


@client.tree.command(name="ticket_menu", description="Create a ticket create menu.")
async def ticket(interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("```fix\nYou do not have permission to create a ticket menu.```", ephemeral=True)
        return
    button = Button(style=discord.ButtonStyle.green, label="📬 Create a Ticket", custom_id="ticket_menu")
    button.callback = ticket_callback
    view = View(timeout=None)
    view.add_item(button)
    await interaction.followup.send(
        "How to Submit Tickets:\n\n1. Click the button below to create a ticket.\n2. Choose the type of ticket you would like to create.\n3. A ticket channel will be created for you.\n4. Give as much detail as possible about the issue or question.\n5. Wait for response.\n6. Close ticket when response has been received.\n\n**Tickets remain saved on our side, so when you close a ticket we are still able to review the ticket and delete it afterwards.**", 
        view=view)


# Team commands
@client.tree.command(name="createteam", description="Create a team with a leader and an emoji.")
async def createteam(interaction: discord.Interaction, member: discord.Member, emoji: str) -> None:
    await interaction.response.defer(ephemeral=True)  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to create a team.", ephemeral=True)
        return
    
    if member.id in teams:
        await interaction.followup.send("This user already leads a team.", ephemeral=True)
        return

    if len(teams) >= max_teams:
        await interaction.followup.send("The maximum number of teams has been reached. Cannot create a new team.", ephemeral=True)
        return
    
    emoji = emoji.strip(":")  # Remove the colons from the emoji if present
    print(f"[teams] Creating a team with {member.name}:{member.id} as the leader and {emoji} as the emoji.")
    
    await interaction.followup.send(f"Team {emoji} has been created!", ephemeral=False)
    team_message = f"__**Group Leader**__\n{member.mention} {emoji}\n\n__**Members**__\n"

    message = await interaction.channel.send(team_message)

    # Add the bot's reaction
    await message.add_reaction(emoji)

    # Save team information
    teams[member.id] = {
        "message_id": message.id,
        "emoji": emoji,
        "members": [],
        "max_members": 8,  # Max members in the team
        "leader_id": member.id,
        "reaction_count": 1,  # Start with 1 to count the team leader
        "last_locked_message_time": 0,
        "locked": False,  # Initialize the locked state
        "channel_id": interaction.channel.id,  # Track the channel ID
        "resetting": False  # Track if the team is currently resetting
    }


@client.tree.command(name="closeteam", description="Close the given leader's team.")
async def closeteam(interaction: discord.Interaction, member: discord.Member) -> None:
    await interaction.response.defer(ephemeral=True)  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to close a team.", ephemeral=True)
        return
    
    if member.id not in teams:
        await interaction.followup.send(f"A team led by {member.mention} not found.", ephemeral=True)
        return
    
    team_data = teams[member.id]
    
    # Check if the team is locked
    if team_data["locked"] == False: 
        await interaction.followup.send(f"Team {team_data['emoji']} led by {member.mention} is not currently locked. Please lock the team first.", ephemeral=True)
        return
    team_data["closed"] = True  # Set the closed flag
    channel = client.get_channel(team_data["channel_id"])  # Get the team's channel
    message = await channel.fetch_message(team_data["message_id"])  # Fetch the message
    await message.delete()  # Delete the message

    del teams[member.id]  # Remove the team from the dictionary
    await interaction.channel.send(f"Team {team_data['emoji']} led by {member.mention} has been closed.")
    await interaction.followup.send(f"Team {team_data['emoji']} led by {member.mention} has been closed.", ephemeral=False)


@client.tree.command(name="lockteam", description="Lock the given leader's team.")
async def lockteam(interaction: discord.Interaction, member: discord.Member) -> None:
    await interaction.response.defer(ephemeral=True)  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to lock a team.", ephemeral=True)
        return
        
    if member.id not in teams:
        await interaction.followup.send(f"A team led by {member.mention} not found.", ephemeral=True)
        return
        
    team_data = teams[member.id]
    message_id = team_data["message_id"]
    
    if team_data["locked"] == True: 
        await interaction.followup.send(f"Team {team_data['emoji']} is already locked.", ephemeral=True)
        return
    
    # Retrieve the team message
    message = await interaction.channel.fetch_message(message_id)
    
    # Update the message to indicate the team is locked
    updated_message = message.content + "\n\n__**Team Full**__ - This team has been locked ^^"
    update_queue.append((message_id, updated_message))

    # Set the locked flag for the team
    teams[member.id]["locked"] = True
    await interaction.followup.send(f"Team {team_data['emoji']} has been locked.", ephemeral=False)
    await interaction.channel.send(f"Team {team_data['emoji']} has been locked.")


@client.tree.command(name="unlockteam", description="Unlock a given leader's team.")
async def unlockteam(interaction: discord.Interaction, member: discord.Member) -> None:
    await interaction.response.defer(ephemeral=True)  # Defer the response to get more time
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to unlock a team.", ephemeral=True)
        return
    
    if member.id not in teams:
        await interaction.followup.send(f"A team led by {member.mention} not found.", ephemeral=True)
        return
    
    team_data = teams[member.id]
    message_id = team_data["message_id"]

    if team_data["locked"] == False:
        await interaction.followup.send("Team is not locked.", ephemeral=True)
        return

    # Prevent modifications during the reset phase
    teams[member.id]["resetting"] = True

    # Retrieve the team message
    message = await interaction.channel.fetch_message(message_id)

    # Update the message to indicate the reset procedure
    reset_message = f"__**Group Leader**__\n{client.get_user(team_data['leader_id']).mention} :{team_data['emoji']}:\n\n__**Members**__\n<> The bot is currently resetting the player list. Please wait. <>"
    await message.edit(content=reset_message)
    
    wait_message = await interaction.channel.send("Please wait for the team to unlock...")
    await interaction.followup.send(f"Team {team_data['emoji']} will be unlocked", ephemeral=True)

    # Adding a delay to simulate the refresh time
    await asyncio.sleep(2)

    # Rebuild the team members list based on the reaction order
    if member.id in reaction_tracker:
        # Sort the users based on the timestamp of when they reacted
        sorted_reactors = sorted(reaction_tracker[member.id], key=lambda x: x["timestamp"])

        team_data["members"] = []  # Start with an empty list
        for reactor in sorted_reactors:
            if len(team_data["members"]) < team_data["max_members"]:
                team_data["members"].append(reactor["user_id"])
                print(f"[teams] Added user {reactor['user_id']} to team {team_data['leader_id']} after unlocking.")
        
        # Inform the channel if the team is full again
        if len(team_data["members"]) >= team_data["max_members"]:
            teams[member.id]["locked"] = True

        # Update the team message to reflect the current state
        member_mentions = [
            client.get_user(member_id).mention for member_id in team_data["members"] if member_id != team_data["leader_id"]
        ]
        member_names_str = "\n".join(member_mentions)
        final_message = f"__**Group Leader**__\n{client.get_user(team_data['leader_id']).mention} :{team_data['emoji']}:\n\n__**Members**__\n<*> Fixing the member list UwU <*>"

        if member_names_str:
            final_message += f"\n\n{member_names_str}"
        await message.edit(content=final_message)

    # Remove resetting status and unlock the team
    teams[member.id]["resetting"] = False
    teams[member.id]["locked"] = False
    
    await interaction.channel.send(f"Team {team_data['emoji']} has been unlocked.")

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
                if team["resetting"]:
                    return
                
                # Skip updating members list if team is locked
                if team["locked"]: 
                    return

                user = await client.fetch_user(user_id)  # Fetch the user who reacted

                if user_id != team_leader_id:
                    if user_id not in team["members"]:  # Only add if not already in the team
                        team["reaction_count"] += 1

                        # Track the reaction order
                        if team_id not in reaction_tracker:
                            reaction_tracker[team_id] = []
                        if not any(entry['user_id'] == user_id for entry in reaction_tracker[team_id]):
                            reaction_tracker[team_id].append({"user_id": user_id, "timestamp": time.time()})

                        # Check if team is full and not locked yet
                        if len(team["members"]) + 1 < team["max_members"]:
                            team["members"].append(user_id)  # Add member to the list
                            print(f"[teams] Added user {user_id} to team {team_leader_id}")
                            print(f"this team now has {len(team['members']) + 1} members including the leader")
                            print(team["members"])
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
                                member = await client.fetch_user(member_id)  # Fetch the user from the Discord API
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
                        if len(team["members"]) + 1 >= team["max_members"]:
                            team["locked"] = True
                            await channel.send(f"{client.get_user(team_leader_id).mention} group is now locked!")

                    else:
                        # User is already in the team
                        team["reaction_count"] -= 1


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    message_id = payload.message_id
    user_id = payload.user_id

    for team_id, team in teams.items():
        if message_id == team["message_id"]:
            if user_id in team["members"]:
                
                # Skip updating members list if team is resetting
                if team["resetting"] == True:
                    return
                
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


# dev commands
@client.tree.command(name="dev", description="Creates a hidden dev channel.")
async def dev(interaction: discord.Interaction, name: str) -> None:
    await interaction.response.defer()  # Defer the response to get more time
    if not any(role.id in [tech_oracle_role_id] for role in interaction.user.roles):
        await interaction.followup.send("```fix\nYou do not have permission to create a dev channel.```", ephemeral=True)
        return
    
    general_category = discord.utils.get(interaction.guild.categories, id=general_category_id)
    if not general_category:
        print("[error][dev] general category not found. Please provide a valid category ID.")
        await interaction.followup.send("```fix\ngeneral category not found. Please provide a valid category ID.```", ephemeral=True)
        return
    
    tech_oracle = interaction.guild.get_role(tech_oracle_role_id)
    if not tech_oracle:
        print("[error][dev] Tech Oracle role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nTech Oracle not found. Please provide a valid role ID.```", ephemeral=True)
        return
    
    assistaint = discord.utils.get(interaction.guild.roles, id=assistaint_role_id)
    if not assistaint:
        print("[error][dev] Assistaint (bot) role not found. Please provide a valid role ID.")
        await interaction.followup.send("```fix\nAssistaint not found. Please provide a valid role ID.```", ephemeral=True)
        return
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
        interaction.user: discord.PermissionOverwrite(read_messages=True),
        tech_oracle: discord.PermissionOverwrite(read_messages=True, manage_channels=True, manage_messages=True),
        assistaint: discord.PermissionOverwrite(read_messages=True, manage_channels=True, manage_messages=True)
    }

    def_channel = await interaction.guild.create_text_channel(name=name, category=general_category, overwrites=overwrites, reason="Created a channel for tech oracle dev")
    
    print(f"[dev] Dev channel created for user {interaction.user.name} in channel {def_channel.name}")
    
    await interaction.followup.send("a dev channel has been created!")
    # Send DM to Femboipet (replace with actual user ID) and the user
    femboipet = await client.fetch_user(owner_id)
    channel_url = f"https://discord.com/channels/{interaction.guild.id}/{def_channel.id}"
    await send_message_to_user(client, interaction.user.id, f"Your dev channel has been created: {channel_url}")

    await femboipet.send(f"There has been created an dev channel named `{def_channel.name}` by {interaction.user.mention}: {channel_url}")


# Command to delete a message by its link
@client.tree.command(name="delete_message", description="Delete a message by its link")
async def delete_message(interaction: discord.Interaction, message_link: str):
    if not any(role.id in [tech_oracle_role_id] for role in interaction.user.roles):
        await interaction.response.send_message("```fix\nYou do not have permission to create a team.```", ephemeral=True)
        return
    try:
        # Parse the message link to extract guild_id, channel_id, and message_id
        parts = message_link.split('/')
        if len(parts) < 7 or not message_link.startswith("https://discord.com/channels/"):
            await interaction.response.send_message("Invalid message link format.", ephemeral=True)
            return

        guild_id = int(parts[4])
        channel_id = int(parts[5])
        message_id = int(parts[6])

        # Ensure the bot is in the correct guild (server)
        if interaction.guild_id != guild_id:
            await interaction.response.send_message("The message is from another server.", ephemeral=True)
            return

        # Fetch the channel and message
        channel = client.get_channel(channel_id)
        if channel is None:
            await interaction.response.send_message("Channel not found.", ephemeral=True)
            return

        message = await channel.fetch_message(message_id)
        if message is None:
            await interaction.response.send_message("Message not found.", ephemeral=True)
            return

        # Delete the message
        await message.delete()
        await interaction.response.send_message(f"Message deleted successfully.", ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to delete that message.", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("An error occurred while trying to delete the message.", ephemeral=True)


# Error handling for command not found
@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        command = ctx.message.content.lower().strip(bot_prefix)
        if command in command_whitelist:
            print(f"[info] {ctx.author} tried to use an whitelisted command in channel {ctx.channel}: {ctx.message.content}")
            return
        print(f"[warning] {ctx.author} tried to use an unknown command in channel {ctx.channel}: {ctx.message.content}")
        # await ctx.send(f"Command not found! Please check your command or use `/help` for available commands.")
        await ctx.reply(f"Command not found! Please check your command or use `/help` for available commands.", ephemeral=True, delete_after=10)
        await ctx.message.delete(delay=10)
    else:
        # Raise the error if it's not CommandNotFound
        raise error


# updating the ticket_menu message upon bot restart
async def update_ticket_menu(client: commands.Bot, message_link: str):
    try:
        # Parse the message link to extract guild_id, channel_id, and message_id
        parts = message_link.split('/')
        if len(parts) < 7 or not message_link.startswith("https://discord.com/channels/"):
            print("[error][ticket_update] ticket_menu link is not valid.")
            return

        guild_id = int(parts[4])
        channel_id = int(parts[5])
        message_id = int(parts[6])
        
        # Fetch the channel and message
        channel = client.get_channel(channel_id)
        if channel is None:
            print("[error][ticket_update] Channel not found.")
            return
        
        # Ensure the bot is in the correct guild (server)
        if channel.guild.id != guild_id:
            print("[error][ticket_update] guild does not match up.")
            return

        message = await channel.fetch_message(message_id)
        if message is None:
            print("[error][ticket_update] ticket_menu message not found.")
            return

        # update ticket_menu message
        button = Button(style=discord.ButtonStyle.green, label="📬 Create a Ticket", custom_id="ticket_menu")
        button.callback = ticket_callback
        view = View(timeout=None)
        view.add_item(button)
    
        await message.edit(content="How to Submit Tickets:\n\n1. Click the button below to create a ticket.\n2. Choose the type of ticket you would like to create.\n3. A ticket channel will be created for you.\n4. Give as much detail as possible about the issue or question.\n5. Wait for response.\n6. Close ticket when response has been received.\n\n**Tickets remain saved on our side, so when you close a ticket we are still able to review the ticket and delete it afterwards.**", view=view)
        print("[info] updated the ticket_menu.")

    except discord.Forbidden:
        print("[error][ticket_update] Ticket_menu could not be updated due to a lack of premissions.")
    except discord.HTTPException:
        print("[error][ticket_update] An error occurred while trying to update the ticket_menu message.")


def main() -> None:
    client.run(TOKEN)


if __name__ == "__main__":
    main()