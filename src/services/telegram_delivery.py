import asyncio
import logging
import re
from typing import Dict, Any, Optional
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from src.services.config import config

class TelegramDeliveryService:
    """Service for delivering digests to
 Telegram groups or chats"""
    
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
    
    def send_message(self, text: str) -> bool:
        """Send a message to Telegram (synchronous wrapper)"""
        return asyncio.run(self._send_message_async(text))
    
    async def _send_digest_async(self, digest: Dict[str, Any]) -> bool:
        """Send a digest to Telegram asynchronously"""
        if not self.is_configured():
            self.logger.warning("Telegram delivery not configured, skipping")
            return False
        
        try:
            # Create a Telegram-friendly version of the digest
            title = digest.get('summary', 'AI Digest')
            count = digest.get('count', 0)
            
            if count == 0:
                message = f"<b>{title}</b>\n\nNo items found for this digest."
                return await self._send_message_async(message)
            
            # Send header message
            header = f"<b>{title}</b>\n\n"
            header += f"Generated: {digest.get('generated_at', '')}\n"
            header += f"Items: {count}\n\n"
            
            # Add quality metrics if available
            items = digest.get('items', [])
            if items:
                scores = [item.get('score', 0) for item in items]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    high_quality = len([s for s in scores if s >= 0.7])
                    header += f"Average Score: {avg_score:.2f}\n"
                    header += f"High Quality Items: {high_quality}/{len(scores)}\n\n"
            
            await self._send_message_async(header)
            
            # For groups, send a single consolidated message instead of multiple messages
            # if self.is_group_chat() and len(items) > 3:
            #     return await self._send_digest_consolidated(digest)
            
            # Send each item as a separate message for better readability
            for i, item in enumerate(items, 1):
                title = item.get('title', 'No Title')
                url = item.get('url', '')
                score = item.get('score', 0)
                source = item.get('source', 'unknown')
                
                # Create item message with HTML formatting
                safe_title = self._escape_html(title)
                message = f"<b>{i}. <a href='{url}'>{safe_title}</a></b>\n\n"
                message += f"Score: {score:.2f} | Source: {source}\n\n"
                
                # Add description if available
                description = item.get('description', '')
                if description and len(description) > 0:
                    # Truncate description for Telegram
                    if len(description) > 300:
                        description = description[:297] + "..."
                    # Escape HTML characters
                    safe_description = self._escape_html(description)
                    message += f"{safe_description}\n\n"
                
                # Add reasoning
                reasoning = item.get('reasoning', '')
                if reasoning:
                    if len(reasoning) > 150:
                        reasoning = reasoning[:147] + "..."
                    safe_reasoning = self._escape_html(reasoning)
                    message += f"<i>Why it matters: {safe_reasoning}</i>"
                
                # Send this item
                await self._send_message_async(message)
                
                # Add small delay between messages to avoid rate limiting
                await asyncio.sleep(0.5)
            
            return True
            
        except TelegramError as e:
            self.logger.error(f"Failed to send digest to Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error sending digest to Telegram: {e}")
            return False
    
    # async def _send_digest_consolidated(self, digest: Dict[str, Any]) -> bool:
    #     """Send digest as a single consolidated message (better for groups)"""
    #     items = digest.get('items', [])
        
    #     # Create a consolidated message with just titles and links
    #     message = f"<b>{digest.get('summary', 'AI Digest')}</b>\n\n"
        
    #     for i, item in enumerate(items, 1):
    #         title = self._escape_html(item.get('title', 'No Title'))
    #         url = item.get('url', '')
    #         score = item.get('score', 0)
            
    #         message += f"{i}. <a href='{url}'>{title}</a> ({score:.2f})\n"
        
    #     # Send the consolidated message
    #     return await self._send_message_async(message)
    
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