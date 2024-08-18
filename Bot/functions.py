import discord as disc
from discord.ext import commands 

# Function to send the response
async def send_message_to_user(client: commands.Bot, user_id: int, message: str) -> None:
    if not message:
        print("User message is empty.")
        return

    try:
        # Assuming get_response is defined in responses.py and returns a string
        user = client.get_user(user_id)
        await user.send(str(message))

    
    except Exception as e:
        print(f"\n[error][functions] An error occurred while trying to send an message: {e}\n")
