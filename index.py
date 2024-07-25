import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import time
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

allowed_roles = [1240725491099631717, 1242514956058890240]
tickets = {}
teams = {}
update_queue = []
full_team_cooldowns = {}
cooldown_period = 60  # 60 seconds cooldown

client = commands.Bot(command_prefix="/", intents=discord.Intents.all())

@client.event
async def on_ready():
    print("Bot is connected to Discord")
    # No cooldowns needed
    await client.tree.sync()  # Sync slash commands
    process_update_queue.start()

@client.tree.command(name="timers", description="Get the link to the timers channel")
async def timers(interaction: discord.Interaction):
    timer_channel_link = "https://discord.com/channels/1239651599480127649/1252324353115291849"
    response = "Here is the link to the channel with all the timers: " + timer_channel_link
    await interaction.response.send_message(response)

@client.tree.command(name="openticket", description="Open a ticket")
async def openticket(interaction: discord.Interaction, name: str = "Open Ticket", description: str = "Command to open a ticket!"):
    if interaction.channel.name == "🎫query-corner":
        support_category_id = 1250699865621794836
        support_category = discord.utils.get(interaction.guild.categories, id=support_category_id)

        if support_category:
            sky_guardians_role = interaction.guild.get_role(1242514956058890240)

            if sky_guardians_role:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                    interaction.user: discord.PermissionOverwrite(read_messages=True),
                    sky_guardians_role: discord.PermissionOverwrite(read_messages=True)
                }

                ticket_name = f"ticket-{interaction.user.name}" if not name else f"{name}'s ticket"
                ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
                tickets[ticket_channel.id] = {"user_id": interaction.user.id, "channel_id": ticket_channel.id}
                
                # Notify user and ping Sky Guardians role
                await ticket_channel.send(f"{sky_guardians_role.mention}, {interaction.user.mention} needs assistance. Please wait until a Sky Guardian is on the case <3")

                # Send DM to Femboipet (replace with actual user ID) and the user
                femboipet = await client.fetch_user(529007366365249546) 
                ticket_link = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
                await femboipet.send(f"A ticket has been created by {interaction.user.mention}: {ticket_link}")
                await interaction.user.send(f"Your ticket has been created: {ticket_link}")

                await interaction.response.send_message("Ticket created!", ephemeral=True)
            else:
                await interaction.response.send_message("Sky Guardians role not found. Please provide a valid role ID.")
        else:
            await interaction.response.send_message("Support category not found. Please provide a valid category ID.")
    else:
        await interaction.response.send_message("Please use this command in the 🎫query-corner channel.")

@client.tree.command(name="closeticket", description="Close the current ticket")
async def closeticket(interaction: discord.Interaction):
    sky_guardians_role = interaction.guild.get_role(1242514956058890240)
    
    # Check if the channel is indeed a ticket channel
    if interaction.channel.id in tickets:
        ticket_info = tickets[interaction.channel.id]
        
        # Check if the author is the ticket creator or in Sky Guardians role
        if interaction.user.id == ticket_info["user_id"] or sky_guardians_role in interaction.user.roles:
            ticket_logs = f"Transcript for ticket-{interaction.user.name}:\n```"
            async for message in interaction.channel.history(limit=None):
                ticket_logs += f"{message.author.name}: {message.content}\n"
            ticket_logs += "```"

            ticket_logs_channel = discord.utils.get(interaction.guild.text_channels, name="🎟ticket-logs")
            if ticket_logs_channel:
                await ticket_logs_channel.send(ticket_logs)

            await interaction.channel.delete()
            del tickets[interaction.channel.id]
            await interaction.user.send("Your ticket has been closed successfully. Transcript saved in 🎟ticket-logs channel.")
            return

    await interaction.response.send_message("No open ticket found in this channel or you do not have permission to close this ticket.")

