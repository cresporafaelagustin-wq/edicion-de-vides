"""Edita C0475.MP4: sincroniza el audio del micrófono, corta silencios,
añade subtítulos y título, y exporta en vertical 1080x1920 para redes."""
import subprocess
from pathlib import Path

BASE = Path(__file__).parent
VIDEO = BASE / "originales/C0475.MP4"
AUDIO = BASE / "originales/2.wav"
SALIDA = BASE / "salida/C0475_editado.mp4"
ASS = BASE / "salida/C0475_subtitulos.ass"
SRT = BASE / "salida/C0475_subtitulos.srt"

DESFASE_MIC = 0.655  # el micrófono empezó a grabar 0,655 s después que la cámara
TITULO = "Me lo tengo que pensar"
DURACION_TITULO = 3.0

# Tramos del video original que se conservan (se quitan los silencios)
TRAMOS = [(0.0, 6.6), (8.65, 13.6), (14.2, 17.95), (19.6, 30.72)]

# Subtítulos en tiempos del video original
SUBTITULOS = [
    (0.70, 3.40, "Pues la verdad…"),
    (3.40, 6.50, "me lo tengo que pensar"),
    (8.80, 13.50, "¿Me lo tendría que pensar?"),
    (14.30, 17.85, "¿Me lo tendría que pensar?"),
    (19.70, 21.80, "¿Genial?"),
    (21.80, 23.80, "¿No eran tres?"),
    (23.80, 25.40, "No, son dos, únicamente"),
    (25.40, 27.60, "Ah, vale. Sí, sí"),
    (27.60, 30.70, "Bueno, pues esto lo…"),
]


def a_tiempo_editado(t):
    """Convierte un tiempo del original al tiempo del video ya cortado."""
    acumulado = 0.0
    for ini, fin in TRAMOS:
        if t < ini:
            return acumulado
        if t <= fin:
            return acumulado + (t - ini)
        acumulado += fin - ini
    return acumulado


def fmt_ass(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def fmt_srt(t):
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def escribir_subtitulos():
    subs = [(a_tiempo_editado(i), a_tiempo_editado(f), txt) for i, f, txt in SUBTITULOS]
    cabecera = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Liberation Sans,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,80,80,560,1
Style: Titulo,Liberation Sans,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,24,0,8,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = [f"Dialogue: 1,{fmt_ass(0)},{fmt_ass(DURACION_TITULO)},Titulo,,0,0,0,,{{\\fad(200,300)}}{TITULO}"]
    lineas += [f"Dialogue: 0,{fmt_ass(i)},{fmt_ass(f)},Sub,,0,0,0,,{txt}" for i, f, txt in subs]
    ASS.write_text(cabecera + "\n".join(lineas) + "\n", encoding="utf-8")
    SRT.write_text(
        "\n".join(f"{n}\n{fmt_srt(i)} --> {fmt_srt(f)}\n{txt}\n" for n, (i, f, txt) in enumerate(subs, 1)),
        encoding="utf-8",
    )


def exportar():
    n = len(TRAMOS)
    filtros = [
        # Audio del micrófono: sincronizado, sin graves ni ruido de fondo, comprimido
        f"[1:a]adelay={int(DESFASE_MIC * 1000)}:all=1,highpass=f=80,afftdn=nf=-30,"
        f"acompressor=threshold=-20dB:ratio=3:attack=5:release=100,"
        f"asplit={n}" + "".join(f"[mic{i}]" for i in range(n)),
        f"[0:v]split={n}" + "".join(f"[cam{i}]" for i in range(n)),
    ]
    for i, (ini, fin) in enumerate(TRAMOS):
        filtros.append(f"[cam{i}]trim={ini}:{fin},setpts=PTS-STARTPTS[v{i}]")
        filtros.append(f"[mic{i}]atrim={ini}:{fin},asetpts=PTS-STARTPTS[a{i}]")
    filtros += [
        "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]",
        f"[vc]scale=1080:1920,fps=30,subtitles={ASS}[vout]",
        "[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]",
    ]
    filtro = ";".join(filtros)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-stats",
            "-i", str(VIDEO), "-i", str(AUDIO),
            "-filter_complex", filtro,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            str(SALIDA),
        ],
        check=True,
    )


if __name__ == "__main__":
    SALIDA.parent.mkdir(exist_ok=True)
    escribir_subtitulos()
    exportar()
    print("Listo:", SALIDA)
