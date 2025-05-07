import os
import time
import sqlite3
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError
import asyncio

load_dotenv()

# Configuration
INTERVAL = 1800  # 30 minutes
TARGET_USERS = [u.strip() for u in os.getenv('TARGET_USERS', '').split(',') if u.strip()] # Add target accounts
PATH_PREFIX = os.getenv("PATH_PREFIX", '') # Path prefix

async def main():
    # Initialize DB
    conn = sqlite3.connect('stories.db')
    print("Database connected", conn)

    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            story_id TEXT PRIMARY KEY,
            user_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Telegram setup
    bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
    channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
    
    # Instagram client setup
    cl = Client()
    try:
        cl.load_settings(PATH_PREFIX + 'session.json')
    except FileNotFoundError:
        cl.login(os.getenv('INSTAGRAM_USERNAME'), os.getenv('INSTAGRAM_PASSWORD'))
        cl.dump_settings(PATH_PREFIX + 'session.json')
    
    while True:
        try:
            for username in TARGET_USERS:
                try:
                    print(f"Fetching stories for {username}")
                    user = cl.user_info_by_username(username)
                    print(f"User: {user}")
                    stories = cl.user_stories(user.pk)
                    print(f"Found {len(stories)} stories")
                    
                    for story in stories:
                        cursor = conn.cursor()
                        cursor.execute('SELECT story_id FROM stories WHERE story_id = ?', (story.pk,))
                        
                        if not cursor.fetchone():
                            try:
                                print(f"Processing story: {story.pk}")
                                if story.media_type == 1:
                                    file_path = cl.photo_download(story.pk, PATH_PREFIX + "downloads")
                                    with open(file_path, 'rb') as f:
                                        await bot.send_photo(channel_id, photo=f, caption=f"New story from @{username}")
                                elif story.media_type == 2:
                                    file_path = cl.video_download(story.pk, PATH_PREFIX + "downloads")
                                    with open(file_path, 'rb') as f:
                                        await bot.send_video(channel_id, video=f, caption=f"New story from @{username}")
                                
                                cursor.execute('INSERT INTO stories (story_id, user_id) VALUES (?, ?)', (story.pk, user.pk))
                                conn.commit()
                                
                            except (TelegramError, ClientError) as e:
                                print(f"Error processing story: {e}")
                                continue

                except LoginRequired:
                    raise LoginRequired
                            
                except ClientError as e:
                    print(f"Error fetching stories for {username}: {e}")
                    continue
            
            await asyncio.sleep(INTERVAL)
            
        except LoginRequired:
            print("Session expired. Relogining...")
            cl = Client()
            cl.login(os.getenv('INSTAGRAM_USERNAME'), os.getenv('INSTAGRAM_PASSWORD'))
            cl.dump_settings(PATH_PREFIX + 'session.json')
            print("Re-login successful as ", cl.username)
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"Critical error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())  # Run async main function
