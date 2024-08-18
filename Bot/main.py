from typing import Final
import os
import time
from dotenv import load_dotenv
import discord as disc
from discord.ext import commands
from discord.types.activity import ActivityAssets
import asyncio
from functions import send_message_to_user

# Load the environment variables
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# Bot settings
allowed_roles: list[int] = [1240725491099631717, 1242514956058890240, 1274673142153084928, 1266201501924331552] # last one is for testing purpeses
sky_guardians_role_id: int = 1242514956058890240
owner_id: int = 529007366365249546
support_category_id = 1250699865621794836
max_teams = 4

tickets: dict = {}
teams: dict = {}
update_queue: list = []
full_team_cooldowns: dict = {}
cooldown_period: int = 60  # 60 seconds cooldown

# Create a bot instance
intents: disc.Intents = disc.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix="/", intents=intents)

# Startup of the bot
@client.event
async def on_ready():
    print(f"\n[info] Bot is ready as {client.user}\n")
    
    # Set Rich Presence (Activity)
    activity = disc.Activity(type=disc.ActivityType.streaming, name="PixelPoppyTV", url="https://www.twitch.tv/pixelpoppytv", details="PixelPoppyTV", state="Sky: Children of The Light")
    
    await client.change_presence(status=disc.Status.online, activity=activity)
    await client.tree.sync()  # Sync slash commands


@client.tree.command(name="timers", description="Get the link to the timers channel")
async def timers(interaction: disc.Interaction):
    timer_channel_link = "https://discord.com/channels/1239651599480127649/1252324353115291849/1252324488901824556"
    response = "Here is the link to the channel with all the timers: " + timer_channel_link
    print(f"[info] {interaction.user.name} requested the timer")
    await interaction.response.send_message(response)


