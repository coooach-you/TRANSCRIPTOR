"""
Transcriptor – přepis s určením mluvčích (Soniox), překlad a shrnutí (Google Gemini).

Spuštění:  streamlit run app.py   (nebo dvojklik na spustit.bat)
Klíče:     SONIOX_API_KEY a GEMINI_API_KEY v souboru .env vedle app.py
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from docx import Document
from dotenv import load_dotenv
from google import genai
from google.genai import types
from soniox import SonioxClient
from soniox.types import CreateTranscriptionConfig, StructuredContext

# ======================================================================================
# Nastavení (ověřeno k 21. 11. 2026)
# ======================================================================================

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")
DEFAULT_OUTPUT_DIR = APP_DIR / "vystupy"


def output_dir() -> Path:
    """Složka pro výsledky. Jde nastavit v aplikaci, třeba do synchronizované složky Google Disku."""
    return Path(os.getenv("OUTPUT_DIR") or DEFAULT_OUTPUT_DIR)


def update_env(values: dict[str, str]):
    """Zapíše hodnoty do .env a zachová ostatní řádky (klíče, nastavení)."""
    env_path = APP_DIR / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    rest = [l for l in lines if l.split("=", 1)[0].strip() not in values]
    rest += [f"{k}={v}" for k, v in values.items()]
    env_path.write_text("\n".join(rest) + "\n", encoding="utf-8")
    os.environ.update(values)

# Soniox: stt-async-v6 je aktuální model pro soubory (0,10 USD za hodinu, mluvčí v ceně).
# Pozor: knihovna soniox má jako výchozí starší v5, proto model předáváme vždy výslovně.
SONIOX_MODEL = os.getenv("SONIOX_MODEL", "stt-async-v6")
SONIOX_USD_PER_HOUR = 0.10
MAX_AUDIO_HOURS = 5

# Gemini: gemini-2.5-flash Google vypíná 1. 12. 2026, proto používáme řadu 3.x.
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"]
DEFAULT_GEMINI = os.getenv("GEMINI_MODEL", GEMINI_MODELS[0])

TRANSLATE_CHUNK_CHARS = 12_000
MAX_SEGMENT_MS = 60_000  # dlouhý monolog rozdělíme na odstavce zhruba po minutě

AUDIO_LANGUAGES = {"Čeština": "cs", "Angličtina": "en", "Slovenština": "sk", "Němčina": "de",
                   "Polština": "pl", "Francouzština": "fr", "Španělština": "es", "Ruština": "ru",
                   "Ukrajinština": "uk"}
TARGET_LANGUAGES = ["čeština", "angličtina", "slovenština", "němčina", "polština",
                    "francouzština", "španělština", "ukrajinština"]

SUMMARY_TEMPLATES = {
    "Stručný přehled": (
        "Napiš stručný přehled nahrávky: 1 odstavec o čem nahrávka je, kdo v ní mluví, "
        "a potom 5 až 8 odrážek s nejdůležitějšími body."
    ),
    "Detailní zápis z porady": (
        "Vytvoř detailní zápis z porady. Struktura: ## Účastníci, ## Probíraná témata "
        "(každé téma s podbody a kdo co navrhoval), ## Rozhodnutí, ## Úkoly "
        "(tabulka: úkol | odpovědná osoba | termín), ## Otevřené otázky."
    ),
    "Seznam úkolů": (
        "Vypiš všechny úkoly, závazky a dohodnuté další kroky jako zaškrtávací seznam "
        "(- [ ] ...). U každého uveď odpovědnou osobu a termín, pokud zazněly. "
        "Nic si nevymýšlej; když osoba nebo termín nezazněly, napiš 'neuvedeno'."
    ),
    "Analýza tónu": (
        "Analyzuj tón a atmosféru rozhovoru: celkové naladění, míra shody či konfliktu, "
        "emoce a postoje jednotlivých mluvčích, momenty napětí a jak se vyřešily. "
        "Každé tvrzení doplň krátkou citací z přepisu s časem."
    ),
}

# ======================================================================================
# Přepis přes Soniox
# ======================================================================================


def soniox_transcribe(api_key: str, filename: str, data: bytes, language_hints: list[str],
                      terms: list[str], on_status) -> tuple[list[dict], float]:
    """Nahraje soubor do Sonioxu, počká na přepis a vrátí (tokeny, délka v minutách).

    Soubor i přepis se na serveru Sonioxu po stažení vždy smažou (i při chybě).
    """
    config = CreateTranscriptionConfig(
        language_hints=language_hints or None,
        enable_speaker_diarization=True,
        enable_language_identification=True,
        context=StructuredContext(terms=terms) if terms else None,
    )
    with SonioxClient(api_key=api_key, timeout_sec=600) as client:
        on_status("Nahrávám soubor do Sonioxu…")
        uploaded = client.files.upload(data, filename=filename)
        transcription_id = None
        try:
            job = client.stt.create(model=SONIOX_MODEL, file_id=uploaded.id, config=config)
            transcription_id = job.id
            started = time.monotonic()
            while job.status in ("queued", "processing"):
                waited = int(time.monotonic() - started)
                on_status(f"Soniox přepisuje… ({waited // 60} min {waited % 60:02d} s)")
                if waited > 3 * 3600:
                    raise TimeoutError("Přepis trvá déle než 3 hodiny, zkuste to později.")
                time.sleep(5)
                job = client.stt.get(transcription_id)
            if job.status != "completed":
                raise RuntimeError(f"Soniox hlásí chybu: {job.error_type}: {job.error_message}")
            transcript = client.stt.get_transcript(transcription_id)
            tokens = [t.model_dump() for t in transcript.tokens]
            minutes = (job.audio_duration_ms or 0) / 60_000
            return tokens, minutes
        finally:
            if transcription_id:
                client.stt.delete_if_exists(transcription_id)
            client.files.delete_if_exists(uploaded.id)


def tokens_to_segments(tokens: list[dict]) -> list[dict]:
    """Spojí tokeny do odstavců: nový odstavec při změně mluvčího nebo po ~minutě monologu."""
    segments: list[dict] = []
    for tok in tokens:
        if tok.get("translation_status") == "translation":
            continue
        speaker = str(tok.get("speaker") or "1")
        start = tok.get("start_ms") or 0
        cur = segments[-1] if segments else None
        new_par = (
            cur is None
            or cur["speaker"] != speaker
            or (start - cur["start_ms"] > MAX_SEGMENT_MS and cur["text"].rstrip()[-1:] in ".?!")
        )
        if new_par:
            segments.append({"speaker": speaker, "start_ms": start, "text": tok["text"].lstrip()})
        else:
            cur["text"] += tok["text"]
    for s in segments:
        s["text"] = re.sub(r"\s+", " ", s["text"]).strip()
    return [s for s in segments if s["text"]]


def fmt_time(ms: int) -> str:
    s = ms // 1000
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def speaker_name(sid: str, names: dict) -> str:
    return names.get(sid) or f"Mluvčí {sid}"


def render_transcript(segments: list[dict], names: dict, markdown: bool = False) -> str:
    lines = []
    for s in segments:
        who = speaker_name(s["speaker"], names)
        if markdown:
            lines.append(f"**[{fmt_time(s['start_ms'])}] {who}:** {s['text']}")
        else:
            lines.append(f"[{fmt_time(s['start_ms'])}] {who}: {s['text']}")
    return "\n\n".join(lines)


# Překlad si drží neutrální značky „S1:“, aby se jména dala měnit i po přeložení.
LABEL_RE = re.compile(r"^\[(\d\d:\d\d:\d\d)\] S(\w+):", re.MULTILINE)


def labeled_transcript(segments: list[dict]) -> str:
    return "\n\n".join(f"[{fmt_time(s['start_ms'])}] S{s['speaker']}: {s['text']}" for s in segments)


def render_translation(raw: str, names: dict, markdown: bool = False) -> str:
    def repl(m):
        who = speaker_name(m.group(2), names)
        return f"**[{m.group(1)}] {who}:**" if markdown else f"[{m.group(1)}] {who}:"
    return LABEL_RE.sub(repl, raw)


def translation_by_segment(raw: str) -> dict[tuple[str, str], str]:
    """Rozloží překlad na odstavce podle značky [čas] S<mluvčí>:."""
    out: dict[tuple[str, str], str] = {}
    matches = list(LABEL_RE.finditer(raw))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        out[(m.group(1), m.group(2))] = re.sub(r"\s+", " ", raw[m.end():end]).strip()
    return out


def render_combined(segments: list[dict], raw: str, names: dict, markdown: bool = False) -> str:
    """Dohromady: úsek originálu a hned pod ním jeho překlad."""
    tr = translation_by_segment(raw)
    blocks = []
    for s in segments:
        t = fmt_time(s["start_ms"])
        who = speaker_name(s["speaker"], names)
        translated = tr.get((t, s["speaker"]), "(překlad tohoto úseku chybí)")
        if markdown:
            blocks.append(f"**[{t}] {who}:** {s['text']}\n\n*{translated}*")
        else:
            blocks.append(f"[{t}] {who}: {s['text']}\n» {translated}")
    return "\n\n".join(blocks)


LAYOUTS = {"separate": "Zvlášť (přepis a překlad jako dva dokumenty)",
           "combined": "Dohromady (úsek originálu a pod ním překlad)"}


def current_layout() -> str:
    return os.getenv("LAYOUT", "separate") if os.getenv("LAYOUT") in LAYOUTS else "separate"


def transcript_documents(data: dict, names: dict) -> list[tuple[str, str, str, str]]:
    """Dokumenty podle zvoleného uspořádání: (název, soubor, text, markdown)."""
    segs, raw, src = data["segments"], data.get("translation_raw", ""), data["source_name"]
    if raw and current_layout() == "combined":
        return [(f"Přepis a překlad – {src}", "prepis_a_preklad",
                 render_combined(segs, raw, names), render_combined(segs, raw, names, True))]
    docs = [(f"Přepis – {src}", "prepis",
             render_transcript(segs, names), render_transcript(segs, names, True))]
    if raw:
        docs.append((f"Překlad – {src}", "preklad",
                     render_translation(raw, names), render_translation(raw, names, True)))
    return docs


# ======================================================================================
# Gemini: překlad a shrnutí
# ======================================================================================


def gemini_generate(api_key: str, model: str, system: str, text: str, temperature: float) -> str:
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model, contents=text,
        config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
    )
    if not resp.text:
        raise RuntimeError("Gemini vrátil prázdnou odpověď (možná ho zastavil bezpečnostní filtr).")
    return resp.text.strip()


def split_text(text: str, max_chars: int) -> list[str]:
    blocks, current = [], ""
    for para in text.split("\n\n"):
        if current and len(current) + len(para) + 2 > max_chars:
            blocks.append(current)
            current = ""
        current = f"{current}\n\n{para}" if current else para
    if current.strip():
        blocks.append(current)
    return blocks


def translate(api_key: str, model: str, labeled: str, target: str, progress) -> str:
    system = (
        f"Jsi profesionální překladatel. Přelož přepis rozhovoru do jazyka: {target}. "
        "Každý odstavec začíná značkou ve tvaru [hh:mm:ss] S1: – tyto značky ponech přesně beze změny "
        "a zachovej i rozdělení do odstavců. Pasáže, které už jsou v cílovém jazyce, ponech, jen oprav "
        "zjevné chyby přepisu. Zachovej jména a odborné pojmy, hovorové obraty převeď přirozeně. "
        "Vrať pouze překlad, bez komentářů."
    )
    blocks = split_text(labeled, TRANSLATE_CHUNK_CHARS)
    out = []
    for i, block in enumerate(blocks, start=1):
        progress(i, len(blocks))
        out.append(gemini_generate(api_key, model, system, block, 0.2))
    return "\n\n".join(out)


def summarize(api_key: str, model: str, text: str, template: str, out_lang: str) -> str:
    system = (
        "Jsi pečlivý asistent, který zpracovává přepisy nahrávek. Přepis obsahuje časové značky "
        "a jména mluvčích. Vycházej výhradně z přepisu, nic si nedomýšlej; přepis může obsahovat "
        f"chyby rozpoznávání řeči. Odpověz v jazyce: {out_lang}. Formátuj v Markdownu.\n\n"
        f"Úkol: {SUMMARY_TEMPLATES[template]}"
    )
    return gemini_generate(api_key, model, system, text, 0.3)


# ======================================================================================
# Export: Word (DOCX) a ukládání do složky vystupy
# ======================================================================================


def _add_runs(paragraph, text: str):
    """Převede **tučné** a *kurzívní* úseky na formátování ve Wordu."""
    for part in re.split(r"(\*\*.+?\*\*|(?<!\*)\*[^*\s][^*]*\*(?!\*))", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            paragraph.add_run(part[1:-1]).italic = True
        else:
            paragraph.add_run(part)


def markdown_to_docx(md: str, title: str) -> bytes:
    doc = Document()
    doc.add_heading(title, level=0)
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("|"):  # tabulka
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                ncols = max(len(r) for r in rows)
                table = doc.add_table(rows=len(rows), cols=ncols)
                table.style = "Table Grid"
                for r, row in enumerate(rows):
                    for c, cell in enumerate(row):
                        _add_runs(table.cell(r, c).paragraphs[0], cell)
            continue
        if m := re.match(r"^(#{1,4})\s+(.*)", stripped):
            doc.add_heading(m.group(2).replace("**", ""), level=min(len(m.group(1)), 4))
        elif m := re.match(r"^[-*]\s+\[[ xX]\]\s+(.*)", stripped):
            _add_runs(doc.add_paragraph(style="List Bullet"), "☐ " + m.group(1))
        elif m := re.match(r"^[-*]\s+(.*)", stripped):
            style = "List Bullet 2" if line.startswith(("  ", "\t")) else "List Bullet"
            _add_runs(doc.add_paragraph(style=style), m.group(1))
        elif m := re.match(r"^\d+[.)]\s+(.*)", stripped):
            _add_runs(doc.add_paragraph(style="List Number"), m.group(1))
        else:
            _add_runs(doc.add_paragraph(), stripped)
        i += 1
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def safe_name(text: str) -> str:
    text = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE).strip("_")
    return text[:60] or "nahravka"


def _write_atomic(path: Path, data: bytes):
    """Zapíše soubor najednou, aby Google Disk nikdy nesynchronizoval rozepsanou verzi."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def save_job(change: str = "all", summary_name: str = ""):
    """Uloží práci do složky přepisu. Volá se po každé změně.

    Kvůli práci z více počítačů se nejdřív načte verze na disku a přepíše se jen to,
    co se právě změnilo (change = "all" | "names" | "translation" | "summary").
    Shrnutí vytvořené mezitím na druhém počítači se tak neztratí.
    """
    s = st.session_state
    if not s.job_dir:
        return
    d = Path(s.job_dir)
    d.mkdir(parents=True, exist_ok=True)
    data_path = d / "data.json"
    mine = {
        "source_name": s.source_name, "minutes": s.minutes, "segments": s.segments,
        "speaker_names": s.speaker_names, "translation_raw": s.translation_raw,
        "translation_lang": s.translation_lang, "summaries": dict(s.summaries),
    }
    data = mine
    if change != "all" and data_path.exists():
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = mine
        if change == "names":
            data["speaker_names"] = mine["speaker_names"]
        elif change == "translation":
            data["translation_raw"] = mine["translation_raw"]
            data["translation_lang"] = mine["translation_lang"]
        elif change == "summary":
            data.setdefault("summaries", {})[summary_name] = mine["summaries"][summary_name]
        # do otevřené relace převezmeme i změny z druhého počítače
        s.speaker_names = data.get("speaker_names", {})
        s.translation_raw = data.get("translation_raw", "")
        s.translation_lang = data.get("translation_lang", "")
        s.summaries = data.get("summaries", {})
    _write_atomic(data_path, json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
    s.job_mtime = data_path.stat().st_mtime

    names = data.get("speaker_names", {})
    docs = transcript_documents(data, names)
    for stem in ("prepis", "preklad", "prepis_a_preklad"):  # smaž soubory jiného uspořádání
        if stem not in [doc[1] for doc in docs]:
            for ext in (".txt", ".docx"):
                (d / f"{stem}{ext}").unlink(missing_ok=True)
    for title, stem, txt, md in docs:
        _write_atomic(d / f"{stem}.txt", txt.encode("utf-8"))
        _write_atomic(d / f"{stem}.docx", markdown_to_docx(md, title))
    for name, text in data.get("summaries", {}).items():
        if change in ("all", "names") or name == summary_name:
            _write_atomic(d / f"shrnuti_{safe_name(name)}.md", text.encode("utf-8"))
            # Word verze se dobře čte v aplikaci Google Disk na mobilu
            _write_atomic(d / f"shrnuti_{safe_name(name)}.docx",
                          markdown_to_docx(text, f"{name} – {data['source_name']}"))


def load_job(folder: Path):
    data = json.loads((folder / "data.json").read_text(encoding="utf-8"))
    s = st.session_state
    s.job_dir = str(folder)
    s.source_name = data["source_name"]
    s.minutes = data.get("minutes", 0)
    s.segments = data["segments"]
    s.speaker_names = data.get("speaker_names", {})
    s.translation_raw = data.get("translation_raw", "")
    s.translation_lang = data.get("translation_lang", "")
    s.summaries = data.get("summaries", {})
    s.job_mtime = (folder / "data.json").stat().st_mtime
    for k in [k for k in s if str(k).startswith("spk_")]:
        del s[k]


def refresh_if_changed_elsewhere():
    """Když přepis mezitím změnil druhý počítač (přes Google Disk), načte novou verzi."""
    s = st.session_state
    if not s.job_dir:
        return
    data_path = Path(s.job_dir) / "data.json"
    try:
        if data_path.stat().st_mtime > s.job_mtime + 0.5:
            load_job(Path(s.job_dir))
            st.toast("Načtena novější verze z druhého zařízení.")
    except OSError:
        pass


def saved_jobs() -> list[Path]:
    out = output_dir()
    try:
        return sorted((p for p in out.iterdir() if (p / "data.json").exists()), reverse=True)
    except OSError:
        return []


def download_row(label: str, txt: str, md: str, base: str, key: str):
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ TXT", txt.encode("utf-8"), f"{base}.txt", "text/plain",
                       key=f"{key}_txt", use_container_width=True)
    c2.download_button("⬇️ Markdown", md.encode("utf-8"), f"{base}.md", "text/markdown",
                       key=f"{key}_md", use_container_width=True)
    c3.download_button("⬇️ Word", markdown_to_docx(md, label), f"{base}.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       key=f"{key}_docx", use_container_width=True)


# ======================================================================================
# Stav aplikace
# ======================================================================================

DEFAULTS = {"job_dir": "", "job_mtime": 0.0, "source_name": "", "minutes": 0.0, "segments": [],
            "speaker_names": {}, "translation_raw": "", "translation_lang": "", "summaries": {}}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

st.set_page_config(page_title="Transcriptor", page_icon="🎙️", layout="wide")
st.title("🎙️ Transcriptor")
st.caption("Přepis s určením mluvčích (Soniox) → překlad → shrnutí podle šablony (Gemini)")

# ======================================================================================
# Postranní panel
# ======================================================================================

with st.sidebar:
    st.header("🔑 Klíče")
    env_soniox = os.getenv("SONIOX_API_KEY", "")
    env_gemini = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    soniox_key = env_soniox or st.text_input("Soniox API klíč", type="password")
    gemini_key = env_gemini or st.text_input("Gemini API klíč", type="password")
    if env_soniox and env_gemini:
        st.success("Oba klíče načteny ze souboru .env")
    elif soniox_key and gemini_key:
        if st.button("💾 Zapamatovat klíče", use_container_width=True,
                     help="Uloží klíče do souboru .env vedle app.py, příště se načtou samy."):
            update_env({"SONIOX_API_KEY": soniox_key.strip(), "GEMINI_API_KEY": gemini_key.strip()})
            st.rerun()

    st.header("⚙️ Model Gemini")
    options = GEMINI_MODELS if DEFAULT_GEMINI in GEMINI_MODELS else [DEFAULT_GEMINI, *GEMINI_MODELS]
    gemini_model = st.selectbox("Pro překlad a shrnutí", options, label_visibility="collapsed")

    st.header("📂 Dřívější přepisy")
    with st.expander("Složka pro ukládání"):
        st.caption("Pro přístup z více počítačů a mobilu sem vložte cestu do složky Google Disku, "
                   "např. G:\\Můj disk\\Transcriptor. Na obou počítačích nastavte stejnou složku.")
        new_dir = st.text_input("Cesta ke složce", value=str(output_dir()))
        if st.button("Uložit složku", use_container_width=True):
            try:
                Path(new_dir.strip().strip('"')).mkdir(parents=True, exist_ok=True)
                update_env({"OUTPUT_DIR": new_dir.strip().strip('"')})
                st.rerun()
            except OSError as e:
                st.error(f"Složku nejde použít: {e}")
    jobs = saved_jobs()
    if jobs:
        pick = st.selectbox("Uložené", jobs, format_func=lambda p: p.name, label_visibility="collapsed")
        if st.button("Otevřít", use_container_width=True):
            load_job(pick)
            st.rerun()
    else:
        st.caption(f"Zatím nic. Přepisy se ukládají do: {output_dir()}")

    st.divider()
    if st.button("➕ Nová nahrávka", use_container_width=True):
        for k, v in DEFAULTS.items():
            st.session_state[k] = type(v)() if not isinstance(v, float) else 0.0
        for k in [k for k in st.session_state if str(k).startswith("spk_")]:
            del st.session_state[k]
        st.rerun()

# ======================================================================================
# 1. Přepis
# ======================================================================================

st.subheader("1. Nahrávka")
uploaded = st.file_uploader(
    f"Audio soubor (až {MAX_AUDIO_HOURS} hodin)",
    type=["mp3", "m4a", "wav", "ogg", "flac", "aac", "webm", "mp4", "opus", "amr", "aiff"],
)
c1, c2 = st.columns(2)
with c1:
    langs = st.multiselect("Jazyky v nahrávce", list(AUDIO_LANGUAGES), default=["Čeština", "Angličtina"],
                           help="Pomůže přesnosti. Mluví-li se jinak, Soniox jazyk stejně rozpozná.")
with c2:
    terms_raw = st.text_input("Jména a odborné pojmy (nepovinné, oddělte čárkou)",
                              help="Např. jména účastníků, firem, zkratky. Zlepší jejich zápis.")
c3, c4 = st.columns(2)
with c3:
    do_translate = st.checkbox("Rovnou přeložit", value=False,
                               help="Přeloží přepis pomocí Gemini. Jde to udělat i později.")
with c4:
    target_lang = st.selectbox("Do jazyka", TARGET_LANGUAGES, disabled=not do_translate)

if st.button("▶️ Spustit přepis", type="primary", disabled=uploaded is None):
    if not soniox_key:
        st.error("Chybí Soniox API klíč.")
        st.stop()
    if do_translate and not gemini_key:
        st.error("Pro překlad chybí Gemini API klíč.")
        st.stop()
    try:
        with st.status("Zpracovávám…", expanded=True) as status:
            line = st.empty()
            tokens, minutes = soniox_transcribe(
                soniox_key, uploaded.name, uploaded.getvalue(),
                [AUDIO_LANGUAGES[l] for l in langs],
                [t.strip() for t in terms_raw.split(",") if t.strip()],
                on_status=line.write,
            )
            segments = tokens_to_segments(tokens)
            if not segments:
                raise RuntimeError("Soniox v nahrávce nenašel žádnou řeč.")
            line.write(f"Přepsáno {minutes:.1f} min, cena ≈ {minutes / 60 * SONIOX_USD_PER_HOUR:.3f} USD.")

            s = st.session_state
            s.source_name = Path(uploaded.name).stem
            s.minutes = minutes
            s.segments = segments
            s.speaker_names = {}
            s.translation_raw = ""
            s.translation_lang = ""
            s.summaries = {}
            for k in [k for k in s if str(k).startswith("spk_")]:
                del s[k]
            s.job_dir = str(output_dir() / f"{datetime.now():%Y-%m-%d_%H%M}_{safe_name(s.source_name)}")
            save_job()  # zaplacený přepis je uložený na disku dřív, než začne překlad

            if do_translate:
                bar = st.progress(0.0, text="Překládám…")
                s.translation_raw = translate(
                    gemini_key, gemini_model, labeled_transcript(segments), target_lang,
                    lambda i, n: bar.progress((i - 1) / n, text=f"Překládám část {i} / {n}"))
                s.translation_lang = target_lang
                save_job("translation")
            status.update(label="Hotovo ✅", state="complete", expanded=False)
    except Exception as e:  # noqa: BLE001 – uživateli ukážeme jakoukoli chybu
        st.error(f"Zpracování selhalo: {e}")

# ======================================================================================
# Výsledky (čtou se jen ze session_state, takže přežijí jakékoli kliknutí)
# ======================================================================================

S = st.session_state
refresh_if_changed_elsewhere()
if not S.segments:
    st.info("Nahrajte audio soubor a klikněte na „Spustit přepis“.")
    st.stop()

st.divider()
st.markdown(f"### 📄 {S.source_name}  \n{S.minutes:.0f} min · uloženo v `{Path(S.job_dir).name}`")

# --- Jména mluvčích -------------------------------------------------------------------
speakers = sorted({seg["speaker"] for seg in S.segments}, key=lambda x: (len(x), x))
with st.expander(f"👥 Jména mluvčích ({len(speakers)})", expanded=len(S.speaker_names) == 0):
    st.caption("Přepište „Mluvčí 1“ apod. na skutečná jména. Ukázka pomůže poznat, kdo je kdo.")
    cols = st.columns(min(len(speakers), 3))
    for i, sid in enumerate(speakers):
        sample = next(seg for seg in S.segments if seg["speaker"] == sid and len(seg["text"]) > 30) \
            if any(seg["speaker"] == sid and len(seg["text"]) > 30 for seg in S.segments) \
            else next(seg for seg in S.segments if seg["speaker"] == sid)
        with cols[i % len(cols)]:
            st.text_input(f"Mluvčí {sid}", value=S.speaker_names.get(sid, ""),
                          placeholder=f"Mluvčí {sid}", key=f"spk_{sid}")
            st.caption(f"[{fmt_time(sample['start_ms'])}] „{sample['text'][:120]}…“")
    new_names = {sid: S.get(f"spk_{sid}", "").strip() for sid in speakers}
    new_names = {k: v for k, v in new_names.items() if v}
    if new_names != S.speaker_names:
        S.speaker_names = new_names
        save_job("names")

names = S.speaker_names
base = safe_name(S.source_name)

# --- 2. Přepis a překlad --------------------------------------------------------------
st.subheader("2. Přepis a překlad")
if S.translation_raw:
    layout_labels = list(LAYOUTS.values())
    chosen = st.radio("Uspořádání přepisu a překladu", layout_labels,
                      index=list(LAYOUTS).index(current_layout()), horizontal=True)
    chosen_key = next(k for k, v in LAYOUTS.items() if v == chosen)
    if chosen_key != current_layout():
        update_env({"LAYOUT": chosen_key})  # zapamatuje se i pro další nahrávky
        save_job("names")                   # přegeneruje soubory ve složce
        st.rerun()

docs = transcript_documents(
    {"segments": S.segments, "translation_raw": S.translation_raw, "source_name": S.source_name},
    names)
tab_labels = [title.split(" – ")[0] + (f" ({S.translation_lang})" if "řeklad" in title else "")
              for title, *_ in docs]
for tab, (title, stem, txt, md) in zip(st.tabs(tab_labels), docs):
    with tab:
        st.text_area(title, txt, height=400, label_visibility="collapsed")
        download_row(title, txt, md, f"{base}_{stem}", f"dl_{stem}")

with st.expander("🌍 " + ("Přeložit znovu do jiného jazyka" if S.translation_raw else "Přeložit přepis")):
    t1, t2 = st.columns([2, 1])
    later_lang = t1.selectbox("Cílový jazyk", TARGET_LANGUAGES, key="later_lang",
                              label_visibility="collapsed")
    if t2.button("Přeložit", use_container_width=True):
        if not gemini_key:
            st.error("Chybí Gemini API klíč.")
        else:
            try:
                bar = st.progress(0.0, text="Překládám…")
                S.translation_raw = translate(
                    gemini_key, gemini_model, labeled_transcript(S.segments), later_lang,
                    lambda i, n: bar.progress((i - 1) / n, text=f"Překládám část {i} / {n}"))
                S.translation_lang = later_lang
                save_job("translation")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Překlad selhal: {e}")

# --- 3. Shrnutí -----------------------------------------------------------------------
st.subheader("3. Shrnutí")
s1, s2, s3 = st.columns(3)
template = s1.selectbox("Šablona", list(SUMMARY_TEMPLATES))
summary_lang = s2.selectbox("Jazyk shrnutí", TARGET_LANGUAGES)
source_choice = s3.radio("Vycházet z", ["přepisu", "překladu"], horizontal=True,
                         disabled=not S.translation_raw)

if st.button("✨ Generovat shrnutí", type="primary"):
    if not gemini_key:
        st.error("Chybí Gemini API klíč.")
    else:
        text = (render_translation(S.translation_raw, names)
                if source_choice == "překladu" and S.translation_raw
                else render_transcript(S.segments, names))
        try:
            with st.spinner("Generuji shrnutí…"):
                S.summaries[template] = summarize(gemini_key, gemini_model, text, template, summary_lang)
            save_job("summary", template)
        except Exception as e:  # noqa: BLE001
            st.error(f"Shrnutí selhalo: {e}")

for name, summary in S.summaries.items():
    with st.expander(f"📝 {name}", expanded=(name == template)):
        st.markdown(summary)
        download_row(f"{name} – {S.source_name}", summary, summary,
                     f"{base}_{safe_name(name)}", f"dl_sum_{safe_name(name)}")
