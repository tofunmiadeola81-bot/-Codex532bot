import os
import io
import logging
import requests
from datetime import datetime
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import validators
import pyshorteners

# === LOGGING SETUP ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found! Please set it in Railway environment variables.")

# === IMAGE GENERATION API (FREE - uses Pollinations.ai) ===
def generate_image(prompt: str) -> str:
    """Generate an image using the free Pollinations.ai API"""
    try:
        encoded_prompt = requests.utils.quote(prompt)
        # Pollinations generates images on the fly
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true"
        return image_url
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return None

# === IMAGE CONVERSION ===
def convert_image(image_bytes: bytes, target_format: str) -> bytes:
    """Convert image to specified format (jpg, png, webp, etc.)"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        output = io.BytesIO()
        
        # Handle RGBA -> RGB for JPEG
        if target_format.lower() in ['jpeg', 'jpg']:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            target_format = 'JPEG'
            img.save(output, format=target_format, quality=95)
        elif target_format.lower() == 'png':
            target_format = 'PNG'
            img.save(output, format=target_format, optimize=True)
        elif target_format.lower() == 'webp':
            target_format = 'WEBP'
            img.save(output, format=target_format, quality=90)
        else:
            target_format = target_format.upper()
            img.save(output, format=target_format)
        
        return output.getvalue()
    except Exception as e:
        raise Exception(f"Conversion failed: {str(e)}")

# === URL SHORTENER ===
def shorten_url(long_url: str) -> str:
    """Shorten URL using multiple free services (fallback)"""
    try:
        # Try TinyURL first (free, no API key needed)
        s = pyshorteners.Shortener()
        return s.tinyurl.short(long_url)
    except Exception as e1:
        logger.warning(f"TinyURL failed: {e1}")
        try:
            # Fallback to is.gd
            response = requests.get(
                f"https://is.gd/create.php?format=simple&url={long_url}",
                timeout=10
            )
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e2:
            logger.warning(f"is.gd failed: {e2}")
            try:
                # Second fallback to v.gd
                response = requests.get(
                    f"https://v.gd/create.php?format=simple&url={long_url}",
                    timeout=10
                )
                if response.status_code == 200:
                    return response.text.strip()
            except Exception as e3:
                logger.warning(f"v.gd failed: {e3}")
        
        return f"⚠️ Error: Could not shorten URL. Please try again."

# === KEYBOARD / MENU ===
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📸 Image Converter", callback_data="convert")],
        [InlineKeyboardButton("🎨 Image Generator", callback_data="generate")],
        [InlineKeyboardButton("🔗 URL Shortener", callback_data="shorten")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

# === COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message with the main menu"""
    user = update.effective_user
    welcome_text = (
        f"🤖 *Welcome to Codex532 Bot!*\n\n"
        f"Hello {user.first_name}! I'm your all-in-one utility bot.\n\n"
        "I can help you with:\n"
        "📸 *Image Converter* - Convert images to JPG, PNG, WEBP\n"
        "🎨 *Image Generator* - Create images from text prompts\n"
        "🔗 *URL Shortener* - Shorten long URLs instantly\n\n"
        "Choose an option below:"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help information"""
    help_text = (
        "ℹ️ *How to use Codex532 Bot*\n\n"
        "📸 *Image Converter*\n"
        "• Send any image\n"
        "• Reply with format: `jpg`, `png`, or `webp`\n"
        "• Get your converted image instantly!\n\n"
        "🎨 *Image Generator*\n"
        "• Send a text description\n"
        "• Example: `A cat wearing a hat`\n"
        "• Get an AI-generated image!\n\n"
        "🔗 *URL Shortener*\n"
        "• Send any URL\n"
        "• Get a short link instantly!\n\n"
        "Use the main menu to switch between functions.\n\n"
        "📊 *Stats*\n"
        "• See your usage statistics\n\n"
        "Made with ❤️ using Python & Railway"
    )
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
        ])
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user = update.effective_user
    # You can expand this with actual database stats later
    stats_text = (
        f"📊 *Your Stats*\n\n"
        f"👤 User: {user.first_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 Joined: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"📈 Usage Statistics:\n"
        f"• Total commands: {context.user_data.get('total_commands', 0)}\n"
        f"• Images converted: {context.user_data.get('images_converted', 0)}\n"
        f"• Images generated: {context.user_data.get('images_generated', 0)}\n"
        f"• URLs shortened: {context.user_data.get('urls_shortened', 0)}\n\n"
        f"ℹ️ This is your personal usage tracker."
    )
    await update.message.reply_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
        ])
    )

# === CALLBACK HANDLER ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks from the menu"""
    query = update.callback_query
    await query.answer()
    
    # Increment command counter
    context.user_data['total_commands'] = context.user_data.get('total_commands', 0) + 1
    
    if query.data == "convert":
        await query.edit_message_text(
            "📸 *Image Converter*\n\n"
            "Send me an image, and I'll convert it to your preferred format.\n\n"
            "✅ Supported formats: `JPG`, `PNG`, `WEBP`\n"
            "📤 Just send an image and then tell me the format you want.\n\n"
            "💡 *Tip:* Higher quality images take slightly longer to process.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
            ])
        )
        context.user_data['mode'] = 'convert'
    
    elif query.data == "generate":
        await query.edit_message_text(
            "🎨 *Image Generator*\n\n"
            "Send me a text description, and I'll generate a unique image for you.\n\n"
            "📝 *Examples:*\n"
            "• `A beautiful sunset over mountains`\n"
            "• `A futuristic city at night`\n"
            "• `A cute puppy wearing a bow tie`\n\n"
            "💡 The more detailed your prompt, the better the result!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
            ])
        )
        context.user_data['mode'] = 'generate'
    
    elif query.data == "shorten":
        await query.edit_message_text(
            "🔗 *URL Shortener*\n\n"
            "Send me a long URL and I'll shorten it instantly.\n\n"
            "📋 *Example:*\n"
            "`https://www.example.com/very/long/url/with/many/parameters`\n\n"
            "✅ I support multiple shortening services for reliability.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
            ])
        )
        context.user_data['mode'] = 'shorten'
    
    elif query.data == "help":
        help_text = (
            "ℹ️ *How to use Codex532 Bot*\n\n"
            "1️⃣ *Image Converter*: Send an image, then reply with format (jpg/png/webp)\n"
            "2️⃣ *Image Generator*: Send a text prompt describing what you want\n"
            "3️⃣ *URL Shortener*: Send any URL and get a short link\n\n"
            "📱 Use the main menu to switch between functions.\n"
            "📊 Check your stats anytime with /stats.\n\n"
            "🔗 *Source Code:*\n"
            "https://github.com/yourusername/codex532-bot\n\n"
            "Made with ❤️ using Python & Railway"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
            ])
        )
    
    elif query.data == "stats":
        user = update.effective_user
        stats_text = (
            f"📊 *Your Stats*\n\n"
            f"👤 User: {user.first_name}\n"
            f"🆔 ID: `{user.id}`\n\n"
            f"📈 Usage:\n"
            f"• Total commands: {context.user_data.get('total_commands', 0)}\n"
            f"• Images converted: {context.user_data.get('images_converted', 0)}\n"
            f"• Images generated: {context.user_data.get('images_generated', 0)}\n"
            f"• URLs shortened: {context.user_data.get('urls_shortened', 0)}"
        )
        await query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
            ])
        )
    
    elif query.data == "menu":
        await query.edit_message_text(
            "🤖 *Welcome back to Codex532 Bot!*\n\n"
            "Choose an option below:",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
        context.user_data['mode'] = None

# === MESSAGE HANDLER ===
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages based on the current mode"""
    user = update.effective_user
    message = update.message
    mode = context.user_data.get('mode')
    
    # If no mode set, ask to choose from menu
    if not mode:
        await message.reply_text(
            "Please choose an option from the menu first!",
            reply_markup=get_main_menu()
        )
        return
    
    # === IMAGE CONVERSION ===
    if mode == 'convert':
        if message.photo:
            # Get the largest photo
            photo_file = await message.photo[-1].get_file()
            image_bytes = await photo_file.download_as_bytearray()
            
            # Store image in context for later
            context.user_data['image_bytes'] = image_bytes
            context.user_data['awaiting_format'] = True
            
            await message.reply_text(
                "✅ Image received!\n\n"
                "Now reply with the format you want:\n"
                "• `jpg` or `jpeg`\n"
                "• `png`\n"
                "• `webp`\n\n"
                "Example: `png`",
                parse_mode="Markdown"
            )
        elif message.document and message.document.mime_type and 'image' in message.document.mime_type:
            # Handle image as document
            doc_file = await message.document.get_file()
            image_bytes = await doc_file.download_as_bytearray()
            
            context.user_data['image_bytes'] = image_bytes
            context.user_data['awaiting_format'] = True
            
            await message.reply_text(
                "✅ Image received!\n\n"
                "Now reply with the format you want:\n"
                "• `jpg` or `jpeg`\n"
                "• `png`\n"
                "• `webp`\n\n"
                "Example: `png`",
                parse_mode="Markdown"
            )
        else:
            await message.reply_text(
                "❌ Please send an image (photo or document), not text or other files."
            )
    
    # === IMAGE GENERATION ===
    elif mode == 'generate':
        prompt = message.text
        if not prompt or len(prompt) < 2:
            await message.reply_text(
                "❌ Please provide a valid text description (at least 2 characters)."
            )
            return
        
        await message.reply_text("🎨 Generating your image... This may take a moment.")
        
        try:
            # Generate image URL
            image_url = generate_image(prompt)
            
            if not image_url:
                await message.reply_text(
                    "❌ Failed to generate image. Please try a different prompt."
                )
                return
            
            # Download the generated image
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                # Update stats
                context.user_data['images_generated'] = context.user_data.get('images_generated', 0) + 1
                
                await message.reply_photo(
                    photo=response.content,
                    caption=f"🎨 *Generated for: {prompt[:60]}...*\n\n"
                            f"📝 Prompt: `{prompt}`\n"
                            f"⚡ Powered by Pollinations.ai",
                    parse_mode="Markdown"
                )
            else:
                await message.reply_text(
                    "❌ Failed to generate image. Please try a different prompt."
                )
        except Exception as e:
            logger.error(f"Generation error: {e}")
            await message.reply_text(f"❌ Error generating image: {str(e)}")
    
    # === URL SHORTENER ===
    elif mode == 'shorten':
        url = message.text.strip()
        
        # Validate URL
        if not validators.url(url):
            await message.reply_text(
                "❌ That doesn't look like a valid URL.\n\n"
                "Make sure it starts with `http://` or `https://`",
                parse_mode="Markdown"
            )
            return
        
        await message.reply_text("🔗 Shortening your URL...")
        
        try:
            short_url = shorten_url(url)
            if short_url and "Error" not in short_url:
                # Update stats
                context.user_data['urls_shortened'] = context.user_data.get('urls_shortened', 0) + 1
                
                await message.reply_text(
                    f"✅ *URL shortened successfully!*\n\n"
                    f"🔗 Original: `{url[:80]}{'...' if len(url) > 80 else ''}`\n"
                    f"📎 Short URL: `{short_url}`",
                    parse_mode="Markdown"
                )
            else:
                await message.reply_text(
                    f"❌ {short_url if short_url else 'Could not shorten URL. Please try again.'}"
                )
        except Exception as e:
            logger.error(f"URL shortening error: {e}")
            await message.reply_text(f"❌ Error shortening URL: {str(e)}")

# === FORMAT RESPONSE HANDLER ===
async def handle_format_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the format selection after an image is received"""
    if not context.user_data.get('awaiting_format'):
        return
    
    format_input = update.message.text.strip().lower()
    valid_formats = ['jpg', 'jpeg', 'png', 'webp']
    
    if format_input not in valid_formats:
        await update.message.reply_text(
            f"❌ Invalid format. Please choose from: {', '.join(valid_formats)}"
        )
        return
    
    image_bytes = context.user_data.get('image_bytes')
    if not image_bytes:
        await update.message.reply_text("❌ Image not found. Please send the image again.")
        context.user_data['awaiting_format'] = False
        return
    
    await update.message.reply_text(f"🔄 Converting to {format_input.upper()}...")
    
    try:
        # Convert the image
        converted = convert_image(image_bytes, format_input)
        
        # Determine the correct mimetype for sending
        file_ext = 'jpg' if format_input in ['jpg', 'jpeg'] else format_input
        
        # Update stats
        context.user_data['images_converted'] = context.user_data.get('images_converted', 0) + 1
        
        await update.message.reply_document(
            document=io.BytesIO(converted),
            filename=f"converted.{file_ext}",
            caption=f"✅ Converted successfully!\n\n"
                    f"📁 Format: `{format_input.upper()}`\n"
                    f"📊 Size: {len(converted) // 1024} KB",
            parse_mode="Markdown"
        )
        
        # Reset state
        context.user_data['image_bytes'] = None
        context.user_data['awaiting_format'] = False
        
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        await update.message.reply_text(f"❌ Conversion failed: {str(e)}")
        context.user_data['awaiting_format'] = False

# === ERROR HANDLER ===
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify user"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or use /start to reset."
            )
    except:
        pass

# === MAIN ===
def main():
    """Start the bot"""
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")
    
    logger.info("🚀 Starting Codex532 Bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_messages))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_messages))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_format_response))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot (using long polling for Railway)
    logger.info("✅ Bot is running and ready!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
