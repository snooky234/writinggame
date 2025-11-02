import base64
import os
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ImageGenerator:
    def __init__(self, assets_dir: str = 'assets') -> None:
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print('❌ OPENAI_API_KEY fehlt in der Umgebung oder .env.')
            self.client = None
            return
        if OpenAI is None:
            print('❌ openai-Paket nicht installiert. Bitte `pip install openai` ausführen.')
            self.client = None
            return
        self.client = OpenAI(api_key=api_key)

    def generate_image(self, wort: str) -> Optional[Path]:
        if not wort:
            return None
        target_path = self.assets_dir / f'{wort.lower()}.png'
        if target_path.exists():
            return target_path
        if self.client is None:
            return None

        prompt = (
            f"Erstelle ein farbenfrohes, kinderfreundliches Illustrationsbild von '{wort.lower()}', "
            "Soll wirken wie mit aquarell aus einem Bilderbuch, nicht zu verspielt freundlicher Stil, einfacher Hintergrund, WICHTIG: keine Buchstaben im Bild!!"
        )

        try:
            response = self.client.images.generate(
                model='dall-e-3',
                prompt=prompt,
                size='1024x1024',
                response_format='b64_json'
            )
            data = response.data[0]
            image_base64 = getattr(data, 'b64_json', None)
            if image_base64:
                image_bytes = base64.b64decode(image_base64)
            elif getattr(data, 'url', None):
                with urlopen(data.url) as remote:
                    image_bytes = remote.read()
            else:
                print(f'❌ OpenAI lieferte keine Bilddaten für "{wort}".')
                return None
            target_path.write_bytes(image_bytes)
            return target_path
        except Exception as exc:
            message = str(exc)
            if 'must be verified to use the model' in message:
                print('❌ Organisation muss für dalle-3 verifiziert werden. Bitte erst verifizieren oder anderes Modell wählen.')
            else:
                print(f'❌ Fehler bei der OpenAI-Bilderzeugung für "{wort}": {message}')
            return None