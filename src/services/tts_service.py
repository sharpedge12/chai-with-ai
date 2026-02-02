import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import pyttsx3
from gtts import gTTS
from src.services.config import config
from src.services.llm_client import llm

class TTSService:
    """Text-to-Speech service for digest audio summaries"""
    
    def __init__(self):
        self.output_dir = config.PROJECT_ROOT / "output" / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize pyttsx3 engine
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 0.9)  # Volume level
            self.use_pyttsx3 = True
        except:
            print("⚠️  pyttsx3 not available, will use gTTS for audio generation")
            self.use_pyttsx3 = False
    
    def generate_audio_summary(self, digest: Dict[str, Any]) -> Optional[str]:
        """Generate audio summary of the digest"""
        try:
            # First, generate a concise summary using LLM
            summary_text = self._generate_summary_text(digest)
            
            if not summary_text:
                print("❌ Failed to generate summary text")
                return None
            
            # Generate audio file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            persona = digest.get('persona', 'digest').lower().replace(' ', '_')
            audio_filename = f"{persona}_summary_{timestamp}.mp3"
            audio_path = self.output_dir / audio_filename
            
            if self.use_pyttsx3:
                success = self._generate_with_pyttsx3(summary_text, str(audio_path))
            else:
                success = self._generate_with_gtts(summary_text, str(audio_path))
            
            if success:
                print(f"🔊 Audio summary generated: {audio_filename}")
                return str(audio_path)
            else:
                print("❌ Failed to generate audio file")
                return None
                
        except Exception as e:
            print(f"❌ Error generating audio summary: {e}")
            return None
    
    def _generate_summary_text(self, digest: Dict[str, Any]) -> str:
        """Generate a concise audio-friendly summary using LLM"""
        
        items = digest.get('items', [])
        if not items:
            return f"Today's {digest.get('persona', 'digest')} has no items to report."
        
        # Prepare content for LLM - limit to top 5 items to reduce prompt size
        items_text = ""
        for i, item in enumerate(items[:5], 1):  # Reduced from 10 to 5
            title = item.get('title', '')[:100]  # Truncate title
            topic = item.get('topic', '')
            why_it_matters = item.get('why_it_matters', '').strip('"')[:150]  # Truncate
            star_rating = item.get('star_rating', '⭐')
            tags = ', '.join(item.get('tags', [])[:2])  # Limit tags
            
            items_text += f"""
Item {i}: {title}
Rating: {star_rating}
Tags: {tags}
Why it matters: {why_it_matters}
---
"""
        
        # Shorter, more focused prompt
        prompt = f"""Create a 2-minute audio summary for {digest.get('persona', 'digest')} with {len(items)} items.

DIGEST ITEMS:
{items_text}

Requirements:
1. Keep under 300 words
2. Conversational podcast style
3. Mention top items with ratings
4. Brief conclusion about trends
5. No URLs or technical IDs

Start: "Welcome to today's {digest.get('persona', 'digest')} summary..."
"""
        
        try:
            print(f"    📤 Generating summary text with LLM (timeout: 180s)...")
            summary = llm.generate(
                prompt=prompt,
                system_prompt="You are a professional podcast host creating brief, engaging audio summaries.",
                temperature=0.3,
                timeout=180  # Increased timeout for audio generation
            )
            
            # Clean up the summary for audio
            summary = summary.replace('*', '').replace('#', '').replace('`', '')
            summary = summary.replace('⭐', 'star')
            
            print(f"    ✅ Generated {len(summary)} character summary")
            return summary.strip()
            
        except Exception as e:
            print(f"    ❌ Failed to generate summary text: {e}")
            # Fallback summary
            fallback = f"Welcome to today's {digest.get('persona', 'digest')} summary. "
            fallback += f"We have {len(items)} high-quality items covering topics like "
            
            # Extract topics from items
            topics = []
            for item in items[:3]:
                topic = item.get('topic', '')
                if topic and topic not in topics:
                    topics.append(topic)
            
            if topics:
                fallback += ', '.join(topics) + ". "
            
            fallback += "Check out the full digest for detailed analysis and links to all articles."
            
            return fallback
    
    def _generate_with_pyttsx3(self, text: str, output_path: str
) -> bool:
        """Generate audio using pyttsx3 (offline)"""
        try:
            # Convert .mp3 to .wav for pyttsx3
            wav_path = output_path.replace('.mp3', '.wav')
            
            self.engine.save_to_file(text, wav_path)
            self.engine.runAndWait()
            
            # Convert WAV to MP3 if ffmpeg is available
            try:
                import subprocess
                subprocess.run([
                    'ffmpeg', '-i', wav_path, '-codec:a', 'libmp3lame', 
                    '-b:a', '128k', output_path, '-y'
                ], check=True, capture_output=True)
                
                # Remove WAV file
                os.remove(wav_path)
                return True
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                # If ffmpeg not available, keep WAV file
                print("⚠️  ffmpeg not available, keeping WAV format")
                final_path = output_path.replace('.mp3', '.wav')
                if wav_path != final_path:
                    os.rename(wav_path, final_path)
                return True
                
        except Exception as e:
            print(f"❌ pyttsx3 generation failed: {e}")
            return False
    
    def _generate_with_gtts(self, text: str, output_path: str) -> bool:
        """Generate audio using Google TTS (online)"""
        try:
            print(f"    🌐 Using Google TTS for audio generation...")
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            return True
            
        except Exception as e:
            print(f"❌ gTTS generation failed: {e}")
            return False

# Global TTS service
tts_service = TTSService()