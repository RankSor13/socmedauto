"""
post_love_stories_reel.py
==========================
Love & Relationship Stories Facebook REEL Poster — Animated Video Edition
Inspired by Boiling Waters PH style — anonymous relationship stories in Tagalog/Taglish.

Topics: Love, Cheating, Struggles, Advice, Hidden Desire, Confession, Heartbreak

Pipeline:
  1. Groq AI generates a realistic anonymous relationship story (Tagalog/Taglish)
  2. Draws a Boiling Waters-style slide set (dark bg + emotional photo + text overlay)
  3. Assembles into a vertical 9:16 animated video with lofi music
  4. Uploads to GitHub Release → posts to Facebook Page as a Reel

Required GitHub Secrets:
  FB_ACCESS_TOKEN  — Facebook Page Access Token (pages_manage_posts + publish_video)
  FB_PAGE_ID       — Your Facebook Page numeric ID
  GROQ_API_KEY     — Free at console.groq.com (Llama 3.3 70B)
  PAGE_NAME        — Your Facebook Page name/handle (e.g. "yourloveconfessions")
  GH_RELEASE_TOKEN — (auto-provided by GitHub Actions as GITHUB_TOKEN)

GitHub Actions dependencies:
  pip install requests Pillow "moviepy<2" numpy
"""

import os, sys, json, random, requests, re, time, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO

try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        concatenate_videoclips, ColorClip, VideoClip
    )
    import moviepy.video.fx.all as vfx
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
FB_PAGE_ID       = os.environ["FB_PAGE_ID"]
FB_ACCESS_TOKEN  = os.environ["FB_ACCESS_TOKEN"]
GH_RELEASE_TOKEN = os.environ.get("GH_RELEASE_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
PAGE_NAME        = os.environ.get("PAGE_NAME", "loveconfessionsPH")

# ── Canvas: vertical 9:16 for Reels
IMG_W, IMG_H = 1080, 1920
FB_BASE      = "https://graph.facebook.com/v21.0"

FONT_BOLD_URL  = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
FONT_REG_URL   = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf"
FONT_BOLD_PATH = "/tmp/Poppins-Bold.ttf"
FONT_REG_PATH  = "/tmp/Poppins-Regular.ttf"

# ── Video settings
SLIDE_DURATION = 4.5   # seconds per slide
FADE_DURATION  = 0.5   # crossfade between slides
FPS            = 30
ZOOM_AMOUNT    = 0.07  # Ken Burns zoom

# ── Background music
MUSIC_PATH       = "/tmp/bg_music.wav"
MUSIC_VOLUME     = 0.15
BEAT_SAMPLE_RATE = 44100

# ─────────────────────────────────────────────────────────────────────────────
# STORY CATEGORIES & DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────
CATEGORIES = {
    "LOVE":         {"rgb": (220,  60, 100), "emoji": "💗", "label": "LOVE STORY"},
    "CHEATING":     {"rgb": (200,  40,  40), "emoji": "🔥", "label": "CHEATING"},
    "STRUGGLES":    {"rgb": (130,  90, 200), "emoji": "😔", "label": "STRUGGLES"},
    "ADVICE":       {"rgb": ( 30, 160, 140), "emoji": "💬", "label": "ADVICE"},
    "HIDDEN_DESIRE":{"rgb": (180,  50, 160), "emoji": "🤫", "label": "HIDDEN DESIRE"},
    "CONFESSION":   {"rgb": (230, 130,  30), "emoji": "📝", "label": "CONFESSION"},
    "HEARTBREAK":   {"rgb": ( 80,  80, 200), "emoji": "💔", "label": "HEARTBREAK"},
}

# Colors
BG_DARK  = (10, 8, 20)     # near-black deep purple
BG_CARD  = (22, 14, 38)    # dark card
C_WHITE  = (255, 255, 255)
C_GRAY   = (200, 185, 220)
ANON_BG  = (230, 90, 60)   # orange-red for anonymous icon (Boiling Waters style)

HASHTAG_MAP = {
    "LOVE":          "#LoveStory #RelationshipGoals #TrueLove #KiligPH #PagtatamaanPH",
    "CHEATING":      "#CheatingStory #Infidelity #BreakUp #HindiAkoSulit #ToxicRelationship",
    "STRUGGLES":     "#RelationshipStruggles #SasakitinKaRinNiya #LongDistance #PagmamahalKo",
    "ADVICE":        "#RelationshipAdvice #LoveAdvice #KailangaMoMalaman #LoveTips",
    "HIDDEN_DESIRE": "#HiddenFeelings #SecretAdmirer #HiddenDesire #MahiwaganPagmamahal",
    "CONFESSION":    "#LoveConfession #Hugot #ConfessionPH #AnonymousConfession",
    "HEARTBREAK":    "#Heartbreak #Sakit #BreakUp #Heartbroken #MagpapalusogMuna",
}

MOOD_PRESETS = {
    "soft": {
        "bpm": 68, "minor": False,
        "kick_amp": 0.7, "snare_amp": 0.5,
        "chords": [[-9,-5,-2],[-14,-10,-7],[-12,-8,-5],[-17,-13,-10]],
    },
    "sad": {
        "bpm": 58, "minor": True,
        "kick_amp": 0.8, "snare_amp": 0.55,
        "chords": [[-12,-8,-5],[-17,-13,-10],[-19,-15,-12],[-14,-11,-7]],
    },
    "tense": {
        "bpm": 80, "minor": True,
        "kick_amp": 1.0, "snare_amp": 0.75,
        "chords": [[-12,-8,-5],[-7,-3,0],[-17,-13,-10],[-14,-11,-7]],
    },
    "hopeful": {
        "bpm": 76, "minor": False,
        "kick_amp": 0.85, "snare_amp": 0.6,
        "chords": [[-9,-5,-2],[-2,2,5],[0,4,7],[-5,-1,2]],
    },
}

CATEGORY_MOOD = {
    "LOVE":          "hopeful",
    "CHEATING":      "tense",
    "STRUGGLES":     "sad",
    "ADVICE":        "soft",
    "HIDDEN_DESIRE": "soft",
    "CONFESSION":    "hopeful",
    "HEARTBREAK":    "sad",
}

# Slide labels (Boiling Waters style)
SLIDE_LABELS = [
    "",                           # 0 — hook / headline
    "ANG NANGYARI 📖",            # 1 — what happened
    "NANG MALAMAN KO... 😱",      # 2 — the discovery
    "ANG NARAMDAMAN KO 💔",       # 3 — the feeling
    "ANG TANONG KO SA INYO 🙏",   # 4 — the question
    "HILING KO LANG... ✨",       # 5 — wish/advice
    "",                           # 6 — CTA
]

# ─────────────────────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────────────────────
def setup_fonts():
    for url, path in [(FONT_BOLD_URL, FONT_BOLD_PATH), (FONT_REG_URL, FONT_REG_PATH)]:
        if not os.path.exists(path):
            print(f"  Downloading font: {url}…")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"  Saved → {path}")


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD_PATH if bold else FONT_REG_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# MUSIC — pure-Python lofi beat generator
# ─────────────────────────────────────────────────────────────────────────────
def _note_freq(semitones_from_a4: float) -> float:
    return 440.0 * (2.0 ** (semitones_from_a4 / 12.0))