@client.tree.command(name="createteam", description="Create a team")
async def createteam(interaction: discord.Interaction, member: discord.Member, emoji: str):
    if any(role.id in allowed_roles for role in interaction.user.roles):
        team_leader = interaction.guild.get_member(member.id)  # Get the member from the guild
        emoji = emoji.strip(":")  # Remove surrounding colons

        if team_leader.id in teams:
            await interaction.response.send_message("This user already leads a team.")
            return

        if len(teams) >= 4:
            await interaction.response.send_message("The maximum number of teams has been reached. Cannot create a new team.")
            return

        team_message = f"__**Group Leader**__\n{team_leader.mention} :{emoji}:\n\n__**Members**__\n"
        # Defer the interaction, so we can send the message and add the reaction later
        await interaction.response.defer()  
        message = await interaction.channel.send(team_message)

        # Add the bot's reaction
        await message.add_reaction(emoji)

        # Save team information
        teams[team_leader.id] = {
            "message_id": message.id,
            "emoji": emoji,
            "members": [],
            "max_members": 8,  # assigns max members of team
            "leader_id": team_leader.id,
            "reaction_count": 1,  # Start with 1 to count the team leader
            "last_locked_message_time": 0,
            "locked": False,  # Initialize the locked state
            "channel_id": interaction.channel.id  # Track the channel ID
        }

    else:
        await interaction.response.send_message("You do not have permission to create a team.")

@client.tree.command(name="lockteam", description="Lock a team")
async def lockteam(interaction: discord.Interaction, member: discord.Member):
    if any(role.id in allowed_roles for role in interaction.user.roles):
        if member.id in teams:
            team_data = teams[member.id]
            message_id = team_data["message_id"]
            
            # Retrieve the team message
            message = await interaction.channel.fetch_message(message_id)
            
            # Update the message to indicate the team is locked
            updated_message = message.content + "\n\n__**Team Full**__ - This team has been locked ^^"
            update_queue.append((message_id, updated_message))
    
            # Set the locked flag for the team
            teams[member.id]["locked"] = True
            await interaction.response.send_message("Team has been locked.")
        else:
            await interaction.response.send_message("Team not found.")
    else:
        await interaction.response.send_message("You do not have permission to lock a team.")

@client.tree.command(name="unlockteam", description="Unlock a team")
async def unlockteam(interaction: discord.Interaction, member: discord.Member):
    if any(role.id in allowed_roles for role in interaction.user.roles):
        if member.id in teams:
            team_data = teams[member.id]
            message_id = team_data["message_id"]

            if team_data.get("locked", False):
                # Prevent modifications during the reset phase
                teams[member.id]["resetting"] = True

                # Retrieve the team message
                message = await interaction.channel.fetch_message(message_id)

                # Update the message to indicate the reset procedure
                reset_message = f"__**Group Leader**__\n{client.get_user(team_data['leader_id']).mention} :{team_data['emoji']}:\n\n__**Members**__\n<> The bot is currently Resetting the player list, give it 5 seconds to refresh <>"
                await message.edit(content=reset_message)
                
                await interaction.response.send_message("Team has been unlocked and is resetting. Please wait...")

                # Adding a delay to simulate the refresh time
                await asyncio.sleep(5)

                # Capture all users who currently have the reaction
                current_reactors = set()
                for reaction in message.reactions:
                    if str(reaction.emoji) == team_data["emoji"]:
                        async for user in reaction.users():
                            if user.id != client.user.id and user.id != team_data["leader_id"]:
                                current_reactors.add(user.id)

                # Rebuild the team members list
                team_data["members"] = [team_data["leader_id"]]  # Start with leader only
                for user_id in current_reactors:
                    if len(team_data["members"]) < team_data["max_members"]:
                        team_data["members"].append(user_id)
                        print(f"Added user {user_id} to team {team_data['leader_id']} after unlocking.")

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
            else:
                await interaction.response.send_message("Team is not locked.")
        else:
            await interaction.response.send_message("Team not found.")
    else:
        await interaction.response.send_message("You do not have permission to unlock a team.")