@client.tree.command(name="openticket", description="Open a ticket")
async def openticket(interaction: disc.Interaction, name: str = "Open Ticket", description: str = "Command to open a ticket!"):
    if not interaction.channel.name == "🎫query-corner":
        await interaction.response.send_message("Please use this command in the 🎫query-corner channel.")
        return
    
    support_category = disc.utils.get(interaction.guild.categories, id=support_category_id)
    if not support_category:
        print("[error][tickets] Support category not found. Please provide a valid category ID.")
        await interaction.response.send_message("Support category not found. Please provide a valid category ID.")
        return
    
    sky_guardians_role = interaction.guild.get_role(sky_guardians_role_id)
    if not sky_guardians_role:
        print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
        await interaction.response.send_message("Sky Guardians role not found. Please provide a valid role ID.")
        return
    
    overwrites = {
        interaction.guild.default_role: disc.PermissionOverwrite(read_messages=False),
        interaction.guild.me: disc.PermissionOverwrite(read_messages=True),
        interaction.user: disc.PermissionOverwrite(read_messages=True),
        sky_guardians_role: disc.PermissionOverwrite(read_messages=True)
    }

    ticket_name = f"ticket-{interaction.user.name}" if not name else f"{name}'s ticket"
    ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
    tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
    
    print(f"[tickets] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
    
    await interaction.response.send_message("A ticket has been created!", ephemeral=True)
    # Send DM to Femboipet (replace with actual user ID) and the user
    femboipet = await client.fetch_user(owner_id) 
    ticket_link = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
    await send_message_to_user(client, interaction.user.id, f"Your ticket has been created: {ticket_link}")
    
    # Notify user and ping Sky Guardians role
    await ticket_channel.send(f"{sky_guardians_role.mention}, {interaction.user.mention} needs assistance. Please wait until a Sky Guardian is on the case <3\n\nThe ticket is called '{str(name)}' and is about '{str(description)}'")

    await femboipet.send(f"A ticket has been created by {interaction.user.mention}: {ticket_link}")


@client.tree.command(name="closeticket", description="Close the current ticket")
async def closeticket(interaction: disc.Interaction):
    sky_guardians_role = interaction.guild.get_role(sky_guardians_role_id)
    
    # Check if the channel is indeed a ticket channel
    if not interaction.channel.id in tickets:
        await interaction.response.send_message("No open ticket found in this channel or you do not have permission to close this ticket.")
        print(f"[tickets] No open ticket found in channel {interaction.channel.name}")
        return
    
    ticket_info = tickets[interaction.channel.id]
    
    # Check if the author is the ticket creator or in Sky Guardians role
    if interaction.user.id == ticket_info["user_id"] or sky_guardians_role in interaction.user.roles:
        ticket_logs = f"```"
        async for message in interaction.channel.history(limit=None):
            ticket_logs = f"{message.author.name}: {message.content}\n" + str(ticket_logs)
        ticket_logs = f"Transcript for ticket-{interaction.user.name}:\n```" + str(ticket_logs)

        ticket_logs_channel = disc.utils.get(interaction.guild.text_channels, name="🎟ticket-logs")
        if ticket_logs_channel:
            await ticket_logs_channel.send(ticket_logs)
        
        print(f"[tickets] Ticket closed by user {interaction.user.name} in channel {interaction.channel.name}")

        await interaction.response.send_message("Your ticket has been closed successfully. Transcript saved in 🎟ticket-logs channel.")
        await interaction.channel.delete()
        del tickets[interaction.channel.id]
        await interaction.user.send("Your ticket has been closed successfully. Transcript saved in 🎟ticket-logs channel.")
        await interaction.user.send(ticket_logs)
        


@client.tree.command(name="createteam", description="Create a team")
async def createteam(interaction: disc.Interaction, member: disc.Member, emoji: str):
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to create a team.")
        return
    
    if member.id in teams:
        await interaction.response.send_message("This user already leads a team.")
        return

    if len(teams) >= max_teams:
        await interaction.response.send_message("The maximum number of teams has been reached. Cannot create a new team.")
        return
    
    print(f"[teams] Creating a team with {member.name}:{member.id} as the leader and {emoji} as the emoji.")
    
    await interaction.response.send_message(f"Team {emoji} has been created!")
    team_message = f"__**Group Leader**__\n{member.mention} :{emoji}:\n\n__**Members**__\n"
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
async def closeteam(interaction: disc.Interaction, member: disc.Member):
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to close a team.")
        return
    
    if not member.id in teams:
        await interaction.response.send_message(f"A team lead by {member.mention} not found.")
        return
    
    team_data = teams[member.id]
    
    # Check if the team is already locked
    if team_data["locked"] == False: 
        await interaction.response.send_message(f"Team {team_data['emoji']} led by {member.mention} is not currently locked. Please lock the team first.")
        return
    team_data["closed"] = True  # Set the closed flag
    channel = client.get_channel(team_data["channel_id"])  # Get the team's channel
    message = await channel.fetch_message(team_data["message_id"])  # Fetch the message
    await message.delete()  # Delete the message

    del teams[member.id]  # Remove the team from the dictionary

    await interaction.response.send_message(f"Team {team_data['emoji']} led by {member.mention} has been closed.")


@client.tree.command(name="lockteam", description="Lock a team")
async def lockteam(interaction: disc.Interaction, member: disc.Member):
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to lock a team.")
        return
        
    if member.id not in teams:
        await interaction.response.send_message(f"A team lead by {member.mention} not found.")
        return
        
    team_data = teams[member.id]
    message_id = team_data["message_id"]
    
    if team_data["locked"] == True: 
        await interaction.response.send_message(f"Team {team_data['emoji']} is already locked.")
        return
    
    # Retrieve the team message
    message = await interaction.channel.fetch_message(message_id)
    
    # Update the message to indicate the team is locked
    updated_message = message.content + "\n\n__**Team Full**__ - This team has been locked ^^"
    update_queue.append((message_id, updated_message))

    # Set the locked flag for the team
    teams[member.id]["locked"] = True
    await interaction.response.send_message(f"Team {team_data['emoji']} has been locked.")


@client.tree.command(name="unlockteam", description="Unlock a team")
async def unlockteam(interaction: disc.Interaction, member: disc.Member):
    if not any(role.id in allowed_roles for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to unlock a team.")
        return
    
    if member.id not in teams:
        await interaction.response.send_message("Team not found.")
        return
    
    team_data = teams[member.id]
    message_id = team_data["message_id"]

    if team_data["locked"] == False:
        await interaction.response.send_message("Team is not locked.")
        return
        
    # Prevent modifications during the reset phase
    teams[member.id]["resetting"] = True

    # Retrieve the team message
    message = await interaction.channel.fetch_message(message_id)

    # Update the message to indicate the reset procedure
    reset_message = f"__**Group Leader**__\n{client.get_user(team_data['leader_id']).mention} :{team_data['emoji']}:\n\n__**Members**__\n<> The bot is currently Resetting the player list, give it a few seconds to refresh <>"
    await message.edit(content=reset_message)
    
    wait_message = await interaction.channel.send("Please wait for the team to unlock...")
    await interaction.response.send_message(f"Team {team_data['emoji']} will be unlocked")
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


@client.event
async def on_raw_reaction_add(payload):
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
                            except disc.NotFound:
                                # Handle the case where the user cannot be found
                                print(f"[teams] User with ID {member_id} not found.")
                            except Exception as e:
                                print(f"[teams] An error occurred while fetching user {member_id}: {e}")

                        member_names_str = "\n".join(member_mentions)

                        # Safely get the team leader user and handle the case where it might return None
                        try:
                            team_leader = await client.fetch_user(team_leader_id)
                        except disc.NotFound:
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
                                except disc.NotFound:
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
async def on_raw_reaction_remove(payload):
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
                        except disc.NotFound:
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


def main() -> None:
    client.run(TOKEN)


if __name__ == "__main__":
    main()