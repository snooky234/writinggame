from nicegui import ui
import random
import asyncio
import subprocess
import json
from pathlib import Path
from image_generator import ImageGenerator
from words import WOERTER, ALPHABET

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Woerter nach Schwierigkeitsgrad

class ReadingApp:
    def __init__(self):
        self.aktuelles_wort = ''
        self.geschriebenes_wort = ''
        self.spiel_laeuft = False
        self.verbleibende_zeit = 60
        self.timer_task = None
        self.audio_cache = Path('audio_cache')
        self.audio_cache.mkdir(exist_ok=True)
        self.image_generator = ImageGenerator()
        self.bild_container = None
        self.bild_timer = None
        # Piper voice configuration: model path and slower speaking rate
        self.tts_model_path = Path('piper/de_DE-thorsten_emotional-medium.onnx')
        # self.tts_model_path = Path('piper/de_DE-thorsten-medium.onnx')
        self.tts_length_scale = 2
        self.tts_speaker = 7
        self.erfolgsaussagen = [
            'Super',
            'gut gemacht',
            'Perfekt',
            'Toll gemacht',
            'Das war gut!'
        ]

    def generiere_audio(self, text: str) -> str:
        """Generates audio with Piper TTS"""
        model_path = self.tts_model_path
        voice_id = model_path.stem
        scale_tag = f"ls{self.tts_length_scale}".replace('.', '_')
        speaker_value = str(self.tts_speaker) if self.tts_speaker is not None else 'default'
        safe_speaker = speaker_value.replace('/', '_').replace(' ', '-')
        filepath = self.audio_cache / (
            f"{voice_id}_{safe_speaker}_{scale_tag}_{text.lower()}.wav"
        )
        if filepath.exists():
            return str(filepath)
        
        try:
            piper_exe = Path('piper/piper.exe')
            
            if not piper_exe.exists() or not model_path.exists():
                print(f"Error: Piper or model not found")
                return None
            
            command = [
                str(piper_exe),
                '--model', str(model_path),
                '--output_file', str(filepath),
                '--length_scale', str(self.tts_length_scale),
            ]
            if self.tts_speaker is not None:
                speaker_value = str(self.tts_speaker)
                option = '--speaker-id' if isinstance(self.tts_speaker, int) or speaker_value.isdigit() else '--speaker'
                command.extend([option, speaker_value])
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=text.encode('utf-8'))
            
            if process.returncode == 0:
                return str(filepath)
            print(f"Error: Piper failed: {stderr.decode()}")
            return None
        except Exception as e:
            print(f"Error: Audio generation failed: {e}")
            return None
    
    def spreche_wort(self, wort):
        """Spielt Audio ab"""
        if not wort:
            return
        audio_path = self.generiere_audio(wort)
        if audio_path:
            audio_url = f"/audio_cache/{Path(audio_path).name}"
            script = f'''
                window.__audioQueue = window.__audioQueue || (function() {{
                    const state = {{ queue: [], playing: false }};
                    state.playNext = function() {{
                        if (!state.queue.length) {{
                            state.playing = false;
                            return;
                        }}
                        state.playing = true;
                        const src = state.queue.shift();
                        const audio = new Audio(src);
                        audio.addEventListener('ended', state.playNext);
                        audio.addEventListener('error', state.playNext);
                        audio.play().catch(err => {{
                            console.error('Audio error:', err);
                            state.playNext();
                        }});
                    }};
                    state.enqueue = function(src) {{
                        state.queue.push(src);
                        if (!state.playing) {{
                            state.playNext();
                        }}
                    }};
                    return state;
                }})();
                window.__audioQueue.enqueue({json.dumps(audio_url)});
            '''
            ui.run_javascript(script)
    
    def buchstabe_hinzufuegen(self, buchstabe):
        """Fügt Buchstaben hinzu"""
        if not self.spiel_laeuft:
            return
        self.geschriebenes_wort += buchstabe
        self.aktualisiere_anzeige()
        self.spreche_wort(self.geschriebenes_wort)
        
        # Prüfe ob Wort korrekt
        if self.geschriebenes_wort == self.aktuelles_wort:
            self.spiel_gewonnen()
    
    def buchstabe_entfernen(self, index):
        """Entfernt Buchstaben"""
        if not self.spiel_laeuft:
            return
        self.geschriebenes_wort = (self.geschriebenes_wort[:index] + 
                                   self.geschriebenes_wort[index+1:])
        self.aktualisiere_anzeige()
        self.spreche_wort(self.geschriebenes_wort)
    
    def aktualisiere_anzeige(self):
        """Aktualisiert Buchstaben-Anzeige"""
        self.buchstaben_container.clear()
        with self.buchstaben_container:
            for i, buchstabe in enumerate(self.geschriebenes_wort):
                ui.button(buchstabe, on_click=lambda idx=i: self.buchstabe_entfernen(idx)
                         ).classes('text-2xl w-12 h-12 bg-gray-300 hover:bg-red-300')
    
    def pruefe_bild_verfuegbar(self):
        """Checks if image is available and updates display"""
        # Sicherheitscheck: Wenn Timer bereits None ist, nicht weitermachen
        if self.bild_timer is None:
            return
            
        bildpfad = Path(f'assets/{self.aktuelles_wort.lower()}.png')
        if bildpfad.exists():
            # Timer SOFORT stoppen und auf None setzen
            if self.bild_timer:
                self.bild_timer.active = False
                self.bild_timer.cancel()
                self.bild_timer = None
            
            # Bild nur laden wenn Container noch existiert
            if self.bild_container:
                self.bild_container.clear()
                with self.bild_container:
                    ui.image(f'assets/{self.aktuelles_wort.lower()}.png').classes(
                        'w-full max-h-64 md:max-h-96 object-contain mx-auto rounded-xl')
                    
            print(f"✓ Image loaded once: {self.aktuelles_wort}")
    
    def spiel_gewonnen(self):
        """Gewonnen"""
        self.spiel_laeuft = False
        
        # Timer komplett stoppen
        if self.timer_task:
            self.timer_task.cancel()
            
        # Bild-Timer stoppen und auf None setzen
        if self.bild_timer:
            self.bild_timer.active = False
            self.bild_timer.cancel()
            self.bild_timer = None

        self.spreche_wort(random.choice(self.erfolgsaussagen))

        ui.notify(' Gewonnen! 🎉', type='positive', position='center', timeout=3000, 
             classes='text-4xl')
        ui.timer(3.0, lambda: ui.navigate.to('/'), once=True)
    
    def spiel_verloren(self):
        """Time up"""
        self.spiel_laeuft = False
        
        # Bild-Timer stoppen und auf None setzen
        if self.bild_timer:
            self.bild_timer.active = False
            self.bild_timer.cancel()
            self.bild_timer = None
            
        ui.notify(f'⏰ Time up! The word was: {self.aktuelles_wort}', 
                 type='negative', position='center', timeout=5000)
        ui.timer(4.0, lambda: ui.navigate.to('/'), once=True)
    
    async def timer_countdown(self):
        """Timer-Countdown"""
        while self.verbleibende_zeit > 0 and self.spiel_laeuft:
            await asyncio.sleep(1)
            self.verbleibende_zeit -= 1
            self.progress.set_value(self.verbleibende_zeit / 60)
        if self.spiel_laeuft:
            self.spiel_verloren()
    
    def starte_spiel(self, schwierigkeitsgrad):
        """Startet neues Spiel"""
        self.aktuelles_wort = random.choice(WOERTER[schwierigkeitsgrad])
        self.geschriebenes_wort = ''
        self.verbleibende_zeit = 60
        self.spiel_laeuft = True
        asyncio.create_task(asyncio.to_thread(
            self.image_generator.generate_image, self.aktuelles_wort))
        ui.navigate.to('/spiel')
    
    def erstelle_startseite(self):
        """Start screen""" 
        with ui.column().classes('w-full min-h-screen px-4 py-6 md:py-12 items-center justify-center gap-6'):
            ui.label('Wort Spiel').classes('text-4xl md:text-6xl font-bold text-blue-600 text-center')
            
            with ui.row().classes('w-full max-w-sm md:max-w-3xl gap-4 md:gap-8 flex-wrap justify-center'):
                for level, (farbe, text) in enumerate([
                    ('green', '👶 Leicht'),
                    ('yellow', '👦 Mittel'),
                    ('red', '🦸‍♀️ Schwer')
                ], 1):
                    ui.button(text, on_click=lambda l=level: self.starte_spiel(l)
                             ).classes(f'text-2xl md:text-3xl px-6 py-5 md:px-8 md:py-6 bg-{farbe}-500 text-white rounded-xl w-full max-w-xs shadow-md')
    
    def erstelle_spielseite(self):
        """Game page"""
        with ui.column().classes('w-full min-h-screen p-4 md:p-8 gap-4 md:gap-6'):
            # Audio buttons
            with ui.row().classes('w-full justify-center md:justify-end gap-3 flex-wrap'):
                ui.button('🔊 Dein Wort', on_click=lambda: self.spreche_wort(
                    self.geschriebenes_wort or 'nothing')
                         ).classes('bg-purple-500 text-white text-lg md:text-xl px-4 py-2.5 md:px-6 md:py-3 rounded-lg w-full max-w-xs md:w-auto')
                ui.button('🎯 Suchwort', on_click=lambda: self.spreche_wort(
                    self.aktuelles_wort)
                         ).classes('bg-green-500 text-white text-lg md:text-xl px-4 py-2.5 md:px-6 md:py-3 rounded-lg w-full max-w-xs md:w-auto')
            
            # Timer
            self.progress = (
                ui.linear_progress(value=1.0, size='30px', show_value=False)
                .props('color=blue :show-value="false"')
                .classes('w-full h-2 md:h-3 rounded-full')
            )
            
            # Image container (dynamically updated)
            self.bild_container = ui.column().classes('w-full max-w-xs md:max-w-md mx-auto')
            
            bildpfad = Path(f'assets/{self.aktuelles_wort.lower()}.png')
            if bildpfad.exists():
                # Image already exists
                with self.bild_container:
                    ui.image(f'assets/{self.aktuelles_wort.lower()}.png').classes(
                        'w-full max-h-64 md:max-h-96 object-contain mx-auto rounded-xl')
            else:
                # Image still generating - loading display + timer
                with self.bild_container:
                    with ui.card().classes('w-full max-w-xs md:max-w-md h-64 md:h-96 flex items-center justify-center bg-gray-100 rounded-xl'):
                        ui.spinner(size='md')
                        ui.label('🎨 Bild erstellen...').classes('text-lg md:text-xl mt-4 text-gray-500 text-center px-2')
                
                # Timer that checks every 0.5 seconds
                self.bild_timer = ui.timer(0.5, self.pruefe_bild_verfuegbar)
            
            # Letter container
            with ui.card().classes('w-full mx-auto p-4'):
                self.buchstaben_container = ui.row().classes('justify-center flex-wrap gap-2 md:gap-3 min-h-14')
            
            # Alphabet
            # Alphabet mit automatischem Zeilenumbruch am Ende jeder Zeile
            max_buchstaben_pro_zeile = 8
            alphabet_chunks = [ALPHABET[i:i+max_buchstaben_pro_zeile] for i in range(0, len(ALPHABET), max_buchstaben_pro_zeile)]
            # Dynamisch: Buchstaben pro Zeile, abhängig von Bildschirmbreite
            with ui.row().classes('w-full max-w-4xl mx-auto flex-wrap gap-2 justify-center'):
                for buchstabe in ALPHABET:
                    ui.button(buchstabe, on_click=lambda b=buchstabe: self.buchstabe_hinzufuegen(b)
                             ).classes('text-2xl md:text-3xl font-bold px-3 py-3 md:px-4 md:py-4 bg-blue-500 text-white rounded-lg w-12 h-12 md:w-16 md:h-16')
            # Start timer
            self.timer_task = asyncio.create_task(self.timer_countdown())

# Create app
app = ReadingApp()

@ui.page('/')
def startseite():
    ui.dark_mode().enable() 
    app.erstelle_startseite()

@ui.page('/spiel')
def spielseite():
    ui.dark_mode().enable() 
    app.erstelle_spielseite()

# Register audio cache
from nicegui import app as nicegui_app
nicegui_app.add_static_files('/audio_cache', 'audio_cache')

ui.run(title='Word Game', port=8080)