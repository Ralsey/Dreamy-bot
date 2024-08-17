import discord as disc

# Function to send the response
async def send_message_to_user(interaction: disc.Interaction, message: str, private: bool) -> None:
    if not message:
        print("User message is empty.")
        return

    try:
        # Assuming get_response is defined in responses.py and returns a strin
        if private:
            await interaction.user.send(str(message))
            await interaction.response.send_message("Message sent to user.")
        else:
            await interaction.response.send_message(str(message))
    
    except Exception as e:
        print(f"\n[error] An error occurred while trying to send an message: {e}\n")
