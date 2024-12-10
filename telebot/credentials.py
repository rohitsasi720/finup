import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Get environment variables
bot_token = os.environ.get('BOT_TOKEN')
bot_user_name = os.environ.get('BOT_USERNAME')
URL = os.environ.get('URL')

# Validate environment variables
if not all([bot_token, bot_user_name, URL]):
    raise ValueError("Missing required environment variables. Please check your .env file or environment settings.")
