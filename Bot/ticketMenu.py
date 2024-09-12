# discord imports
import discord
from discord.ext import commands
from discord.ui import View, Select

# python imports
import time

# local imports
from functions import send_message_to_user, create_connection, save_ticket_to_db, load_ticket_from_db, close_connection, load_ids, delete_ticket_from_db, save_transcript

ids: dict[int, dict[str, int]] = load_ids()

class PersistentTicketView(discord.ui.View):
    def __init__(self, client: commands.Bot):
        super().__init__(timeout=None)  
        self.add_item(discord.ui.Button(label="📬 Create a Ticket", style=discord.ButtonStyle.green, custom_id="ticket_menu"))
        self.children[-1].callback = self.ticket_callback
        self.client = client

    async def ticket_callback(self, interaction: discord.Interaction) -> None:
        select = Select(options=[
            discord.SelectOption(label="Inappropriate Behavior", value="01", emoji="🚫", description="Report someone who is behaving inappropriately"),
            discord.SelectOption(label="Discord Server Issue", value="02", emoji="🛠️", description="Report a discord server issue or bug"),
            discord.SelectOption(label="Bot Issue", value="03", emoji="🤖", description="Report an issue with the Dreamy Assistant bot"),
            discord.SelectOption(label="Other Issue or Subject", value="04", emoji="❓", description="For any and all other issues or questions")
        ])
        select.callback = self.select_callback
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Select the type of ticket you would like to create.", view=view, ephemeral=True, delete_after=60)
    
    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        support_category = discord.utils.get(interaction.guild.categories, id=ids[interaction.guild.id]["support_category_id"])
        if not support_category:
            print("[error][tickets] Support category not found. Please provide a valid category ID.")
            await interaction.followup.send("```fix\nSupport category not found. Please provide a valid category ID.```", ephemeral=True)
            return
        
        sky_guardians_role = interaction.guild.get_role(ids[interaction.guild.id]["sky_guardians_role_id"])
        if not sky_guardians_role:
            print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
            await interaction.followup.send("```fix\nSky Guardians role not found. Please provide a valid role ID.```", ephemeral=True)
            return
        
        tech_oracle_role = interaction.guild.get_role(ids[interaction.guild.id]["tech_oracle_role_id"])
        if not tech_oracle_role:
            print("[error][tickets] Tech Oracle role not found. Please provide a valid role ID.")
            await interaction.followup.send("```fix\nTech Oracle role not found. Please provide a valid role ID.```", ephemeral=True)
            return

        owner = await self.client.fetch_user(ids[interaction.guild.id]["owner_id"]) 
        if not owner:
            print("[error][tickets] owner user not found. Please provide a valid user ID.")
            await interaction.followup.send("```fix\nowner was not found. Please provide a valid user ID.```", ephemeral=True)
            return
        
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
            
            print(f"[tickets][inappropriate] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket for Inappropriate Behavior has been created!", ephemeral=True)
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(self.client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            await ticket_channel.send("# Inappropriate Behavior\nAfter you are done, you can close this ticket via the button below!", view=PersistentCloseTicketView(self.client))
            
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
            
            print(f"[tickets][inappropriate] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket for Inappropriate Behavior has been created!", ephemeral=True)
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(self.client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            await ticket_channel.send("# Server Issue\nAfter you are done, you can close this ticket via the button below!", view=PersistentCloseTicketView(self.client))

            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{sky_guardians_role.mention}, {interaction.user.mention} wants to report a server issue.\nPlease wait until a Sky Guardian is on the case <3\nIn the meantime, please provide as much detail as possible about the issue")

            await owner.send(f"A user report ticket has been created by {interaction.user.mention}: {ticket_url}")
            
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
            
            print(f"[tickets][inappropriate] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket for Inappropriate Behavior has been created!", ephemeral=True)
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(self.client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            await ticket_channel.send("# Bot Issue\nAfter you are done, you can close this ticket via the button below!", view=PersistentCloseTicketView(self.client))
            
            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{tech_oracle_role.mention}, {interaction.user.mention} wants to report a issue with the bot.\nPlease wait until an Tech Oracle is on the case <3\nIn the meantime, please provide as much detail as possible about the issue with the bot")

            await owner.send(f"A user report ticket has been created by {interaction.user.mention}: {ticket_url}")
            
        elif interaction.data["values"][0] == "04": # Other Issue or Subject
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True),
                sky_guardians_role: discord.PermissionOverwrite(read_messages=True),
                tech_oracle_role: discord.PermissionOverwrite(read_messages=True, manage_messages=True, manage_channels=True)
            }
            ticket_name = f"Other Issue - {interaction.user.display_name}'s - {str(time.time_ns())[-6:]}"
            ticket_channel = await interaction.guild.create_text_channel(name=ticket_name, category=support_category, overwrites=overwrites)
            
            print(f"[tickets][inappropriate] Ticket created for user {interaction.user.name} in channel {ticket_channel.name}")
            
            await interaction.followup.send("A ticket for Inappropriate Behavior has been created!", ephemeral=True)
            
            ticket_url = f"https://discord.com/channels/{interaction.guild.id}/{ticket_channel.id}"
            await send_message_to_user(self.client, interaction.user.id, f"Your ticket has been created: {ticket_url}")
            
            await ticket_channel.send("# Other Issue\nAfter you are done, you can close this ticket via the button below!", view=PersistentCloseTicketView(self.client))
            
            # Notify user and ping Sky Guardians role
            await ticket_channel.send(f"\n{sky_guardians_role.mention}, {interaction.user.mention} has an general issue or question.\nPlease wait until a Sky Guardian is on the case <3\nIn the meantime, please provide the context of the issue or question")
            
            await owner.send(f"A user report ticket has been created by {interaction.user.mention}: {ticket_url}")
            
        else: # Invalid selection
            await interaction.followup.send("Invalid selection", ephemeral=True)
            return # Exit the function
        connection = create_connection("Tickets")
        save_ticket_to_db(connection, interaction.user.id, ticket_channel.id)
        close_connection(connection)

class PersistentCloseTicketView(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)  
        self.add_item(discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close_menu"))
        self.children[-1].callback = self.close_callback
        self.client = client

    async def close_callback(self, interaction: discord.Interaction) -> None:
        sky_guardians_role = interaction.guild.get_role(ids[interaction.guild.id]["sky_guardians_role_id"])
        if not sky_guardians_role:
            print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
            await interaction.response.send_message("```fix\nSky Guardians role not found. Please provide a valid role ID.```", ephemeral=True)
            return
        
        tech_oracle_role = interaction.guild.get_role(ids[interaction.guild.id]["tech_oracle_role_id"])
        if not tech_oracle_role:
            print("[error][tickets] Tech Oracle role not found. Please provide a valid role ID.")
            await interaction.response.send_message("```fix\nTech Oracle role not found. Please provide a valid role ID.```", ephemeral=True)
            return
        
        connection = create_connection("Tickets")
        user_id = load_ticket_from_db(connection, interaction.channel.id)
        if not user_id:
            await interaction.response.send_message("No saved ticket found for this channel.", ephemeral=True)
            return
        
        select = Select(options=[
            discord.SelectOption(label="Yes, close this ticket", value="01", emoji="☑️", description="This closes the ticket and will mark it as solved"),
            discord.SelectOption(label="No, keep this ticket open", value="02", emoji="✖️", description="This will keep the ticket open and allow you to continue the conversation"),
        ])
        
        select.callback = self.select_callback
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Do you really want to close the ticket?", view=view, ephemeral=True, delete_after=60)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        sky_guardians_role = interaction.guild.get_role(ids[interaction.guild.id]["sky_guardians_role_id"])
        if not sky_guardians_role:
            print("[error][tickets] Sky Guardians role not found. Please provide a valid role ID.")
            await interaction.followup.send("```fix\nSky Guardians role not found. Please provide a valid role ID.```", ephemeral=True)
            return
        
        tech_oracle_role = interaction.guild.get_role(ids[interaction.guild.id]["tech_oracle_role_id"])
        if not tech_oracle_role:
            print("[error][tickets] Tech Oracle role not found. Please provide a valid role ID.")
            await interaction.followup.send("```fix\nTech Oracle role not found. Please provide a valid role ID.```", ephemeral=True)
            return
        
        if interaction.data["values"][0] == "01": # Yes, close this ticket
            if interaction.user.id != ids[interaction.guild.id]["owner_id"] or sky_guardians_role in interaction.user.roles or tech_oracle_role in interaction.user.roles:
                await interaction.followup.send("Ticket will be closed.", ephemeral=True)
                user_id = load_ticket_from_db(connection, interaction.channel.id)
                if not user_id:
                    await interaction.followup.send("No saved ticket found for this channel.", ephemeral=True)
                    return
                user = await self.client.fetch_user(user_id)
                if not user:
                    print("[error][tickets] The user that created this ticket is not found!")
                    await interaction.followup.send("```fix\nThe user that created this ticket is not found!```", ephemeral=True)
                    user = interaction.user
                
                ticket_logs = ""
                path = await save_transcript(interaction.channel, ticket_logs)

                ticket_logs_channel = self.client.get_channel(ids[interaction.guild.id]["ticket_log_channel_id"])
                if ticket_logs_channel:
                    await ticket_logs_channel.send(f"Transcript for {interaction.channel.name}:", file=discord.File(path))
                else:
                    print("[warning][tickets] Ticket logs channel not found. Please provide a valid channel name.")
                print(f"[tickets] Ticket closed by user {interaction.user.name} in channel {interaction.channel.name}")
                
                await interaction.channel.delete()
                connection = create_connection("Tickets")
                delete_ticket_from_db(connection, interaction.channel.id)
                close_connection(connection)
                await send_message_to_user(self.client, user_id, "Your ticket has been closed successfully. The Transcript of the ticket has been saved.")
                await user.send(f"Transcript for {interaction.channel.name}:", file=discord.File(path))
            else:
                print(f"[warning][tickets] {interaction.user.name} does not have prems to close ticket {interaction.channel.name}")
                await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)

        elif interaction.data["values"][0] == "02": # No, keep this ticket open
            await interaction.followup.send("Ticket will remain open.", ephemeral=True)
        
        else: # Invalid selection
            await interaction.followup.send("Invalid selection", ephemeral=True)