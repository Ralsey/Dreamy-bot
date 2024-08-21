import discord as disc
from discord.ext import commands 
import re
import yt_dlp

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


# Function to get the video URLs from a playlist
def get_video_urls_from_playlist(playlist_url):
    ydl_opts: dict[str, bool] = {
        'extract_flat': True,  # Only extract the URL, no downloads
        'quiet': True  # Suppress output
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(playlist_url, download=False)
            video_urls = [entry['url'] for entry in info_dict['entries']]
            playlist_title = info_dict['title']
            return video_urls, playlist_title
        except Exception as e:
            print(f"Error: {e}")
            return []


# Main function
def get_video_urls(url: str) -> list:
    playlist_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+'
    radio_pattern = r"^https?:\/\/(www\.)?youtube\.com\/.*[?&]list=(RD|RDEM)[^&]+.*"
    video_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'

    if re.match(playlist_pattern, url):
        video_urls, playlist_title = get_video_urls_from_playlist(url)
        if not video_urls:
            print("[error] No videos found or failed to fetch URLs.")
            return []
        return video_urls

    elif re.match(radio_pattern, url):
        print("[warning] The provided URL is a radio URL and cannot be processed.")
        return "radio"

    elif re.match(video_pattern, url):
        return [url]

    else:
        print("[warning] The provided URL is not a valid YouTube playlist or video URL.")
        return []