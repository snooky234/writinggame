from nicegui import ui
import random
import asyncio

# Wortspeicher mit drei Schwierigkeitsgraden
WORT_SPEICHER = {
    1: ['AUTO', 'NASE', 'HASE', 'TASSE', 'DOSE', 'ROSE', 'SONNE', 'MOND', 'FUSS', 'HAND'],
    2: ['SCHUBLADE', 'TASCHENTUCH', 'REGENBOGEN', 'SANDKASTEN', 'BLUMENTOPF', 'HANDSCHUH', 
        'SCHULBUS', 'APFELBAUM', 'KAUFHAUS', 'TURNSCHUH'],
    3: ['GITARRE', 'TABLETT', 'TRITTLEITER', 'VÖGEL', 'MÄHNE', 'KÄFIG', 'KÖNIGIN', 
        'PHYSIK', 'YACHT', 'RHYTHMUS']
}

# Alphabet mit Umlauten
ALPHABET = list('ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ')

class LeselernApp:
    def __init__(self):
        self.aktuelles_wort = ''
        self.geschriebenes_wort = ''
        self.schwierigkeitsgrad = 1
        self.timer_task = None
        self.verbleibende_zeit = 60
        self.spiel_laeuft = False
        
    def spreche_wort_sync(self, wort):
        """Spricht das Wort mit Browser Speech Synthesis aus (synchron)"""
        if not wort:
            return
        try:
            ui.run_javascript(f'''
                (function() {{
                    const text = "{wort.lower()}";
                    console.log("Spreche:", text);
                    
                    if (typeof speechSynthesis === 'undefined') {{
                        console.error("Speech Synthesis nicht verfügbar!");
                        return;
                    }}
                    
                    speechSynthesis.cancel();
                    
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'de-DE';
                    utterance.rate = 0.8;
                    utterance.pitch = 1.0;
                    utterance.volume = 1.0;
                    
                    speechSynthesis.speak(utterance);
                }})();
            ''')
        except Exception as e:
            print(f"Speech Synthesis Fehler: {e}")
    
    async def spreche_wort(self, wort):
        """Spricht das Wort mit Browser Speech Synthesis aus (async für Test-Button)"""
        if not wort:
            return
        try:
            result = await ui.run_javascript(f'''
                return new Promise((resolve) => {{
                    const text = "{wort.lower()}";
                    console.log("=== Spreche:", text, "===");
                    
                    // Prüfe Speech Synthesis Verfügbarkeit
                    if (typeof speechSynthesis === 'undefined') {{
                        console.error("❌ speechSynthesis ist nicht definiert!");
                        alert("Speech Synthesis ist in diesem Browser nicht verfügbar!");
                        resolve(false);
                        return;
                    }}
                    
                    console.log("✓ speechSynthesis ist verfügbar");
                    
                    // Warte auf Stimmen zu laden
                    let voices = speechSynthesis.getVoices();
                    console.log("Verfügbare Stimmen:", voices.length);
                    
                    const speakNow = () => {{
                        voices = speechSynthesis.getVoices();
                        console.log("Jetzt verfügbare Stimmen:", voices.length);
                        
                        speechSynthesis.cancel();
                        
                        const utterance = new SpeechSynthesisUtterance(text);
                        
                        // Suche deutsche Stimme
                        const germanVoice = voices.find(v => v.lang.startsWith('de'));
                        if (germanVoice) {{
                            console.log("✓ Deutsche Stimme gefunden:", germanVoice.name);
                            utterance.voice = germanVoice;
                        }} else {{
                            console.log("⚠ Keine deutsche Stimme, nutze Standard");
                        }}
                        
                        utterance.lang = 'de-DE';
                        utterance.rate = 0.8;
                        utterance.pitch = 1.0;
                        utterance.volume = 1.0;
                        
                        utterance.onstart = () => {{
                            console.log("✓✓✓ Speech GESTARTET ✓✓✓");
                        }};
                        
                        utterance.onend = () => {{
                            console.log("✓ Speech beendet");
                            resolve(true);
                        }};
                        
                        utterance.onerror = (e) => {{
                            console.error("❌ Speech error:", e.error, e);
                            alert("Speech Error: " + e.error);
                            resolve(false);
                        }};
                        
                        console.log(">>> Rufe speak() auf...");
                        speechSynthesis.speak(utterance);
                        console.log(">>> speak() aufgerufen");
                    }};
                    
                    // Wenn keine Stimmen verfügbar, warte darauf
                    if (voices.length === 0) {{
                        console.log("Warte auf Stimmen...");
                        speechSynthesis.onvoiceschanged = () => {{
                            console.log("Stimmen geladen!");
                            speakNow();
                        }};
                    }} else {{
                        speakNow();
                    }}
                }});
            ''')
            print(f"Speech Synthesis Ergebnis: {result}")
        except Exception as e:
            print(f"Speech Synthesis Fehler: {e}")
    
    def buchstabe_hinzufuegen(self, buchstabe):
        """Fügt einen Buchstaben zum geschriebenen Wort hinzu"""
        if not self.spiel_laeuft:
            return
        self.geschriebenes_wort += buchstabe
        self.aktualisiere_wortanzeige()
        self.spreche_wort_sync(self.geschriebenes_wort)
        self.pruefe_wort()
    
    def buchstabe_entfernen(self, index):
        """Entfernt einen Buchstaben aus dem geschriebenen Wort"""
        if not self.spiel_laeuft or index >= len(self.geschriebenes_wort):
            return
        self.geschriebenes_wort = self.geschriebenes_wort[:index] + self.geschriebenes_wort[index+1:]
        self.aktualisiere_wortanzeige()
        self.spreche_wort_sync(self.geschriebenes_wort)
    
    def aktualisiere_wortanzeige(self):
        """Aktualisiert die Anzeige des geschriebenen Wortes"""
        self.buchstaben_container.clear()
        with self.buchstaben_container:
            if self.geschriebenes_wort:
                for i, buchstabe in enumerate(self.geschriebenes_wort):
                    ui.button(buchstabe, 
                            on_click=lambda idx=i: self.buchstabe_entfernen(idx)).classes(
                        'text-2xl w-12 h-12 bg-gray-300 hover:bg-red-300')
    
    def pruefe_wort(self):
        """Prüft ob das Wort korrekt geschrieben wurde"""
        print(f"Prüfe: '{self.geschriebenes_wort}' == '{self.aktuelles_wort}'")
        if self.geschriebenes_wort == self.aktuelles_wort:
            print("WORT IST RICHTIG! Spiel gewonnen!")
            self.spiel_gewonnen()
    
    def spiel_gewonnen(self):
        """Wird aufgerufen wenn das Kind gewonnen hat"""
        print(">>> spiel_gewonnen() aufgerufen!")
        self.spiel_laeuft = False
        if self.timer_task:
            self.timer_task.cancel()
        
        ui.notify('🎉 Gewonnen! Das Wort ist richtig!', type='positive', position='center', 
                 close_button=True, timeout=3000)
        print(">>> Starte Timer für Navigation...")
        ui.timer(3.0, lambda: ui.navigate.to('/'), once=True)
    
    def spiel_verloren(self):
        """Wird aufgerufen wenn die Zeit abgelaufen ist"""
        self.spiel_laeuft = False
        ui.notify(f'⏰ Zeit abgelaufen! Das Wort war: {self.aktuelles_wort}', 
                 type='negative', position='center', close_button=True, timeout=5000)
        ui.timer(4.0, lambda: ui.navigate.to('/'), once=True)
    

    
    async def timer_countdown(self):
        """Timer-Countdown für die Progressbar"""
        while self.verbleibende_zeit > 0 and self.spiel_laeuft:
            await asyncio.sleep(1)
            self.verbleibende_zeit -= 1
            self.progress.set_value(self.verbleibende_zeit / 60)
            
        if self.spiel_laeuft:
            self.spiel_verloren()
    
    def starte_spiel(self, schwierigkeitsgrad):
        """Startet ein neues Spiel mit dem gewählten Schwierigkeitsgrad"""
        self.schwierigkeitsgrad = schwierigkeitsgrad
        self.aktuelles_wort = random.choice(WORT_SPEICHER[schwierigkeitsgrad])
        self.geschriebenes_wort = ''
        self.verbleibende_zeit = 60
        self.spiel_laeuft = True
        
        ui.navigate.to('/spiel')
    
    def erstelle_startseite(self):
        """Erstellt den Startbildschirm"""
        with ui.column().classes('w-full h-screen items-center justify-center gap-8'):
            ui.label('Lesen Lernen').classes('text-6xl font-bold text-blue-600')
            ui.label('Wähle einen Schwierigkeitsgrad:').classes('text-3xl')
            
            with ui.row().classes('gap-8'):
                ui.button('Leicht\n(Kurze Wörter)', 
                         on_click=lambda: self.starte_spiel(1)).classes(
                    'text-3xl p-8 bg-green-500 text-white rounded-xl w-64 h-32')
                
                ui.button('Mittel\n(Längere Wörter)', 
                         on_click=lambda: self.starte_spiel(2)).classes(
                    'text-3xl p-8 bg-yellow-500 text-white rounded-xl w-64 h-32')
                
                ui.button('Schwer\n(Schwierige Wörter)', 
                         on_click=lambda: self.starte_spiel(3)).classes(
                    'text-3xl p-8 bg-red-500 text-white rounded-xl w-64 h-32')
    
    def erstelle_spielseite(self):
        """Erstellt die Spielseite"""
        with ui.column().classes('w-full h-screen p-4 gap-4'):
            
            # Speech Synthesis initialisieren beim Laden
            ui.timer(0.1, lambda: ui.run_javascript('''
                console.log("Speech Synthesis Test beim Laden...");
                console.log("speechSynthesis verfügbar:", !!window.speechSynthesis);
                if (window.speechSynthesis) {
                    const voices = window.speechSynthesis.getVoices();
                    console.log("Verfügbare Stimmen:", voices.length);
                    voices.forEach(v => {
                        if (v.lang.startsWith('de')) {
                            console.log("Deutsche Stimme:", v.name, v.lang);
                        }
                    });
                }
            '''), once=True)
            
            # Buttons zum Vorlesen
            with ui.row().classes('w-full justify-end gap-4'):
                ui.button('🔊 Mein Wort vorlesen', 
                         on_click=lambda: self.spreche_wort_sync(self.geschriebenes_wort if self.geschriebenes_wort else 'nichts')).classes(
                    'bg-purple-500 text-white text-xl px-6 py-3')
                ui.button('🎯 Gesuchtes Wort hören', 
                         on_click=lambda: self.spreche_wort_sync(self.aktuelles_wort)).classes(
                    'bg-green-500 text-white text-xl px-6 py-3')
            
            # Timer Progressbar
            self.progress = ui.linear_progress(value=1.0, size='30px').classes('w-full')
            self.progress.props('color=blue')
            
            # Bild
            # bildpfad = f'assets/{self.aktuelles_wort.lower()}.jpg'
            bildpfad = f'assets/apfel.jpg' # Platzhalterbild bis bilder für alle Wörter vorhanden sind
            ui.image(bildpfad).classes('w-96 h-96 object-contain mx-auto')
            
            # Container für gewählte Buchstaben
            with ui.card().classes('w-full mx-auto p-4'):
                self.buchstaben_container = ui.row().classes('justify-center flex-wrap gap-2 min-h-14')
            
            # Alphabet-Buttons
            ui.label('Wähle die Buchstaben:').classes('text-2xl font-bold mx-auto mt-4')
            with ui.grid(columns=9).classes('w-full max-w-4xl mx-auto gap-2'):
                for buchstabe in ALPHABET:
                    ui.button(buchstabe, 
                             on_click=lambda b=buchstabe: self.buchstabe_hinzufuegen(b)).classes(
                        'text-3xl font-bold p-4 bg-blue-500 text-white rounded-lg w-16 h-16 hover:bg-blue-600')
            
            # Starte Timer
            self.timer_task = asyncio.create_task(self.timer_countdown())

# App initialisieren
app = LeselernApp()

@ui.page('/')
def startseite():
    app.erstelle_startseite()

@ui.page('/spiel')
def spielseite():
    app.erstelle_spielseite()

ui.run(title='Leselern-App', port=8080)