@client.tree.command(name="closeteam", description="Close the team")
async def closeteam(interaction: discord.Interaction, member: discord.Member):
    if any(role.id in allowed_roles for role in interaction.user.roles):
        if member.id in teams:
            team_data = teams[member.id]
            
            # Check if the team is already locked
            if team_data.get("locked", False): 
                team_data["closed"] = True  # Set the closed flag
                channel = client.get_channel(team_data["channel_id"])  # Get the team's channel
                message = await channel.fetch_message(team_data["message_id"])  # Fetch the message
                await message.delete()  # Delete the message

                del teams[member.id]  # Remove the team from the dictionary

                await interaction.response.send_message(f"The team led by {member.mention} has been closed.")
            else:
                await interaction.response.send_message(f"The team led by {member.mention} is not currently locked. Please lock the team first.")
        else:
            await interaction.response.send_message("Team not found.")
    else:
        await interaction.response.send_message("You do not have permission to close a team.")

@client.event
async def on_raw_reaction_add(payload):
    message_id = payload.message_id
    user_id = payload.user_id

    for team_id, team in teams.items():
        if message_id == team["message_id"]:
            emoji = payload.emoji.name

            if user_id != client.user.id and emoji == team["emoji"]:
                team_leader_id = team["leader_id"]
                channel = client.get_channel(payload.channel_id)

                # Skip updating members list if team is resetting
                if team.get("resetting", False):
                    return

                if user_id != team_leader_id:
                    if user_id not in team["members"]:  # Only add if not already in the team
                        team["reaction_count"] += 1

                        # Check if team is full and not locked yet
                        if len(team["members"]) < team["max_members"]:
                            team["members"].append(user_id)  # Add member to the list
                            print(f"Added user {user_id} to team {team_leader_id}")
                        else:
                            # If team is full, apply cooldown
                            if team_leader_id not in full_team_cooldowns or time.time() - full_team_cooldowns[team_leader_id] > cooldown_period:
                                await channel.send(f"The team of {client.get_user(team_leader_id).mention} :{team['emoji']}: is full - Considering joining another team! {client.get_user(user_id).mention}")
                                full_team_cooldowns[team_leader_id] = time.time()
                            return  # Do not add user if team is full

                        # Update the team message
                        member_mentions = [
                            client.get_user(member_id).mention for member_id in team["members"] if member_id != team_leader_id
                        ]
                        member_names_str = "\n".join(member_mentions)
                        updated_message = f"__**Group Leader**__\n{client.get_user(team_leader_id).mention} :{team['emoji']}:\n\n__**Members**__\n{member_names_str}"

                        # Add update to queue
                        update_queue.append((message_id, updated_message))

                        # Lock the team if it's full
                        if len(team["members"]) == team["max_members"]:
                            team["locked"] = True
                            await channel.send(f"{client.get_user(team_leader_id).mention} group is now locked!")

                    else:
                        # User is already in the team
                        team["reaction_count"] -= 1

                        # Update the team message if a user leaves
                        member_mentions = [
                            client.get_user(member_id).mention for member_id in team["members"] if member_id != team_leader_id
                        ]
                        member_names_str = "\n".join(member_mentions)
                        updated_message = f"__**Group Leader**__\n{client.get_user(team_leader_id).mention} :{team['emoji']}:\n\n__**Members**__\n{member_names_str}"

                        # Add update to queue
                        update_queue.append((message_id, updated_message))

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
                team["members"].remove(user_id)  # Remove member from the list
                print(f"Removed user {user_id} from team {team_id}")

                # Update the message
                member_mentions = [
                    client.get_user(member_id).mention for member_id in team["members"] if member_id != team["leader_id"]
                ]
                member_names_str = "\n".join(member_mentions)
                updated_message = f"__**Group Leader**__\n{client.get_user(team['leader_id']).mention} :{team['emoji']}:\n\n__**Members**__\n{member_names_str}"

                # Add update to queue
                update_queue.append((message_id, updated_message))
            
@tasks.loop(seconds=2.0)  # Adjust the interval as needed
async def process_update_queue():
    if update_queue:
        for _ in range(min(len(update_queue), 5)):  # Process max 5 messages per loop
            message_id, updated_message = update_queue.pop(0)
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
                print(f"Updated message {message_id}")
            except Exception as e:
                print(f"Failed to update message {message_id}: {e}")

client.run(os.getenv("DISCORD_TOKEN"))  