def _sine(freq, dur, sr, amp=1.0):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t)

def _envelope(n, attack=0.02, release=0.3):
    env = np.ones(n)
    a = max(1, int(n * attack))
    r = max(1, int(n * release))
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.minimum(env[-r:], np.linspace(1, 0, r))
    return env

def _lowpass(signal, strength=0.85):
    out = np.zeros_like(signal)
    out[0] = signal[0]
    for i in range(1, len(signal)):
        out[i] = strength * out[i-1] + (1 - strength) * signal[i]
    return out

def _kick(sr, dur=0.25):
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = np.linspace(150, 45, n)
    wave_ = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    return wave_ * np.exp(-t * 18) * 0.9

def _snare(sr, dur=0.18):
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    body = np.sin(2 * np.pi * 180 * t) * 0.3
    return (noise * 0.7 + body) * np.exp(-t * 14) * 0.6

def _hat(sr, dur=0.06):
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    return noise * np.exp(-t * 40) * 0.25

def _mix(base, addition, at_sample):
    end = min(at_sample + len(addition), len(base))
    seg = end - at_sample
    if seg > 0:
        base[at_sample:end] += addition[:seg]

def generate_lofi_beat(duration, path, mood="sad", sr=BEAT_SAMPLE_RATE):
    preset = MOOD_PRESETS.get(mood, MOOD_PRESETS["sad"])
    bpm = preset["bpm"]
    n_samples = int(sr * duration)
    mix = np.zeros(n_samples)
    beat_dur = 60.0 / bpm
    bar_dur  = beat_dur * 4
    chord_progression = preset["chords"]
    n_bars = max(1, int(math.ceil(duration / bar_dur)))
    for bar in range(n_bars):
        chord = chord_progression[bar % len(chord_progression)]
        start_sample = int(bar * bar_dur * sr)
        for semis in chord:
            freq = _note_freq(semis)
            tone = _sine(freq, bar_dur, sr, amp=0.10)
            tone *= _envelope(len(tone), attack=0.05, release=0.6)
            _mix(mix, tone, start_sample)
        for beat in range(4):
            beat_sample = start_sample + int(beat * beat_dur * sr)
            if beat in (0, 2):
                _mix(mix, _kick(sr) * preset["kick_amp"], beat_sample)
            if beat in (1, 3):
                _mix(mix, _snare(sr) * preset["snare_amp"], beat_sample)
            _mix(mix, _hat(sr), beat_sample + int(beat_dur * sr * 0.5))
    mix = mix[:n_samples]
    mix = _lowpass(mix, strength=0.65)
    # vinyl crackle
    pops = np.random.choice(n_samples, size=n_samples // 800, replace=False)
    crackle = np.zeros(n_samples)
    crackle[pops] = np.random.uniform(-1, 1, len(pops)) * 0.015
    mix += crackle
    peak = np.max(np.abs(mix)) or 1.0
    mix = (mix / peak) * 0.82
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path

def setup_music(duration=60.0, mood="sad"):
    try:
        print(f"  🎵 Generating lofi beat (mood: {mood})…")
        generate_lofi_beat(duration, MUSIC_PATH, mood=mood)
        print(f"  🎵 Beat ready!")
        return True
    except Exception as e:
        print(f"  ⚠️  Beat generator failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# STORY GENERATION — Groq Llama 3 (Tagalog/Taglish anonymous story)
# ─────────────────────────────────────────────────────────────────────────────

# Available story categories and their scenarios
STORY_CATEGORIES = list(CATEGORIES.keys())

CATEGORY_SCENARIOS = {
    "LOVE": [
        "We were best friends for 5 years before we finally got together",
        "Long distance relationship that survived everything",
        "She said yes after I confessed 3 times",
        "He remembered every little thing I told him months ago",
        "We broke up but found our way back to each other",
    ],
    "CHEATING": [
        "I found text messages on his/her phone",
        "My bestfriend told me the truth about my partner",
        "I caught them together at the place we used to go to",
        "They denied it even with proof in front of them",
        "I found out through social media",
    ],
    "STRUGGLES": [
        "Long distance relationship and losing communication",
        "Family does not approve of my partner",
        "Financial problems affecting the relationship",
        "Trust issues from past trauma",
        "We fight more than we used to lately",
    ],
    "ADVICE": [
        "Should I give my ex another chance?",
        "How do I know if someone truly loves me?",
        "Is it okay to still be friends with your ex?",
        "How do you move on from someone you still love?",
        "When is the right time to say 'I love you'?",
    ],
    "HIDDEN_DESIRE": [
        "I have feelings for my bestfriend but scared to ruin the friendship",
        "I still love my ex but they are already with someone new",
        "I fell for someone I should not have feelings for",
        "I want to tell them but I am afraid of rejection",
        "I dream about someone I can never be with",
    ],
    "CONFESSION": [
        "I have been pretending to be okay but I am not",
        "I regret letting them go — biggest mistake of my life",
        "I was the toxic one in the relationship and I am ashamed",
        "I still check their social media every day even after the breakup",
        "I sabotaged a good relationship because of my insecurities",
    ],
    "HEARTBREAK": [
        "They left without any explanation",
        "I was replaced immediately after the breakup",
        "We were planning a future together, now it is all gone",
        "Healing is harder than I thought it would be",
        "I lost my person and I do not know how to start over",
    ],
}

def generate_story_groq(category: str) -> dict | None:
    """Use Groq to generate a realistic anonymous Tagalog/Taglish love story."""
    scenario = random.choice(CATEGORY_SCENARIOS.get(category, CATEGORY_SCENARIOS["LOVE"]))
    cat_info = CATEGORIES[category]

    prompt = f"""You are writing for a Filipino Facebook page similar to "Boiling Waters PH" — a page where anonymous members share their real relationship stories, struggles, and confessions in Tagalog/Taglish.

Write an anonymous story for the category: **{category}** ({cat_info['label']})
Scenario hint: {scenario}

RULES:
- Write in natural Tagalog/Taglish mix (like how Filipinos actually text/write online)
- Sound like a real anonymous person sharing their story — raw, emotional, relatable
- Use "siya" (gender neutral) — do NOT specify gender unless it adds drama
- The story should feel real — not too formal, not fake
- Include ages like "(22F)" or "(25M)" at the start if it adds relatability (optional)
- Avoid using names — use "siya", "sila", "kaming dalawa", etc.

OUTPUT: Return ONLY a valid JSON object with these exact keys:
{{
  "headline": "Short punchy 1-2 line hook that makes people stop scrolling (max 80 chars, can be Tagalog or Taglish)",
  "slide_1_hook": "Same as headline but dramatic — the most attention-grabbing version",
  "slide_2_story": "What happened — the main story context (max 130 chars)",
  "slide_3_discovery": "The twist, discovery, or key moment (max 130 chars)",
  "slide_4_feeling": "How it felt — raw emotional reaction (max 130 chars)",
  "slide_5_question": "The question to the audience — ask for advice or opinion (max 130 chars)",
  "slide_6_cta": "Warm call to action — ask followers to share or comment (max 150 chars, can mention the page)",
  "full_story": "The full story in 3-5 sentences (Tagalog/Taglish) — this goes in the caption",
  "caption_question": "One relatable question to ask followers in the caption",
  "category": "{category}"
}}

Remember: Sound like a real Filipino sharing their pain/joy/confusion online. Be genuine, not theatrical."""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.85,
                "max_tokens": 900,
            },
            timeout=30,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return data
    except Exception as e:
        print(f"  ⚠️  Groq error: {e}")
    return None


def generate_story_fallback(category: str) -> dict:
    """Fallback story if Groq is unavailable."""
    scenario = random.choice(CATEGORY_SCENARIOS.get(category, CATEGORY_SCENARIOS["LOVE"]))
    return {
        "headline": "Hindi ko inakala na ganito magiging ending namin... 💔",
        "slide_1_hook": "Hindi ko inakala na ganito magiging ending namin... 💔",
        "slide_2_story": "Sabi niya mahal niya ako. Pero ang gawa niya ay kabaligtaran ng sinabi niya.",
        "slide_3_discovery": "Nalaman ko ang totoo sa pamamagitan ng isang tao na hindi ko inaasahan.",
        "slide_4_feeling": "Nasaktan ako. Hindi dahil sa inakala ko, kundi dahil alam ko nang matagal na.",
        "slide_5_question": "Tama ba na ibigay ko pa rin siya ng pagkakataon? O dapat ko na itong bitiwan?",
        "slide_6_cta": f"💬 Ibahagi ang inyong saloobin sa comments. Follow @{PAGE_NAME} para sa daily stories. 💗",
        "full_story": f"Anonymous member story. Scenario: {scenario}. Hindi ko inakala na darating ang araw na ito. Mahal ko siya pero parang hindi na sapat. Ang tanong ko — worth it pa ba ito?",
        "caption_question": "Ano ang magagawa mo kung ikaw ang nasa sitwasyong ito?",
        "category": category,
    }


def get_story(category: str = None) -> dict:
    """Get a story — randomly pick category if not specified."""
    if not category:
        category = random.choice(STORY_CATEGORIES)
    print(f"  📖 Category selected: {category}")
    if GROQ_API_KEY:
        print("  🤖 Generating story with Groq (Llama 3)…")
        story = generate_story_groq(category)
        if story:
            story["category"] = category
            return story
    print("  ✍️  Using fallback story…")
    return generate_story_fallback(category)


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND IMAGES — Unsplash (free, no API key needed)
# ─────────────────────────────────────────────────────────────────────────────
UNSPLASH_QUERIES = {
    "LOVE":          ["couple love romantic", "couple holding hands", "love couple sunset"],
    "CHEATING":      ["woman crying sad", "man looking away sad", "alone sad night"],
    "STRUGGLES":     ["person thinking sad window", "alone rain window", "sad woman phone"],
    "ADVICE":        ["friends talking coffee", "woman thinking", "couple conversation"],
    "HIDDEN_DESIRE": ["woman looking away dreaming", "person alone night city", "longing sad eyes"],
    "CONFESSION":    ["writing letter emotional", "person looking down", "candle dark room"],
    "HEARTBREAK":    ["woman crying alone", "broken heart rain", "person sad bench"],
}

def fetch_unsplash_photo(category: str) -> Image.Image | None:
    """Fetch a free photo from Unsplash (no API key needed via source.unsplash.com)."""
    queries = UNSPLASH_QUERIES.get(category, ["couple sad emotional"])
    query   = random.choice(queries)
    # Use Unsplash source (free, no key needed)
    url = f"https://source.unsplash.com/1080x1920/?{query.replace(' ', ',')}"
    try:
        print(f"  📷 Fetching photo: {query}…")
        r = requests.get(url, timeout=20, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        w, h = img.size
        if w < 400 or h < 400:
            return None
        print(f"  ✅ Photo loaded: {w}×{h}")
        return img
    except Exception as e:
        print(f"  ⚠️  Could not fetch photo: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE IMAGE GENERATION — Boiling Waters PH style
# ─────────────────────────────────────────────────────────────────────────────
def draw_rounded_rect(draw, x0, y0, x1, y1, r, fill, outline=None, width=2):
    draw.rectangle([x0+r, y0, x1-r, y1], fill=fill)
    draw.rectangle([x0, y0+r, x1, y1-r], fill=fill)
    draw.ellipse([x0, y0, x0+2*r, y0+2*r], fill=fill)
    draw.ellipse([x1-2*r, y0, x1, y0+2*r], fill=fill)
    draw.ellipse([x0, y1-2*r, x0+2*r, y1], fill=fill)
    draw.ellipse([x1-2*r, y1-2*r, x1, y1], fill=fill)
    if outline:
        draw.rectangle([x0+r, y0, x1-r, y1], outline=outline, width=width)
        draw.rectangle([x0, y0+r, x1, y1-r], outline=outline, width=width)


def draw_text_shadow(draw, xy, text, font, fill, shadow_offset=3, shadow_color=(0,0,0,160)):
    draw.text((xy[0]+shadow_offset, xy[1]+shadow_offset), text, font=font, fill=shadow_color)
    draw.text(xy, text, font=font, fill=fill)


def fit_text(draw, text, font_size, max_w, max_lines, bold=True):
    while font_size >= 28:
        font  = get_font(font_size, bold=bold)
        words = text.split()
        lines, cur = [], []
        for word in words:
            test = " ".join(cur + [word])
            if draw.textbbox((0,0), test, font=font)[2] > max_w and cur:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                cur.append(word)
        if cur:
            lines.append(" ".join(cur))
        if len(lines) <= max_lines:
            return font, lines
        font_size -= 4
    return get_font(28, bold=bold), lines


def make_photo_bg(photo: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop/resize photo to fill canvas."""
    src_w, src_h = photo.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    img_r = photo.resize((new_w, new_h), Image.LANCZOS)
    cx = (new_w - target_w) // 2
    cy = int((new_h - target_h) * 0.35)
    cy = max(0, min(cy, new_h - target_h))
    return img_r.crop((cx, cy, cx + target_w, cy + target_h))


def draw_anon_badge(draw, img, x, y, accent):
    """Draw the 'Anonymous member' badge — Boiling Waters style."""
    # Orange circle avatar with mask icon
    r = 36
    draw.ellipse([(x, y), (x+r*2, y+r*2)], fill=ANON_BG)
    # Simple person silhouette (circle head + body arc)
    head_r = 10
    hx, hy = x+r, y+r-6
    draw.ellipse([(hx-head_r, hy-head_r), (hx+head_r, hy+head_r)], fill=C_WHITE)
    draw.ellipse([(hx-16, hy+8), (hx+16, hy+28)], fill=C_WHITE)
    # Sunglass
    draw.rectangle([(hx-9, hy-4), (hx-2, hy+2)], fill=(50,30,30))
    draw.rectangle([(hx+2, hy-4), (hx+9, hy+2)], fill=(50,30,30))
    draw.line([(hx-2, hy-2), (hx+2, hy-2)], fill=(50,30,30), width=2)
    # Text
    anon_font = get_font(34, bold=False)
    draw.text((x+r*2+18, y+r//2), "Anonymous member", font=anon_font, fill=C_WHITE)


def create_slide(slide_text: str, idx: int, total: int,
                 category: str, label: str, photo: Image.Image | None) -> Image.Image:
    """Create a single Boiling Waters-style 1080×1920 slide."""
    cat    = CATEGORIES.get(category, CATEGORIES["LOVE"])
    accent = cat["rgb"]
    is_cta = idx == total - 1

    # Base: dark background
    img  = Image.new("RGB", (IMG_W, IMG_H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # ── Background photo with dark overlay
    if photo and not is_cta:
        bg = make_photo_bg(photo, IMG_W, IMG_H)
        bg = ImageEnhance.Brightness(bg).enhance(0.35)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
        img.paste(bg, (0, 0))
        # Gradient overlay (stronger at bottom for text readability)
        overlay = Image.new("RGBA", (IMG_W, IMG_H), (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        for y in range(IMG_H):
            # Dark at top and stronger at bottom
            alpha_top    = 80
            alpha_bottom = 200
            alpha = int(alpha_top + (alpha_bottom - alpha_top) * (y / IMG_H) ** 1.5)
            alpha = min(255, alpha)
            od.line([(0,y),(IMG_W,y)], fill=(0,0,0,alpha))
        img_rgba = img.convert("RGBA")
        img_rgba.alpha_composite(overlay)
        img = img_rgba.convert("RGB")
        draw = ImageDraw.Draw(img)

    # ── Top accent stripe
    draw.rectangle([(0,0),(IMG_W,12)], fill=accent)

    PAD = 60

    if not is_cta:
        # ── Anonymous member badge (Boiling Waters style) — top left
        draw_anon_badge(draw, img, PAD, 52, accent)

        # ── Slide counter top-right
        ctr_font = get_font(28, bold=False)
        draw.text((IMG_W-PAD, 66), f"{idx+1}/{total}",
                  font=ctr_font, anchor="rm", fill=C_GRAY)

        max_w = IMG_W - PAD*2
        center_y = IMG_H // 2

        if idx == 0:
            # HOOK SLIDE — Large dramatic headline
            font, lines = fit_text(draw, slide_text, 80, max_w, 5, bold=True)
            fs = font.size
            lh = fs + 22
            total_h = len(lines) * lh
            ty = center_y - total_h // 2 - 40

            for i, line in enumerate(lines):
                colour = accent if i == 0 else C_WHITE
                bw = draw.textbbox((0,0), line, font=font)[2]
                tx = (IMG_W - bw) // 2
                draw_text_shadow(draw, (tx, ty), line, font, colour,
                                 shadow_offset=5, shadow_color=(0,0,0,200))
                ty += lh

            # Accent underline
            draw.rectangle([(IMG_W//2-100, ty+16), (IMG_W//2+100, ty+22)], fill=accent)

        else:
            # CONTENT SLIDES — Label + body text
            if label:
                lbl_font = get_font(34)
                lbl_bbox = draw.textbbox((0,0), label, font=lbl_font)
                lbl_w    = lbl_bbox[2]
                lbl_x    = (IMG_W - lbl_w) // 2
                lbl_y    = center_y - 160
                draw.text((lbl_x, lbl_y), label, font=lbl_font, fill=accent)
                draw.rectangle([(lbl_x, lbl_y+lbl_bbox[3]+6),
                                (lbl_x+lbl_w, lbl_y+lbl_bbox[3]+11)], fill=accent)
                text_start_y = lbl_y + 90
            else:
                text_start_y = center_y - 100

            font, lines = fit_text(draw, slide_text, 62, max_w, 5, bold=True)
            fs = font.size
            lh = fs + 22
            total_h = len(lines) * lh
            ty = text_start_y

            for i, line in enumerate(lines):
                colour = C_WHITE if i > 0 else accent
                bw = draw.textbbox((0,0), line, font=font)[2]
                tx = (IMG_W - bw) // 2
                draw_text_shadow(draw, (tx, ty), line, font, colour,
                                 shadow_offset=4, shadow_color=(0,0,0,200))
                ty += lh

    else:
        # ── CTA SLIDE
        overlay = Image.new("RGBA", (IMG_W, IMG_H), (0,0,0,110))
        img_rgba = img.convert("RGBA")
        img_rgba.alpha_composite(overlay)
        img = img_rgba.convert("RGB")
        draw = ImageDraw.Draw(img)

        cy = IMG_H // 2 - 100

        # Heart icon
        hx, hy = IMG_W // 2, cy - 130
        heart_r = 70
        draw.ellipse([(hx-heart_r-5, hy-heart_r), (hx+5, hy+20)], fill=accent)
        draw.ellipse([(hx-5, hy-heart_r), (hx+heart_r+5, hy+20)], fill=accent)
        import math as _math
        pts = []
        for angle in range(0, 181, 5):
            rad = _math.radians(angle)
            px_ = hx + int(heart_r * _math.sin(rad) * 1.2)
            py_ = hy + 20 + int(heart_r * 1.1 * (1 - _math.cos(rad)) * 0.6)
            pts.append((px_, py_))
        if len(pts) >= 3:
            draw.polygon(pts, fill=accent)

        draw.text((IMG_W//2, cy+40), "FOLLOW FOR DAILY",
                  font=get_font(38, bold=False), anchor="mm", fill=C_GRAY)
        draw.text((IMG_W//2, cy+115), "LOVE STORIES",
                  font=get_font(80), anchor="mm", fill=C_WHITE)
        draw.text((IMG_W//2, cy+215), f"@{PAGE_NAME}",
                  font=get_font(52), anchor="mm", fill=accent)
        draw.rectangle([(200, cy+265), (IMG_W-200, cy+272)], fill=accent)

        draw.text((IMG_W//2, cy+330),
                  "💗 I-share sa taong kailangan mabasa ito",
                  font=get_font(36, bold=False), anchor="mm", fill=C_GRAY)
        draw.text((IMG_W//2, cy+390),
                  "💬 I-comment ang inyong saloobin",
                  font=get_font(34, bold=False), anchor="mm", fill=C_GRAY)
        draw.text((IMG_W//2, IMG_H-150),
                  "Para sa inyong mga kwento at tanong:",
                  font=get_font(30, bold=False), anchor="mm", fill=C_GRAY)
        draw.text((IMG_W//2, IMG_H-100),
                  f"Message us at @{PAGE_NAME} 💗",
                  font=get_font(30, bold=False), anchor="mm", fill=accent)

    # ── Bottom branding bar
    draw.rectangle([(0, IMG_H-80), (IMG_W, IMG_H)], fill=BG_CARD)
    draw.rectangle([(0, IMG_H-80), (IMG_W, IMG_H-78)], fill=accent)
    draw.text((IMG_W//2, IMG_H-40), f"@{PAGE_NAME}",
              font=get_font(30, bold=False), anchor="mm", fill=C_GRAY)

    # Category pill (top-right area, smaller)
    if not is_cta:
        pill_font = get_font(28)
        pill_text = f"{cat['emoji']} {cat['label']}"
        pill_bbox = draw.textbbox((0,0), pill_text, font=pill_font)
        pw = pill_bbox[2] + 36
        ph = 50
        px = IMG_W - PAD - pw
        py = 50
        draw_rounded_rect(draw, px, py, px+pw, py+ph, 10, accent)
        draw.text((px+18, py+11), pill_text, font=pill_font, fill=C_WHITE)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# KEN BURNS ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
def make_ken_burns_clip(pil_img: Image.Image, duration: float, zoom_in: bool = True):
    img_array = np.array(pil_img)
    h, w = img_array.shape[:2]
    zoom_start = 1.0
    zoom_end   = 1.0 + ZOOM_AMOUNT
    if not zoom_in:
        zoom_start, zoom_end = zoom_end, zoom_start

    def make_frame(t):
        progress = t / duration
        scale    = zoom_start + (zoom_end - zoom_start) * progress
        crop_w = int(w / scale)
        crop_h = int(h / scale)
        offset_x = int((w - crop_w) * 0.5)
        offset_y = int((h - crop_h) * 0.5)
        offset_x = max(0, min(offset_x, w - crop_w))
        offset_y = max(0, min(offset_y, h - crop_h))
        cropped = img_array[offset_y:offset_y+crop_h, offset_x:offset_x+crop_w]
        return np.array(Image.fromarray(cropped).resize((w, h), Image.LANCZOS))

    return VideoClip(make_frame, duration=duration)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────
def build_reel(images: list, output_path: str, has_music: bool) -> str:
    print(f"\n🎬 Assembling {len(images)} slides into video…")
    clips = []
    for i, pil_img in enumerate(images):
        clip = make_ken_burns_clip(pil_img, SLIDE_DURATION, zoom_in=(i % 2 == 0))
        clip = clip.set_fps(FPS)
        if i > 0:
            clip = clip.crossfadein(FADE_DURATION)
        clips.append(clip)
        print(f"   Slide {i+1}/{len(images)} animated ✓")

    video = concatenate_videoclips(clips, method="compose", padding=-FADE_DURATION)

    if has_music and os.path.exists(MUSIC_PATH):
        try:
            print("  🎵 Mixing background beat…")
            audio = AudioFileClip(MUSIC_PATH)
            total_dur = video.duration
            if audio.duration < total_dur:
                from moviepy.editor import concatenate_audioclips
                loops_needed = math.ceil(total_dur / audio.duration)
                audio = concatenate_audioclips([audio] * loops_needed)
            audio = audio.subclip(0, total_dur).volumex(MUSIC_VOLUME)
            video = video.set_audio(audio)
            print("  ✅ Music mixed in!")
        except Exception as e:
            print(f"  ⚠️  Music mix failed: {e}")

    print(f"\n🎞️  Rendering MP4 → {output_path}…")
    video.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        preset="medium",
        ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
        logger=None,
    )
    print(f"  ✅ Video rendered! Size: {os.path.getsize(output_path)/1024/1024:.1f} MB")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB RELEASE VIDEO HOSTING (throwaway — deleted after FB upload)
# ─────────────────────────────────────────────────────────────────────────────
def upload_video_to_github_release(video_path: str) -> tuple:
    repo  = os.environ["GITHUB_REPOSITORY"]
    token = GH_RELEASE_TOKEN
    if not token:
        raise RuntimeError("No GH_RELEASE_TOKEN or GITHUB_TOKEN available.")

    size_mb = os.path.getsize(video_path) / 1024 / 1024
    print(f"  ☁️  Uploading video ({size_mb:.1f} MB) to GitHub Release…")

    tag = f"love-reel-{int(time.time())}"
    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"tag_name": tag, "name": tag,
              "body": "Auto-generated Love Stories Reel — safe to delete.", "draft": False},
        timeout=30,
    )
    r.raise_for_status()
    release = r.json()
    print(f"  📦 Release created: {tag} (id={release['id']})")

    upload_url = release["upload_url"].split("{")[0]
    filename   = os.path.basename(video_path)
    with open(video_path, "rb") as f:
        data = f.read()
    r2 = requests.post(
        upload_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "Content-Type": "video/mp4"},
        params={"name": filename},
        data=data,
        timeout=180,
    )
    r2.raise_for_status()
    url = r2.json()["browser_download_url"]
    print(f"  ✅ Video hosted at: {url}")
    return url, release["id"]


def delete_github_release(release_id: int, repo: str, token: str):
    try:
        requests.delete(
            f"https://api.github.com/repos/{repo}/releases/{release_id}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=30,
        )
    except Exception as e:
        print(f"  ⚠️  Could not clean up release: {e} (not fatal)")


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK GRAPH API
# ─────────────────────────────────────────────────────────────────────────────
def fb_post_request(path, **params):
    r = requests.post(
        f"{FB_BASE}/{path}",
        params={"access_token": FB_ACCESS_TOKEN, **params},
        timeout=60,
    )
    if not r.ok:
        print(f"  FB API error: {r.status_code} — {r.text}")
    r.raise_for_status()
    return r.json()

def fb_get_request(path, **params):
    r = requests.get(
        f"{FB_BASE}/{path}",
        params={"access_token": FB_ACCESS_TOKEN, **params},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def upload_video_to_page(video_url: str, description: str) -> str:
    data = fb_post_request(f"{FB_PAGE_ID}/videos",
                           file_url=video_url, description=description)
    return data["id"]

def wait_for_video_ready(video_id, retries=24, interval=10):
    for attempt in range(retries):
        status = fb_get_request(video_id, fields="status").get("status", {})
        video_status = status.get("video_status", "unknown")
        print(f"    Video {video_id}: {video_status}  (attempt {attempt+1}/{retries})")
        if video_status == "ready":
            return
        if video_status == "error":
            raise RuntimeError(f"Video {video_id} errored during processing.")
        time.sleep(interval)
    print("    ⚠️  Didn't confirm 'ready' in time — continuing.")


# ─────────────────────────────────────────────────────────────────────────────
# CAPTION BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_caption(story: dict) -> str:
    cat      = story.get("category", "LOVE")
    cat_info = CATEGORIES.get(cat, CATEGORIES["LOVE"])
    tags     = HASHTAG_MAP.get(cat, "#LoveStory #RelationshipPH")
    headline = story.get("headline", "")
    full_story = story.get("full_story", "")
    question   = story.get("caption_question", "Ano ang masasabi mo?")

    return (
        f"{cat_info['emoji']} {headline}\n\n"
        f"─────────────────────────\n"
        f"{full_story}\n"
        f"─────────────────────────\n\n"
        f"💬 {question}\n\n"
        f"📤 I-share ito sa taong kailangan mabasa ito ngayon.\n"
        f"💗 I-follow ang @{PAGE_NAME} para sa daily love stories, confessions, at advice!\n"
        f"📩 Magpadala ng inyong kwento sa aming inbox — lahat ay anonymous.\n\n"
        f"{tags} #AnonymousPH #LoveStoriesPH #RelationshipPH #HugotPH #ConfessionPH"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  💗 Love Stories Facebook REEL Bot — Boiling Waters Style")
    print("=" * 60)

    if not MOVIEPY_OK:
        print("❌ moviepy is not installed! Run: pip install moviepy numpy")
        sys.exit(1)

    print("\n📦 Setting up fonts…")
    setup_fonts()

    # ── Generate story
    print("\n📖 Generating anonymous love story…")
    story    = get_story()
    category = story.get("category", "LOVE")
    mood     = CATEGORY_MOOD.get(category, "sad")

    print(f"\n🎯 Story generated:")
    print(f"   Category : {category}")
    print(f"   Headline : {story.get('headline', '')[:80]}")

    # ── Music
    est_duration = len(SLIDE_LABELS) * SLIDE_DURATION + 2.0
    print(f"\n🎵 Setting up background beat (mood: {mood})…")
    has_music = setup_music(duration=est_duration, mood=mood)

    # ── Background photo
    print("\n📷 Fetching background photo…")
    photo = fetch_unsplash_photo(category)

    # ── Build slides
    slide_content = [
        story.get("slide_1_hook", story.get("headline", "")),      # 0 — Hook
        story.get("slide_2_story", ""),                             # 1
        story.get("slide_3_discovery", ""),                         # 2
        story.get("slide_4_feeling", ""),                           # 3
        story.get("slide_5_question", ""),                          # 4
        story.get("slide_6_cta",
                  f"💗 Follow @{PAGE_NAME} for daily stories!"),   # 5
        f"Follow @{PAGE_NAME} 💗",                                  # 6 — CTA slide
    ]

    print("\n🎨 Creating slides (1080×1920)…")
    images = []
    for i, text in enumerate(slide_content):
        label = SLIDE_LABELS[i] if i < len(SLIDE_LABELS) else ""
        img   = create_slide(text, i, len(slide_content), category, label, photo)
        images.append(img)
        print(f"   Slide {i+1}/{len(slide_content)} ✓")

    # ── Render video
    output_path = "/tmp/love_stories_reel.mp4"
    build_reel(images, output_path, has_music)

    # ── Upload to GitHub Release (temp hosting)
    print("\n☁️  Uploading video…")
    video_url, release_id = upload_video_to_github_release(output_path)

    # ── Build caption
    caption = build_caption(story)

    # ── Post to Facebook
    print("\n📱 Posting to Facebook Page…")
    video_id = upload_video_to_page(video_url, caption)
    print(f"   Video ID: {video_id}")

    print("\n⏳ Waiting for video to process…")
    wait_for_video_ready(video_id, retries=24, interval=10)

    # ── Clean up GitHub Release
    print("\n🧹 Cleaning up GitHub Release…")
    repo  = os.environ["GITHUB_REPOSITORY"]
    delete_github_release(release_id, repo, GH_RELEASE_TOKEN)

    print(f"\n✅ SUCCESS! Love Story Reel posted to Facebook! 💗 Video ID: {video_id}")


if __name__ == "__main__":
    main()
