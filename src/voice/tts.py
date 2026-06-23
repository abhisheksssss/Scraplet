from __future__ import annotations
import re
import os
from rich.console import Console
import sounddevice as sd

console=Console()

_kokoro_model=None

def _get_kokoro():
    """Lazy-loads the Kokoro TTS model into memory."""
    global _kokoro_model
    if _kokoro_model is None:
        try:
            console.print("[dim]Loading Kokoro TTS model...[/dim]")
            from kokoro_onnx import Kokoro
            
            # Dynamically locate the src/models folder you created
            base_dir = os.path.dirname(os.path.dirname(__file__)) # Gets the 'src' directory
            model_path = os.path.join(base_dir, "models", "kokoro-v1.0.onnx")
            voices_path = os.path.join(base_dir, "models", "voices-v1.0.bin")
            
            _kokoro_model = Kokoro(model_path, voices_path)
            console.print("[green]Kokoro TTS ready.[/green]")
        except ImportError:
            console.print("[red]Kokoro-onnx not installed. Run: pip install kokoro-onnx sounddevice[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Failed to load Kokoro: {e}[/red]")
            return None
    return _kokoro_model

def _clean_text_for_speech(text:str)->str:
    """Remove markdown formatting so it sounds natural when spoken."""
    text = re.sub(r"```[\s\S]*?```", "...code block omitted...", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def speak(text:str,voice:str="af_bella"):
    """
    Speaks text using Kokoro ONNX.
    Some great voices: af_bella (US Female), af_sarah (US Female), am_adam (US Male)
    """
    
    cleaned=_clean_text_for_speech(text)
    if not cleaned:
        return False
    
    kokoro=_get_kokoro()
    if not kokoro:
        return False
    console.print(f"[dim italic] Speaking(kokoro)...[/dim italic]")
    try:
        # Generate the audio samples
        # speed=1.0 is default, lang="en-us" is default for 'a' prefixed voices
        samples, sample_rate = kokoro.create(cleaned, voice=voice, speed=1.0, lang="en-us")
        
        # Play the audio synchronously
        sd.play(samples, sample_rate)
        sd.wait() # Wait until audio finishes playing
        
        return True
    except Exception as e:
        console.print(f"[red]TTS Error: {e}[/red]")
        return False



    
