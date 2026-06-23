from __future__ import annotations
import tempfile
import os 
import speech_recognition as sr
from rich.console import Console

# Add internal ffmpeg to system path for Whisper
try:
    import imageio_ffmpeg
    import shutil
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    target_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    
    # imageio-ffmpeg names the file something like 'ffmpeg-win64-v4.2.2.exe'
    # Whisper hardcodes the command as 'ffmpeg', so we must create a copy named 'ffmpeg.exe'
    if not os.path.exists(target_exe) and ffmpeg_exe != target_exe:
        shutil.copyfile(ffmpeg_exe, target_exe)
        
    os.environ["PATH"] += os.pathsep + ffmpeg_dir
except Exception as e:
    console.print(f"[dim]Failed to setup internal ffmpeg: {e}[/dim]")

console=Console()

_whisper_model=None

def _get_whisper():
    """Load and cache the whisper 'base' model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            console.print("[dim]Loading Whisper base model...[/dim]")
            import whisper
            _whisper_model=whisper.load_model("base")
            console.print("[green]Whisper loaded successfully.[/green]")
        except ImportError:
            console.log("[yellow]Whisper not installed. Please run: pip install openai-whisper[/yellow]")
            return None
    return _whisper_model

def listen_and_transcribe()-> str |None:
    """Record audio from the microphone and transcribes it."""
    recognizer=sr.Recognizer()
    recognizer.energy_threshold=300
    recognizer.pause_threshold=1
    recognizer.dynamic_energy_threshold=True

    with sr.Microphone() as source:
        console.print("[green]Listening...[/green]")
        recognizer.adjust_for_ambient_noise(source,duration=0.5)
        try:
            audio=recognizer.listen(source,timeout=10,phrase_time_limit=60)
        except sr.WaitTimeoutError:
            console.print("[yellow]No speech detected[/yellow]")
            return None
    
    console.print("[dim]Transcribing...[/dim]")

    with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as tmp:
        tmp.write(audio.get_wav_data())
        tmp_path=tmp.name
    
    try:
        model=_get_whisper()
        if not model:
            return None
        result=model.transcribe(tmp_path,language="en",fp16=False)
        text=result["text"].strip()
        return text if text else None
    finally:
        os.unlink(tmp_path)
        
