import re
from flask import Flask, request, jsonify
import telegram
from telebot.credentials import bot_token, bot_user_name, URL
import os
import logging
import sys
import json
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log the environment variables (excluding sensitive data)
logger.debug("URL from environment: %s", os.environ.get('URL'))
logger.debug("Bot username from environment: %s", os.environ.get('BOT_USERNAME'))
logger.debug("Bot token exists: %s", bool(os.environ.get('BOT_TOKEN')))

global bot
global TOKEN
TOKEN = bot_token
logger.debug("Token being used: %s", TOKEN[:4] + '...')

# Initialize bot
bot = telegram.Bot(token=TOKEN)

app = Flask(__name__)

async def send_telegram_message(chat_id, text, reply_to_message_id=None):
    try:
        return await bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise

@app.route('/{}'.format(TOKEN), methods=['POST'])
async def respond():
    try:
        # Log the raw request
        logger.debug("Raw request headers: %s", dict(request.headers))
        request_json = request.get_json(force=True)
        logger.debug("Received request data: %s", json.dumps(request_json, indent=2))

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
            welcome_text = "Hello! I'm your bot. I'm working!"
            await send_telegram_message(chat_id, welcome_text, msg_id)
            return jsonify({'status': 'ok', 'message': 'Welcome message sent'})
        else:
            logger.info("Processing non-start message: %s", text)
            response_text = f"You said: {text}"
            await send_telegram_message(chat_id, response_text, msg_id)
            return jsonify({'status': 'ok', 'message': 'Response sent'})

    except Exception as e:
        logger.error("Error in respond function: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)})

@app.route('/set_webhook', methods=['GET', 'POST'])
async def set_webhook():
    try:
        webhook_url = os.environ.get('URL', 'http://localhost:5000')
        webhook_url = webhook_url.rstrip('/') + '/' + TOKEN
        
        logger.info("Setting webhook to URL: %s", webhook_url)
        
        # First, delete any existing webhook
        await bot.delete_webhook()
        logger.info("Deleted existing webhook")
        
        # Set the new webhook
        s = await bot.set_webhook(webhook_url)
        
        # Get webhook info
        webhook_info = await bot.get_webhook_info()
        logger.info("Webhook info: %s", webhook_info)
        
        if s:
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
        bot_info = await bot.get_me()
        webhook_info = await bot.get_webhook_info()
        return jsonify({
            'status': 'Bot is running',
            'bot_info': str(bot_info),
            'webhook_info': str(webhook_info)
        })
    except Exception as e:
        logger.error("Error in index route: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)