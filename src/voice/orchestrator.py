from __future__ import annotations
import questionary
from rich.console import Console

from ..agent.orchestrator import run_agent_task
from .stt import listen_and_transcribe
from .tts import speak

console=Console()

def run_voice_loop()->None:
    console.print(
        "\n[bold cyan]🎙  Voice Assistant Mode[/bold cyan]\n"
        "[dim]Press [bold]Enter[/bold] to speak, say your command, then pause to finish.\n"
        "Type [bold]exit[/bold] and press Enter to quit.[/dim]\n"
    )

    while True:
        try:
            user_input = input("\nPress Enter to speak (or type 'exit' to quit)... ").strip().lower()
            if user_input == "exit":
                speak("Goodbye!")
                break
            # 2. Record and transcribe
            transcript = listen_and_transcribe()
            if not transcript:
                continue

            console.print(f"\n[bold green]You said:[/bold green] {transcript}\n")
            confirmed = questionary.confirm("Send to agent?", default=True).ask()
            
            if not confirmed:
                console.print("[dim]Cancelled.[/dim]")
                continue
                
            console.print("[dim]Running agent...[/dim]")
            result = run_agent_task(
                transcript,
                include_web=True, # Allows the agent to search the web!
                max_steps=20,
            )
            speak(result.text)


        except KeyboardInterrupt:
            console.print("\n[dim]Voice mode interrupted. Bye![/dim]")
            break
    