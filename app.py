import re
from flask import Flask, request, jsonify
import telegram
from telebot.credentials import bot_token, bot_user_name, URL
import os
import logging
import sys
import json
import asyncio
from telegram.error import TelegramError
from bse_scraper import get_bse_screenshot
import httpx
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Bot is starting up...")
logger.info("Environment variables:")
logger.info(f"URL: {os.environ.get('URL')}")
logger.info(f"BOT_USERNAME: {os.environ.get('BOT_USERNAME')}")
logger.info(f"BOT_TOKEN exists: {bool(os.environ.get('BOT_TOKEN'))}")

global bot
global TOKEN
TOKEN = bot_token

# Initialize bot with default settings
bot = telegram.Bot(token=TOKEN)
logger.debug("Token being used: %s", TOKEN[:4] + '...')

# Create a custom HTTP client for the bot
@asynccontextmanager
async def get_http_client():
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        yield client

app = Flask(__name__)

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('Path: %s', request.path)

async def verify_webhook():
    try:
        async with get_http_client() as client:
            webhook_info = await bot.get_webhook_info()
            logger.info("Current webhook info: %s", webhook_info)
            
            webhook_url = os.environ.get('URL', '').rstrip('/') + '/' + TOKEN
            
            if not webhook_info.url:
                logger.warning("No webhook URL set. Setting now...")
                await bot.delete_webhook()
                success = await bot.set_webhook(webhook_url)
                if success:
                    logger.info("Webhook set successfully to: %s", webhook_url)
                else:
                    logger.error("Failed to set webhook")
            elif webhook_info.url != webhook_url:
                logger.warning("Webhook URL mismatch. Expected: %s, Got: %s", webhook_url, webhook_info.url)
                logger.info("Updating webhook URL...")
                await bot.delete_webhook()
                success = await bot.set_webhook(webhook_url)
                if success:
                    logger.info("Webhook updated successfully to: %s", webhook_url)
                else:
                    logger.error("Failed to update webhook")
            else:
                logger.info("Webhook URL is correctly set to: %s", webhook_info.url)
                
    except Exception as e:
        logger.error("Error verifying webhook: %s", str(e), exc_info=True)
        raise

async def send_telegram_message(chat_id, text, reply_to_message_id=None):
    try:
        logger.info("Attempting to send message to chat_id %s: %s", chat_id, text)
        async with get_http_client() as client:
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id
            )
            logger.info("Message sent successfully: %s", message)
            return message
    except TelegramError as e:
        logger.error("Telegram error sending message: %s", str(e), exc_info=True)
        raise
    except Exception as e:
        logger.error("Error sending message: %s", str(e), exc_info=True)
        raise

async def send_telegram_photo(chat_id, photo_path, caption=None, reply_to_message_id=None):
    try:
        logger.info("Attempting to send photo to chat_id %s: %s", chat_id, photo_path)
        async with get_http_client() as client:
            with open(photo_path, 'rb') as photo:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    reply_to_message_id=reply_to_message_id
                )
            logger.info("Photo sent successfully")
            return message
    except Exception as e:
        logger.error("Error sending photo: %s", str(e), exc_info=True)
        raise

@app.route('/{}'.format(TOKEN), methods=['POST'])
async def respond():
    try:
        logger.info("Received webhook request")
        # Log the raw request
        logger.debug("Raw request headers: %s", dict(request.headers))
        request_json = request.get_json(force=True)
        logger.debug("Received request data: %s", json.dumps(request_json, indent=2))

        # Verify webhook on each request
        await verify_webhook()

        # retrieve the message in JSON and then transform it to Telegram object
        update = telegram.Update.de_json(request_json, bot)
        logger.info("Processed update: %s", update)

        if not update or not update.message:
            logger.error("Invalid update received: %s", update)
            return jsonify({'error': 'Invalid update'})

        chat_id = update.message.chat.id
        msg_id = update.message.message_id

        # Log chat details
        logger.info("Chat ID: %s, Message ID: %s", chat_id, msg_id)

        if not update.message.text:
            logger.error("No text in message: %s", update.message)
            return jsonify({'error': 'No text in message'})

        text = update.message.text.encode('utf-8').decode()
        logger.info("Received message: %s from chat_id: %s", text, chat_id)
        
        if text == "/start":
            logger.info("Received /start command from chat_id: %s", chat_id)
            welcome_text = """
            Welcome! I'm your BSE bot. Available commands:
            /start - Show this help message
            /bse - Get BSE screenshot
            """
            try:
                await send_telegram_message(chat_id, welcome_text, msg_id)
                logger.info("Start message sent successfully")
                return jsonify({'status': 'ok', 'message': 'Welcome message sent'})
            except Exception as e:
                logger.error("Failed to send welcome message: %s", str(e))
                return jsonify({'error': str(e)})
        
        elif text == "/bse":
            try:
                # Send a processing message
                await send_telegram_message(chat_id, "Processing BSE request... Please wait.", msg_id)
                
                # Get the screenshot
                screenshot_path = await get_bse_screenshot()
                
                # Send the screenshot
                await send_telegram_photo(
                    chat_id, 
                    screenshot_path, 
                    caption="BSE Screenshot", 
                    reply_to_message_id=msg_id
                )
                
                # Clean up the screenshot file
                os.remove(screenshot_path)
                
                return jsonify({'status': 'ok', 'message': 'BSE screenshot sent'})
            except Exception as e:
                error_message = f"Failed to get BSE screenshot: {str(e)}"
                logger.error(error_message)
                await send_telegram_message(chat_id, error_message, msg_id)
                return jsonify({'error': error_message})
        
        else:
            logger.info("Processing non-command message: %s", text)
            response_text = "Please use one of the available commands:\n/start - Show help\n/bse - Get BSE screenshot"
            try:
                await send_telegram_message(chat_id, response_text, msg_id)
                logger.info("Response message sent successfully")
                return jsonify({'status': 'ok', 'message': 'Response sent'})
            except Exception as e:
                logger.error("Failed to send response message: %s", str(e))
                return jsonify({'error': str(e)})

    except Exception as e:
        logger.error("Error in respond function: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)})

@app.route('/set_webhook', methods=['GET', 'POST'])
async def set_webhook():
    try:
        # Get the webhook URL from environment
        webhook_url = os.environ.get('URL', 'http://localhost:5000')
        webhook_url = webhook_url.rstrip('/') + '/' + TOKEN
        
        logger.info("Setting webhook to URL: %s", webhook_url)
        
        # First, delete any existing webhook
        await bot.delete_webhook()
        logger.info("Deleted existing webhook")
        
        # Set the new webhook
        success = await bot.set_webhook(webhook_url)
        
        # Get webhook info
        webhook_info = await bot.get_webhook_info()
        logger.info("Webhook info: %s", webhook_info)
        
        if success:
            logger.info("Webhook setup successful")
            return jsonify({
                'status': 'ok',
                'webhook_url': webhook_url,
                'webhook_info': str(webhook_info)
            })
        else:
            logger.error("Webhook setup failed")
            return jsonify({
                'status': 'error',
                'message': 'Webhook setup failed',
                'webhook_info': str(webhook_info)
            })
    except Exception as e:
        logger.error("Error setting webhook: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/')
async def index():
    try:
        # Verify webhook
        await verify_webhook()
        
        bot_info = await bot.get_me()
        webhook_info = await bot.get_webhook_info()
        
        return jsonify({
            'status': 'Bot is running',
            'bot_info': str(bot_info),
            'webhook_info': str(webhook_info),
            'environment_url': os.environ.get('URL', 'Not set')
        })
    except Exception as e:
        logger.error("Error in index route: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)