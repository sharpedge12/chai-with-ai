import asyncio
import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from src.services.config import config

class TelegramDeliveryService:
    """Service for delivering digests to Telegram groups or chats"""
    
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        if not self.token or self.token == "your_bot_token":
            self.logger.warning("Telegram bot token not configured")
        
        if not self.chat_id or self.chat_id == "your_chat_id":
            self.logger.warning("Telegram chat ID not configured")
    
    def is_configured(self) -> bool:
        """Check if Telegram delivery is properly configured"""
        return (
            config.TELEGRAM_ENABLED and
            self.token and self.token != "your_bot_token" and
            self.chat_id and self.chat_id != "your_chat_id"
        )
    
    def is_group_chat(self) -> bool:
        """Check if the configured chat ID is for a group"""
        try:
            # Group chat IDs are negative numbers
            chat_id_int = int(self.chat_id)
            return chat_id_int < 0
        except ValueError:
            return False
    
    async def _send_message_async(self, text: str) -> bool:
        """Send a message to Telegram asynchronously"""
        if not self.is_configured():
            self.logger.warning("Telegram delivery not configured, skipping")
            return False
        
        try:
            bot = Bot(token=self.token)
            
            # Use HTML formatting instead of Markdown for better compatibility
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def _send_audio_async(self, audio_path: str, caption: str = None) -> bool:
        """Send an audio file to Telegram asynchronously"""
        if not self.is_configured():
            self.logger.warning("Telegram delivery not configured, skipping")
            return False
        
        try:
            bot = Bot(token=self.token)
            
            # Check if file exists
            if not Path(audio_path).exists():
                self.logger.error(f"Audio file not found: {audio_path}")
                return False
            
            # Check file size (Telegram limit is 50MB for audio)
            file_size = Path(audio_path).stat().st_size
            if file_size > 50 * 1024 * 1024:  # 50MB
                self.logger.error(f"Audio file too large: {file_size} bytes")
                return False
            
            print(f"    📤 Uploading audio file ({file_size} bytes)...")
            
            with open(audio_path, 'rb') as audio_file:
                await bot.send_audio(
                    chat_id=self.chat_id,
                    audio=audio_file,
                    caption=caption,
                    parse_mode=ParseMode.HTML if caption else None,
                    title=f"AI Digest Audio Summary",
                    performer="AI Digest System"
                )
            
            print(f"    ✅ Audio file sent successfully")
            return True
            
        except TelegramError as e:
            self.logger.error(f"Failed to send audio to Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending audio: {e}")
            return False
    
    def send_message(self, text: str) -> bool:
        """Send a message to Telegram (synchronous wrapper)"""
        return asyncio.run(self._send_message_async(text))
    
    def send_audio(self, audio_path: str, caption: str = None) -> bool:
        """Send an audio file to Telegram (synchronous wrapper)"""
        return asyncio.run(self._send_audio_async(audio_path, caption))
    
    async def _send_digest_async(self, digest: Dict[str, Any]) -> bool:
        """Send enhanced digest to Telegram with quote styling"""
        if not self.is_configured():
            self.logger.warning("Telegram delivery not configured, skipping")
            return False
        
        try:
            title = digest.get('summary', 'AI Digest').strip('"')  # Remove quotes for display
            count = digest.get('count', 0)
            
            if count == 0:
                message = f"<b>{title}</b>\n\nNo items found for this digest."
                return await self._send_message_async(message)
            
            # Send header with audio info
            header = f"<b>{title}</b>\n\n"
            header += f"Generated: {digest.get('generated_at', '')}\n"
            header += f"Items: {count}\n"
            
            # Add audio summary notification
            if digest.get('audio_summary_path'):
                header += f"🔊 Audio summary will be sent separately\n"
            
            # Add quality metrics
            items = digest.get('items', [])
            if items:
                scores = [item.get('score', 0) for item in items]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    high_quality = len([s for s in scores if s >= 0.7])
                    header += f"Average Score: {avg_score:.2f}\n"
                    header += f"High Quality Items: {high_quality}/{len(scores)}\n\n"
            
            await self._send_message_async(header)
            
            # Send audio summary first if available
            audio_path = digest.get('audio_summary_path')
            if audio_path:
                print(f"  🔊 Sending audio summary...")
                audio_caption = f"🎧 <b>Audio Summary</b>\n{title}\n\nDuration: ~2-3 minutes"
                audio_success = await self._send_audio_async(audio_path, audio_caption)
                if audio_success:
                    print(f"    ✅ Audio summary sent to Telegram")
                else:
                    print(f"    ❌ Failed to send audio summary")
            
            # Process items to avoid duplication - create unique items list
            unique_items = {}
            for item in items:
                item_id = item.get('url', item.get('title', ''))  # Use URL or title as unique identifier
                if item_id not in unique_items:
                    unique_items[item_id] = item
            
            # Send all items in order without tag grouping
            item_counter = 1
            for item in unique_items.values():
                await self._send_item_message(item, item_counter)
                item_counter += 1
                await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending digest to Telegram: {e}")
            return False

    async def _send_item_message(self, item: Dict[str, Any], counter: int):
        """Send individual item message with quote styling"""
        title = item.get('title', 'No Title')
        url = item.get('url', '')
        star_rating = item.get('star_rating', '⭐')
        source = item.get('source', 'unknown')
        
        safe_title = self._escape_html(title)
        message = f"<b>{counter}. <a href='{url}'>{safe_title}</a></b>\n\n"
        message += f"Rating: {star_rating} | Source: {source}"
        
        # Show tags without emojis
        tags = item.get('tags', [])
        if tags:
            message += f" | Tags: {', '.join(tags)}"
        
        # Add engagement metrics
        engagement_parts = []
        if item.get('like_count') is not None:
            engagement_parts.append(f"👍 {item['like_count']}")
        if item.get('dislike_count') is not None:
            engagement_parts.append(f"👎 {item['dislike_count']}")
        if item.get('comment_count') is not None:
            engagement_parts.append(f"💬 {item['comment_count']}")
        
        if engagement_parts:
            message += f"\nMetrics: {' | '.join(engagement_parts)}"
        
        message += "\n\n"
        
        # Add description with quote styling (remove quotes and add quote formatting)
        description = item.get('description', '').strip('"')
        if description and len(description) > 0:
            if len(description) > 300:
                description = description[:297] + "..."
            safe_description = self._escape_html(description)
            # Use blockquote formatting for Telegram
            message += f"<blockquote>{safe_description}</blockquote>\n\n"
        
        # Add why it matters with quote styling (remove quotes and add quote formatting)
        why_it_matters = item.get('why_it_matters', '').strip('"')
        if why_it_matters:
            if len(why_it_matters) > 150:
                why_it_matters = why_it_matters[:147] + "..."
            safe_why = self._escape_html(why_it_matters)
            message += f"<b>Why it matters:</b>\n<blockquote><i>{safe_why}</i></blockquote>"
        
        await self._send_message_async(message)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        
        # Replace HTML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text
    
    def send_digest(self, digest: Dict[str, Any]) -> bool:
        """Send a digest to Telegram (synchronous wrapper)"""
        return asyncio.run(self._send_digest_async(digest))

# Global telegram delivery service
telegram_delivery = TelegramDeliveryService()