"""
ai_hang.py – AI-narráció generálása a hat jelenethez (Microsoft Edge neurális magyar hang)
=========================================================================================

Futtatás a saját gépen (a felhőből a szolgáltatás nem érhető el):

    pip install edge-tts
    python video/tts/ai_hang.py            # → video/tts/01.mp3 … 06.mp3

A szöveget a video/tts/segments.json-ból veszi (ugyanabból készül a felirat is).
Hang: hu-HU-TamasNeural (férfi). A --rate és --pitch a „trailer” hangulathoz lassít
és mélyít; ha túl lassú/mély, állítsd (pl. --rate=-5% --pitch=-4Hz).

Alternatív hang: hu-HU-NoemiNeural (női). Lista: edge-tts --list-voices | findstr hu-HU
"""

import asyncio
import json
import os
import sys

try:
    import edge_tts
except ImportError:
    sys.exit("Hiányzik az edge-tts: pip install edge-tts")

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE = "hu-HU-TamasNeural"
RATE = "40%"      # lassabb, nyomatékosabb
PITCH = "-20Hz"     # kicsit mélyebb


async def main():
    with open(os.path.join(HERE, "segments.json"), encoding="utf-8") as f:
        segs = json.load(f)
    for key, text in segs.items():
        out = os.path.join(HERE, f"{key}.mp3")
        tts = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        await tts.save(out)
        print("kész:", out, f"({len(text.split())} szó)")
    print("Töröld a régi 01–06.m4a fájlokat (vagy nevezd át), hogy a vágó az mp3-at használja: "
          "a build_video.py az .m4a-t előbb keresi.")


if __name__ == "__main__":
    asyncio.run(main())
