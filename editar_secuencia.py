"""Edita Secuencia.01.mp4: se queda con la mejor toma de cada frase, quita
pausas y errores, alterna un leve zoom para disimular los cortes, añade
subtítulos estilo Reels y título, y normaliza el audio para redes."""
import json
import re
import subprocess
from pathlib import Path

from editar import fmt_ass, fmt_srt

BASE = Path(__file__).parent
VIDEO = BASE / "originales/Secuencia.01.mp4"
SALIDA = BASE / "salida/Secuencia.01_editado.mp4"
ASS = BASE / "salida/Secuencia.01_subtitulos.ass"
SRT = BASE / "salida/Secuencia.01_subtitulos.srt"

TITULO = "¿Tu cliente te dice\\N«me lo tengo que pensar»?"
DURACION_TITULO = 3.5
ZOOM = 1.12  # zoom de los tramos alternos

# (inicio, fin, frases del subtítulo separadas por "|") en tiempos del original
TRAMOS = [
    (0.00, 2.25, "Si un cliente te dice|«me lo tengo que pensar»,"),
    (4.98, 7.30, "no intentes|convencerle todavía."),
    (35.35, 37.30, "Yo, de entrada,|no le diría nada."),
    (38.25, 40.15, "Le dejaría|que terminara."),
    (41.50, 45.78, "Porque muchas veces|ese «me lo tengo que pensar»|no es la objeción real."),
    (64.15, 69.00, "Pero muchos closers|escuchan esa frase|y siempre cometen|el mismo error."),
    (70.55, 75.80, "Se lanzan a rebatirla|sin saber ni por qué|el cliente|se lo está diciendo."),
    (77.55, 78.75, "Pero espera un momento."),
    (79.80, 80.75, "Yo siempre digo:"),
    (83.00, 86.95, "¿Cómo vas a resolver|una objeción|que todavía no conoces?"),
    (88.30, 90.35, "Puede que no tenga dinero,"),
    (92.50, 95.75, "puede que no hayas generado|la suficiente confianza"),
    (98.85, 102.45, "o puede simplemente|que no hayas conectado con él."),
    (112.95, 117.55, "Así que, si después de escucharle,|sigue sin saber|qué le está frenando,"),
    (119.35, 121.65, "simplemente pregúntale:"),
    (123.40, 125.50, "«¿Qué es lo que todavía|no tienes claro?»"),
    (126.05, 128.45, "Y después,|cállate y escucha."),
    (131.30, 137.00, "Resolver objeciones|no consiste en memorizar|frases para cada momento."),
    (141.28, 143.00, "Consiste en entender"),
    (147.70, 151.55, "qué está frenando realmente|al cliente|en este momento."),
    (156.93, 160.08, "Comenta «OBJECIONES»|si quieres que hablemos|de la tarea."),
]


def subtitulos():
    """Reparte cada tramo en frases cortas, con duración proporcional a su longitud."""
    subs, t = [], 0.0
    for ini, fin, texto in TRAMOS:
        frases = texto.split("|")
        dur = fin - ini
        total = sum(len(f) for f in frases)
        for f in frases:
            d = dur * len(f) / total
            subs.append((t, t + d, f))
            t += d
    return subs, t


def escribir_subtitulos(subs):
    cabecera = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Liberation Sans,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,7,3,2,90,90,620,1
Style: Titulo,Liberation Sans,70,&H00000000,&H00000000,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,3,26,0,8,90,90,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = [f"Dialogue: 1,{fmt_ass(0)},{fmt_ass(DURACION_TITULO)},Titulo,,0,0,0,,{{\\fad(150,300)}}{TITULO}"]
    lineas += [
        f"Dialogue: 0,{fmt_ass(i)},{fmt_ass(f)},Sub,,0,0,0,,{{\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}}{txt}"
        for i, f, txt in subs
    ]
    ASS.write_text(cabecera + "\n".join(lineas) + "\n", encoding="utf-8")
    SRT.write_text(
        "\n".join(f"{n}\n{fmt_srt(i)} --> {fmt_srt(f)}\n{txt}\n" for n, (i, f, txt) in enumerate(subs, 1)),
        encoding="utf-8",
    )


def medir_volumen():
    """Primera pasada de loudnorm para una normalización precisa a -14 LUFS."""
    filtro_audio = ";".join(
        f"[0:a]atrim={ini}:{fin},asetpts=PTS-STARTPTS[a{i}]" for i, (ini, fin, _) in enumerate(TRAMOS)
    ) + ";" + "".join(f"[a{i}]" for i in range(len(TRAMOS))) + f"concat=n={len(TRAMOS)}:v=0:a=1,{LIMPIEZA},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json"
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(VIDEO), "-filter_complex", filtro_audio, "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr).group(0))


LIMPIEZA = "highpass=f=80,afftdn=nf=-35,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120"


def exportar():
    m = medir_volumen()
    n = len(TRAMOS)
    filtros = [
        f"[0:v]split={n}" + "".join(f"[cam{i}]" for i in range(n)),
        f"[0:a]asplit={n}" + "".join(f"[mic{i}]" for i in range(n)),
    ]
    for i, (ini, fin, _) in enumerate(TRAMOS):
        zoom = (
            f",scale=iw*{ZOOM}:ih*{ZOOM},crop=1080:1920:(iw-1080)/2:(ih-1920)*0.35" if i % 2 else ""
        )
        filtros.append(f"[cam{i}]trim={ini}:{fin},setpts=PTS-STARTPTS{zoom},setsar=1[v{i}]")
        # fundidos de 15 ms para que los cortes de audio no hagan "clic"
        filtros.append(
            f"[mic{i}]atrim={ini}:{fin},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=0.015,afade=t=out:st={fin - ini - 0.015:.3f}:d=0.015[a{i}]"
        )
    filtros += [
        "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]",
        f"[vc]subtitles={ASS}[vout]",
        f"[ac]{LIMPIEZA},loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
        "aresample=48000[aout]",
    ]
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(VIDEO),
            "-filter_complex", ";".join(filtros),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            str(SALIDA),
        ],
        check=True,
    )


if __name__ == "__main__":
    SALIDA.parent.mkdir(exist_ok=True)
    subs, duracion = subtitulos()
    escribir_subtitulos(subs)
    exportar()
    print(f"Listo: {SALIDA} ({duracion:.1f} s)")
