"""
post_love_stories_reel.py
==========================
Love Stories Facebook REEL Poster — Boiling Waters PH Style
Static slides (no zoom/animation) → stitched into a Reel video

Template mirrors the Boiling Waters PH design:
  • Dark moody background photo + gradient overlay
  • "Anonymous member" badge — top left (orange circle + spy icon)
  • Large bold-italic headline (the hook)
  • Smaller body story text below
  • Bottom-left: cactus icon + "Featured from <community>"
  • Bottom-right: page logo circle + page name

Required GitHub Secrets:
  FB_PAGE_ID        — Facebook Page numeric ID
  FB_ACCESS_TOKEN   — Page Access Token (pages_manage_posts + publish_video)
  GROQ_API_KEY      — Free at console.groq.com
  PAGE_NAME         — Your page handle, e.g. "LoveConfessionsPH"

Optional Secrets:
  COMMUNITY_NAME    — Community/group name, defaults to "<PAGE_NAME> Community"

GitHub Actions pip install line:
  pip install requests Pillow "moviepy<2" numpy
"""

import os, sys, json, random, requests, re, time, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO

try:
    from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
    from moviepy.audio.fx.all import audio_loop
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
PIXABAY_API_KEY  = os.environ.get("PIXABAY_API_KEY", "").strip()
PAGE_NAME        = os.environ.get("PAGE_NAME", "LoveConfessionsPH")
COMMUNITY_NAME   = os.environ.get("COMMUNITY_NAME", f"{PAGE_NAME} Community")

IMG_W, IMG_H    = 1080, 1920
FB_BASE         = "https://graph.facebook.com/v21.0"
OUTPUT_PATH     = "/tmp/love_story_reel.mp4"

FONT_BOLD_PATH      = "/tmp/Poppins-Bold.ttf"
FONT_BOLDITALIC_PATH= "/tmp/Poppins-BoldItalic.ttf"
FONT_REG_PATH       = "/tmp/Poppins-Regular.ttf"

SLIDE_DURATION  = 5.0   # seconds per static slide
FPS             = 24

# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND MUSIC
# ─────────────────────────────────────────────────────────────────────────────
# Pixabay has no public Music API (their REST API only covers images/videos),
# so auto-fetching music live isn't reliable. Instead: drop a few royalty-free
# MP3s (downloaded once, manually, from pixabay.com/music — totally within
# their terms since a human clicked their own Download button) into these
# folders, and the bot will pick one at random per post, matched to the mood.
MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "music")

# category -> mood folder name (assets/music/<mood>/*.mp3)
CATEGORY_MUSIC_MOOD = {
    "LOVE STORY":    "romantic",
    "CHEATING":      "heartbreak",
    "STRUGGLES":     "melancholy",
    "ADVICE":        "hopeful",
    "HIDDEN DESIRE": "dramatic",
    "CONFESSION":    "dramatic",
    "HEARTBREAK":    "heartbreak",
    "AGE GAP":       "romantic",
    "COUSIN LOVE":   "dramatic",
}

MUSIC_VOLUME = 0.35   # keep it subtle — this is background music, not the main event
MUSIC_FADE   = 1.0    # seconds of fade in / fade out

# Brand colors (Boiling Waters style)
ANON_ORANGE     = (220, 95, 35)
C_WHITE         = (255, 255, 255)
C_OFFWHITE      = (240, 235, 230)
C_MUTED         = (185, 175, 165)
C_DARK_BG       = (15,  12,  10)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LoveStoriesBot/1.0)"}

# ─────────────────────────────────────────────────────────────────────────────
# FAKE NAMES — realistic Filipino first names + censored surname
# ─────────────────────────────────────────────────────────────────────────────
FAKE_NAMES_FEMALE = [
    "Jenny", "Ana", "Maria", "Claire", "Nica",
    "Bea", "Trisha", "Len", "Sheila", "Karla",
    "Rhea", "Angel", "Mika", "Diane", "Joanne",
    "Liza", "Camille", "Rica", "Jessa", "Nina",
]
FAKE_NAMES_MALE = [
    "John", "Mark", "Carlo", "Jed", "Ken",
    "Paolo", "Nico", "Renz", "Adrian", "Franz",
    "Bryan", "Dan", "Kevin", "Arvin", "Gab",
    "Luis", "Ryan", "Dino", "Raf", "Jomar",
]
FAKE_SURNAMES = [
    "R", "S", "M", "D", "L",
    "C", "T", "B", "G", "V",
]

def get_fake_name(gender: str = "female") -> str:
    """Return a fake name like 'Jenny R*****' for the badge."""
    if gender == "male":
        first = random.choice(FAKE_NAMES_MALE)
    else:
        first = random.choice(FAKE_NAMES_FEMALE)
    surname_initial = random.choice(FAKE_SURNAMES)
    return f"{first} {surname_initial}*****"

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
CATEGORIES = [
    "LOVE STORY",
    "CHEATING",
    "STRUGGLES",
    "ADVICE",
    "HIDDEN DESIRE",
    "CONFESSION",
    "HEARTBREAK",
    "AGE GAP",
    "COUSIN LOVE",
]

CATEGORY_HASHTAGS = {
    "LOVE STORY":    "#LoveStory #Pagmamahal #RelationshipGoals #LoveConfessionsPH #TotooNgPuso",
    "CHEATING":      "#Cheating #Kabit #Infidelity #LoveAndPain #RealTalk #Pagtataksil",
    "STRUGGLES":     "#RelationshipStruggles #LDR #LoveHurts #MahalKitaPeroBakit #BagalKo",
    "ADVICE":        "#RelationshipAdvice #LoveAdvice #TanongSaInyo #HelpMe #SabihinMo",
    "HIDDEN DESIRE": "#HiddenDesire #SecretFeeling #NaramdamanKo #HindiKoMasabi #Gusto",
    "CONFESSION":    "#Confession #Pagtatapat #AnonymousStory #LoveConfession #Totoo",
    "HEARTBREAK":    "#Heartbreak #SakitNgPuso #MovingOn #LoveHurts #Masakit #Nawala",
    "AGE GAP":       "#AgeGap #AgeGapLove #OlderAndYounger #LoveHasNoAge #AgeIsJustANumber #PagmamahalNaWalangHangganan",
    "COUSIN LOVE":   "#CousinLove #ForbiddenLove #PinaghindilangPagmamahal #SecretFeeling #HiddenHeart #TabooLove",
}

# Pixabay search queries per category — Asian people, slightly blurred bg
# Format: list of queries to try in order (fallback if first returns nothing)
# Split by gender so we can pick "pretty woman" or "handsome man" depending on the story.
CATEGORY_PHOTO_KEYWORDS_FEMALE = {
    "LOVE STORY":    ["korean couple romantic", "asian couple love", "japanese couple"],
    "CHEATING":      ["asian beautiful woman sad", "korean woman alone sad", "vietnamese woman sad"],
    "STRUGGLES":     ["asian woman thinking", "korean woman pensive", "chinese woman melancholy"],
    "ADVICE":        ["japanese beautiful woman", "asian woman coffee thinking", "korean woman contemplating"],
    "HIDDEN DESIRE": ["vietnamese beautiful woman", "asian woman mysterious", "korean beautiful woman"],
    "CONFESSION":    ["asian woman writing", "korean woman diary", "japanese woman letter"],
    "HEARTBREAK":    ["asian woman crying", "korean woman heartbreak", "chinese woman tears"],
    "AGE GAP":       ["asian couple age difference", "older man younger woman asian", "korean couple romantic"],
    "COUSIN LOVE":   ["asian woman secret love", "korean woman hidden feelings", "vietnamese woman thinking"],
}

CATEGORY_PHOTO_KEYWORDS_MALE = {
    "LOVE STORY":    ["korean couple romantic", "asian couple love", "japanese couple"],
    "CHEATING":      ["asian handsome man sad", "korean man alone sad", "vietnamese man serious"],
    "STRUGGLES":     ["asian man thinking", "korean man pensive", "japanese man tired"],
    "ADVICE":        ["japanese handsome man", "asian man coffee thinking", "korean man contemplating"],
    "HIDDEN DESIRE": ["vietnamese handsome man", "asian man mysterious", "korean handsome man"],
    "CONFESSION":    ["asian man writing", "korean man diary", "japanese man letter"],
    "HEARTBREAK":    ["asian man heartbreak", "korean man sad", "chinese man alone"],
    "AGE GAP":       ["asian couple age difference", "older woman younger man asian", "korean couple romantic"],
    "COUSIN LOVE":   ["asian man secret love", "korean man hidden feelings", "vietnamese man thinking"],
}

# Backwards-compat alias (some helper code/tests may still reference the old name)
CATEGORY_PHOTO_KEYWORDS = CATEGORY_PHOTO_KEYWORDS_FEMALE

# Categories that are always a couple shot regardless of gender roll
COUPLE_CATEGORIES = {"LOVE STORY", "AGE GAP"}

# Nationality pool to rotate through for variety
ASIAN_NATIONALITIES = ["korean", "japanese", "vietnamese", "chinese", "asian"]

# Blur radius for background — high enough to obscure detail but keep silhouette
BG_BLUR_RADIUS = 6

# ─────────────────────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────────────────────
FONT_URLS = [
    ("https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",       FONT_BOLD_PATH),
    ("https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-BoldItalic.ttf", FONT_BOLDITALIC_PATH),
    ("https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf",    FONT_REG_PATH),
]

def setup_fonts():
    for url, path in FONT_URLS:
        if not os.path.exists(path):
            print(f"  Downloading font: {url} …")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"  Saved → {path}")


def get_font(size: int, bold: bool = True, italic: bool = False) -> ImageFont.FreeTypeFont:
    if bold and italic:
        path = FONT_BOLDITALIC_PATH
    elif bold:
        path = FONT_BOLD_PATH
    else:
        path = FONT_REG_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# TEXT UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)
    for word in words:
        test = (current + " " + word).strip()
        w = d.textlength(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text_with_shadow(draw: ImageDraw, text: str, x: int, y: int,
                          font, fill=(255, 255, 255),
                          shadow_offset: int = 3, shadow_color=(0, 0, 0, 180)):
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font,
              fill=(shadow_color[0], shadow_color[1], shadow_color[2]))
    draw.text((x, y), text, font=font, fill=fill)


# ─────────────────────────────────────────────────────────────────────────────
# DRAW HELPER: Anonymous Member Badge
# ─────────────────────────────────────────────────────────────────────────────
def draw_anon_badge(draw: ImageDraw, x: int, y: int, fake_name: str = ""):
    """
    Draw the orange circle + incognito spy icon + "Anonymous member" text
    + fake name below (e.g. "Jenny R*****").
    (x, y) = top-left corner of the badge circle.
    """
    r = 50  # circle radius
    cx = x + r
    cy = y + r

    # Orange filled circle
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=ANON_ORANGE)

    # ── Spy/incognito icon (white) inside orange circle ──
    # Hat crown (rectangle)
    hat_top    = cy - r + 12
    hat_bottom = cy - 10
    hat_lx     = cx - 22
    hat_rx     = cx + 22
    draw.rectangle([(hat_lx + 4, hat_top), (hat_rx - 4, hat_bottom)], fill=C_WHITE)

    # Hat brim (wider rectangle below crown)
    brim_y = hat_bottom
    draw.rectangle([(hat_lx, brim_y), (hat_rx, brim_y + 10)], fill=C_WHITE)

    # Face oval
    face_top = brim_y + 6
    face_bot = cy + r - 16
    face_lx  = cx - 17
    face_rx  = cx + 17
    draw.ellipse([(face_lx, face_top), (face_rx, face_bot)], fill=C_WHITE)

    # Glasses: two small ovals on the face (orange cutout to look like glasses)
    g_cy  = face_top + 13
    g_r_x = 8
    g_r_y = 6
    # Left glass
    draw.ellipse([(cx - 18, g_cy - g_r_y), (cx - 18 + g_r_x * 2, g_cy + g_r_y)],
                 fill=ANON_ORANGE)
    # Right glass
    draw.ellipse([(cx + 2, g_cy - g_r_y), (cx + 2 + g_r_x * 2, g_cy + g_r_y)],
                 fill=ANON_ORANGE)
    # Bridge between glasses
    draw.rectangle([(cx - 2, g_cy - 2), (cx + 2, g_cy + 2)], fill=ANON_ORANGE)

    # ── "Anonymous member" text (top line) ──
    text_x = cx + r + 22
    font_main = get_font(36, bold=False)
    draw.text((text_x, cy - 14), "Anonymous member",
              font=font_main, anchor="lm", fill=C_WHITE)

    # ── Fake name text (bottom line, slightly muted) ──
    if fake_name:
        font_name = get_font(30, bold=True)
        draw.text((text_x, cy + 22), fake_name,
                  font=font_name, anchor="lm", fill=C_OFFWHITE)


# ─────────────────────────────────────────────────────────────────────────────
# DRAW HELPER: Simple Cactus Icon
# ─────────────────────────────────────────────────────────────────────────────
def draw_cactus(draw: ImageDraw, x: int, y: int, size: int = 55):
    """Draw a simple outline cactus icon."""
    s = size
    cx = x + s // 2
    col = C_MUTED

    # Main stem (tall thin rectangle)
    stem_w = s // 5
    draw.rounded_rectangle(
        [(cx - stem_w, y), (cx + stem_w, y + s)],
        radius=stem_w, outline=col, width=3
    )
    # Left arm
    arm_y = y + s * 2 // 5
    arm_w = stem_w
    draw.rounded_rectangle(
        [(cx - s // 2, arm_y - arm_w), (cx - stem_w, arm_y + arm_w * 2)],
        radius=arm_w, outline=col, width=3
    )
    draw.rounded_rectangle(
        [(cx - s // 2 - arm_w, arm_y - s // 5), (cx - s // 2 + arm_w, arm_y - arm_w)],
        radius=arm_w, outline=col, width=3
    )
    # Right arm
    draw.rounded_rectangle(
        [(cx + stem_w, arm_y - arm_w), (cx + s // 2, arm_y + arm_w * 2)],
        radius=arm_w, outline=col, width=3
    )
    draw.rounded_rectangle(
        [(cx + s // 2 - arm_w, arm_y - s // 5), (cx + s // 2 + arm_w, arm_y - arm_w)],
        radius=arm_w, outline=col, width=3
    )


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND PHOTO
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_pixabay_photo(query: str) -> Image.Image | None:
    """
    Search Pixabay for a vertical photo matching `query`.
    Returns a PIL Image (1080×1920) or None on failure.
    Picks randomly from top results for variety.
    """
    if not PIXABAY_API_KEY:
        print("  ⚠️  PIXABAY_API_KEY is empty/not set — skipping Pixabay fetch "
              "(this is why you get the plain dark background instead of a photo).")
        return None
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key":          PIXABAY_API_KEY,
                "q":            query,
                "image_type":   "photo",
                "orientation":  "vertical",
                "per_page":     20,
                "safesearch":   "true",
                "min_width":    720,
                "min_height":   1080,
            },
            timeout=20,
        )
        if not r.ok:
            print(f"  ⚠️  Pixabay API error {r.status_code} for '{query}': {r.text[:200]}")
            return None
        hits = r.json().get("hits", [])
        if not hits:
            print(f"  ⚠️  Pixabay: no results for '{query}'")
            return None

        # Pick a random result from top hits for variety
        hit = random.choice(hits[:15])
        img_url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not img_url:
            return None

        img_r = requests.get(img_url, headers=HEADERS, timeout=20)
        img_r.raise_for_status()
        img = Image.open(BytesIO(img_r.content)).convert("RGB")

        # ── Smart crop to portrait 9:16 ──
        target_ratio = IMG_W / IMG_H
        w, h = img.size
        current_ratio = w / h
        if current_ratio > target_ratio:
            # Too wide → crop sides
            new_w = int(h * target_ratio)
            x_off = (w - new_w) // 2
            img = img.crop((x_off, 0, x_off + new_w, h))
        elif current_ratio < target_ratio:
            # Too tall → crop top/bottom (keep upper portion — face is usually there)
            new_h = int(w / target_ratio)
            img = img.crop((0, 0, w, new_h))

        img = img.resize((IMG_W, IMG_H), Image.LANCZOS)
        print(f"  ✅ Pixabay photo fetched: '{query}' → {img_url[:60]}…")
        return img

    except Exception as e:
        print(f"  ⚠️  Pixabay fetch error ('{query}'): {e}")
        return None


def fetch_background_photo(category: str) -> Image.Image:
    """
    Fetch a background photo from Pixabay with an Asian person matching the
    category mood. Randomly picks a pretty woman or a handsome man (unless the
    category is a couple-shot category) so the background varies per post.
    Applies Gaussian blur so the person is softly visible — like Boiling Waters PH.
    Falls back to a dark gradient if Pixabay unavailable.
    """
    if category in COUPLE_CATEGORIES:
        gender = "couple"
        keyword_map = CATEGORY_PHOTO_KEYWORDS_FEMALE  # "couple" queries are identical in both maps
    else:
        gender = random.choice(["female", "male"])
        keyword_map = CATEGORY_PHOTO_KEYWORDS_FEMALE if gender == "female" else CATEGORY_PHOTO_KEYWORDS_MALE

    queries = keyword_map.get(category, ["asian beautiful woman"] if gender != "male" else ["asian handsome man"])
    print(f"  🧑‍🤝‍🧑 Background subject: {gender}")

    # Randomly pick one nationality to mix into the query for variety
    nationality = random.choice(ASIAN_NATIONALITIES)

    img = None

    # Try queries in order, mixing in nationality
    for base_query in queries:
        # First try with nationality injected
        nat_query = f"{nationality} {base_query}" if nationality not in base_query else base_query
        img = _fetch_pixabay_photo(nat_query)
        if img:
            break
        # Then try base query without nationality
        img = _fetch_pixabay_photo(base_query)
        if img:
            break

    # Last resort fallback queries (match the gender we rolled, so it stays consistent)
    if img is None:
        if gender == "male":
            fallbacks = ["asian handsome man", "korean man portrait", "asian man"]
        else:
            fallbacks = ["asian beautiful woman", "korean woman portrait", "asian woman"]
        for fallback in fallbacks:
            img = _fetch_pixabay_photo(fallback)
            if img:
                break

    if img is None:
        # Dark gradient fallback (no network / no API key)
        print("  ℹ️  Using dark gradient fallback background.")
        img = Image.new("RGB", (IMG_W, IMG_H), C_DARK_BG)
        draw = ImageDraw.Draw(img)
        for y in range(IMG_H):
            v = int(255 * (1 - y / IMG_H) * 0.3)
            draw.line([(0, y), (IMG_W, y)], fill=(30 + v, 20 + v, 15 + v))
        return img  # no blur needed for plain bg

    # ── Apply Gaussian blur — person stays subtly visible, like Boiling Waters ──
    img = img.filter(ImageFilter.GaussianBlur(radius=BG_BLUR_RADIUS))
    print(f"  🌫️  Background blurred (radius={BG_BLUR_RADIUS})")
    return img


def apply_dark_overlay(bg: Image.Image) -> Image.Image:
    """
    Apply gradient dark overlay so text is readable while the blurred
    background person is still slightly visible — Boiling Waters style.
    """
    overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    for y in range(IMG_H):
        frac = y / IMG_H
        if frac < 0.12:
            alpha = 115           # Top: light dark — badge area
        elif frac < 0.30:
            alpha = int(115 + (frac - 0.12) / 0.18 * 30)
        elif frac < 0.55:
            # Mid zone: keep overlay moderate so blurred person peeks through
            alpha = int(145 + (frac - 0.30) / 0.25 * 55)
        else:
            alpha = 185           # Bottom: heavy dark for text readability
        draw_ov.line([(0, y), (IMG_W, y)], fill=(0, 0, 0, alpha))

    img_rgba = bg.convert("RGBA")
    img_rgba.alpha_composite(overlay)
    return img_rgba.convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# AI STORY GENERATION (Groq)
# ─────────────────────────────────────────────────────────────────────────────
SLIDE_SCHEMA = {
    "hook":       "1 to 2 sentences — the dramatic hook/headline in Taglish. Bold and emotional.",
    "part1":      "2 to 3 sentences — the situation/background. Relatable and specific.",
    "part2":      "2 to 3 sentences — the problem, twist, or what happened. More dramatic.",
    "part3":      "2 to 3 sentences — feelings, realizations, emotional impact.",
    "question":   "1 question to the followers. Start with 'Sa inyong palagay...' or 'Ano ang...' or 'Kayo ba...'",
    "cta":        "1 to 2 short CTA lines. Encourage commenters to help this anonymous member — use 'tayo' (we/us) framing like 'baka makatulong tayo sa ating kababayan' or 'tulungan natin siya'. Keep it warm, communal, and Taglish.",
}

CATEGORY_PROMPTS = {
    "LOVE STORY":    "a sweet but emotional Tagalog love story about a couple navigating early relationship challenges",
    "CHEATING":      "a heartbreaking Tagalog story about discovering a partner's infidelity",
    "STRUGGLES":     "a relatable Tagalog story about relationship struggles like long distance, insecurity, or poor communication",
    "ADVICE":        "a Tagalog anonymous post asking for honest advice about a confusing relationship situation",
    "HIDDEN DESIRE": "a Tagalog story about secret feelings for someone — unrequited love or a crush the person can't confess",
    "CONFESSION":    "a Tagalog anonymous confession about a past mistake or hidden truth in a relationship",
    "HEARTBREAK":    "a raw emotional Tagalog story about a painful breakup and the struggle to move on",
    "AGE GAP":       "a Tagalog love story where there is a significant age gap between two people (at least 10 years apart) — explore the feelings, the judgment from others, and whether love can overcome the difference",
    "COUSIN LOVE":   "a Tagalog anonymous confession from someone who has developed romantic feelings for their cousin — focus on the inner conflict, the secret feelings they can't act on, the family closeness that makes it confusing, and the pain of loving someone they can never be with",
}


def sanitize_story_text(text: str) -> str:
    """Strip markdown emphasis (**bold**, *italic*, _underline_) that the LLM
    sometimes adds despite being told not to — we already render bold/italic
    ourselves via the font, so literal asterisks would show up on the slide."""
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **bold**
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # *italic*
    text = re.sub(r"__(.+?)__", r"\1", text)        # __bold__
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)  # _italic_
    return text.strip()


def generate_story(category: str) -> dict:
    """Generate a multi-slide Taglish love story using Groq."""
    if not GROQ_API_KEY:
        print("  ⚠️  No GROQ_API_KEY — using fallback story.")
        return _fallback_story(category)

    prompt = f"""You are writing for a Filipino Facebook page similar to Boiling Waters PH.
Write {CATEGORY_PROMPTS.get(category, 'a relatable Tagalog relationship story')}.

The writing style is:
- Natural Taglish (mix of Tagalog and English, the way Filipinos actually text) — write MOSTLY in Tagalog, not English
- Feels like a real anonymous submission from a real person
- Emotional, raw, and relatable
- Age and gender can vary (common formats: "22F and 27M" etc.)
- Avoid being too dramatic or formal — keep it conversational
- Do NOT use any markdown formatting like **bold**, *italic*, or _underline_ anywhere in the text — plain text only
- For the "cta" field: always frame it as the COMMUNITY helping the anonymous member (use "tayo", "natin", "kababayan") — NOT asking the poster to follow or share for themselves

Respond ONLY with valid JSON (no markdown, no extra text, no code fences) matching this exact schema:
{{
  "hook": "{SLIDE_SCHEMA['hook']}",
  "part1": "{SLIDE_SCHEMA['part1']}",
  "part2": "{SLIDE_SCHEMA['part2']}",
  "part3": "{SLIDE_SCHEMA['part3']}",
  "question": "{SLIDE_SCHEMA['question']}",
  "cta": "{SLIDE_SCHEMA['cta']}"
}}"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 700,
            },
            timeout=40,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        # Validate keys
        for k in SLIDE_SCHEMA:
            if k not in data:
                data[k] = _fallback_story(category)[k]
        # Strip any stray markdown the model added despite instructions
        for k in SLIDE_SCHEMA:
            data[k] = sanitize_story_text(str(data[k]))
        print(f"  ✅ AI story generated for category: {category}")
        return data

    except Exception as e:
        print(f"  ⚠️  Groq error: {e} — using fallback story.")
        return _fallback_story(category)


def _fallback_story(category: str) -> dict:
    stories = {
        "LOVE STORY": {
            "hook":     "Dati akong naniniwala na hindi para sa akin ang mahalin nang ganito...",
            "part1":    "Nakilala ko siya sa isang grupo ng mga kaibigan. 24F ako, 27M siya. Hindi ko inakala na magiging ganito kami.",
            "part2":    "Nung una, friends lang kami. Tapos isang gabi, habang nag-uusap kami nang matagal, napagtanto ko na gusto ko na siyang higit pa sa kaibigan.",
            "part3":    "Takot akong sabihin kasi baka masira ang friendship namin. Pero hindi ko na kaya itago. Parang may nag-iingat sa akin sa kanya.",
            "question": "Kayo ba, sasabihin ninyo kung naramdaman ninyo ito? O titiisin na lang?",
            "cta":      "Comment kayo ng advice para sa ating anonymous member — baka makatulong tayo sa kanya. 💬"
        },
        "CHEATING": {
            "hook":     "Nalaman ko sa isang chat ang lahat — at hindi ko inaasahan na siya pala yun...",
            "part1":    "25F ako. Tatlong taon kaming magkasama. Lagi akong nagtiwala sa kanya kahit may mga kaibigan akong nagsasabi na mag-ingat ako.",
            "part2":    "Isang gabi, nagpahiram ako ng phone niya para mag-call. Nakita ko ang messages. Matagal na pala silang nag-uusap ng isa pang babae.",
            "part3":    "Hindi ko malaman kung mananatili o lalayo. Nasaktan ako hindi lang sa ginawa niya, kundi sa lahat ng sinabi niyang mahal niya ako.",
            "question": "Kayo ba, magpapatawad kaya kayo sa ganitong sitwasyon?",
            "cta":      "Ano ang dapat gawin ng ating kababayan? Tulungan natin siya — mag-comment ng inyong saloobin. 💔"
        },
        "HEARTBREAK": {
            "hook":     "Apat na taon — tapos biglang 'we need to talk' na lang...",
            "part1":    "23F ako. Nagmahal ako nang buong-buo. Inakala ko na siya na ang magiging katabi ko habambuhay.",
            "part2":    "Sabi niya kailangan niya ng time para sa sarili niya. Na hindi na siya masaya. Na hindi niya kasalanan, hindi rin daw kasalanan ko.",
            "part3":    "Pero bakit parang kasalanan ko ang sakit? Bakit ako ang nag-iingat ng mga alaala namin habang siya ay sige lang?",
            "question": "Paano kayo nakakaalis sa ganito? Anong tumutulong sa inyo para gumalaw?",
            "cta":      "Para sa ating anonymous member — hindi ka nag-iisa. 🤍 Mag-comment tayo para makatulong sa kanya."
        },
        "AGE GAP": {
            "hook":     "Mahal ko siya nang totoo — pero 15 taon ang pagitan namin at parang mundo ang layo...",
            "part1":    "20F ako, 35M siya. Nagkakilala kami sa trabaho. Hindi ko inasahan na mahuhulog ako sa kanya — seryoso, mabait, at palaging nandoon para sa akin.",
            "part2":    "Nung nalaman ng pamilya ko, parang nagka-gulo lahat. Sinabihan nila ako na huwag, na malayo daw ang mundo namin, na bata pa raw ako para malaman kung ano ang gusto ko.",
            "part3":    "Pero paano mo ipapaliwanag sa puso na huwag? Siya ang pinaka-genuine na tao na nakilala ko. Hindi ko alam kung ang edad ang hadlang — o ang takot lang ng iba.",
            "question": "Sa inyong palagay, magiging okay ba ang ganitong relasyon? O talagang may limitasyon ang age gap?",
            "cta":      "Tulungan natin ang ating anonymous member na makita ang tamang landas — mag-comment ng inyong saloobin. 💬"
        },
        "COUSIN LOVE": {
            "hook":     "Pinsan ko siya — pero bakit ganito ang nararamdaman ko tuwing nandoon siya...",
            "part1":    "21F ako. Mula pagkabata, lagi kaming magkasama sa mga family gatherings. Pero ngayon na mas malalaki na kami, nagsimula akong mapansin na... naiiba na ang pakiramdam ko sa kanya.",
            "part2":    "Ayaw kong aminin sa sarili ko. Lagi ko sinasabi na 'barkada lang' o 'family lang' — pero tuwing tumatawag siya, o ngumingiti sa akin, may kaba akong hindi ko mapaliwanagan.",
            "part3":    "Hindi ko alam kung sasabihin ko ito o itatanim na lang sa puso ko habambuhay. Takot ako sa reaction ng pamilya, at mas takot ako na mawala ang espesyal naming pagkakaibigan.",
            "question": "Paano ninyo haharapin ang ganitong sitwasyon? May nakaranas na ba sa atin ng ganito?",
            "cta":      "Huwag hatulan — tulungan natin ang ating kababayan. Mag-comment ng inyong payo nang may malasakit. 🤍"
        },
    }
    # Default fallback
    default = stories.get(category, stories["HEARTBREAK"])
    return default


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE IMAGE CREATION
# ─────────────────────────────────────────────────────────────────────────────
SLIDE_CONFIGS = [
    # (slide_type, show_headline_only, body_key)
    ("hook",     True,  None),       # Slide 1: Big hook only
    ("story1",   False, "part1"),    # Slide 2: hook header + part1
    ("story2",   False, "part2"),    # Slide 3: hook header + part2
    ("story3",   False, "part3"),    # Slide 4: hook header + part3
    ("question", False, "question"), # Slide 5: question to followers
    ("cta",      False, "cta"),      # Slide 6: follow/CTA
]


def create_slide(slide_type: str, story: dict, bg: Image.Image,
                 category: str, body_key: str = None,
                 hook_only: bool = False, fake_name: str = "") -> Image.Image:
    """Create one static Boiling Waters-style slide."""
    img = apply_dark_overlay(bg)
    draw = ImageDraw.Draw(img)

    pad_x = 58   # left/right padding

    # ── Anonymous member badge (pushed down so it clears the mobile status bar) ──
    draw_anon_badge(draw, x=pad_x, y=160, fake_name=fake_name)

    # ── Category label pill (top-right, aligned with badge) ──
    cat_font = get_font(30, bold=True)
    cat_text = f"  {category}  "
    cat_w = int(draw.textlength(cat_text, font=cat_font)) + 20
    cat_x = IMG_W - pad_x - cat_w
    cat_y = 172
    draw.rounded_rectangle([(cat_x, cat_y), (cat_x + cat_w, cat_y + 52)],
                             radius=10, fill=ANON_ORANGE)
    draw.text((cat_x + cat_w // 2, cat_y + 26), category,
              font=cat_font, anchor="mm", fill=C_WHITE)

    # ── HOOK HEADLINE (large bold italic) ──
    headline_y = int(IMG_H * 0.36)
    hook_text  = story.get("hook", "")

    if hook_only:
        # Slide 1: Large hook, no body
        h_font = get_font(58, bold=True, italic=True)
        h_lines = wrap_text(hook_text, h_font, IMG_W - pad_x * 2)
        for line in h_lines:
            draw_text_with_shadow(draw, line, pad_x, headline_y, h_font,
                                  fill=C_OFFWHITE, shadow_offset=4)
            headline_y += int(h_font.getbbox("Ag")[3] * 1.25)
    else:
        # Other slides: smaller hook as sub-header, then body
        h_font = get_font(52, bold=True, italic=True)
        h_lines = wrap_text(hook_text, h_font, IMG_W - pad_x * 2)
        # Show max 2 lines of hook as context
        for line in h_lines[:2]:
            draw_text_with_shadow(draw, line, pad_x, headline_y, h_font,
                                  fill=C_OFFWHITE, shadow_offset=3)
            headline_y += int(h_font.getbbox("Ag")[3] * 1.2)

        if len(h_lines) > 2:
            # truncation indicator
            draw.text((pad_x, headline_y), "...", font=h_font, fill=C_MUTED)
            headline_y += int(h_font.getbbox("Ag")[3] * 1.2)

        headline_y += 28  # gap

        # Body text
        if body_key:
            body_text = story.get(body_key, "")
            b_font    = get_font(42, bold=False)
            b_lines   = wrap_text(body_text, b_font, IMG_W - pad_x * 2)
            for line in b_lines:
                draw_text_with_shadow(draw, line, pad_x, headline_y, b_font,
                                      fill=C_WHITE, shadow_offset=2,
                                      shadow_color=(0, 0, 0, 160))
                headline_y += int(b_font.getbbox("Ag")[3] * 1.35)

    # ── Slide number dots (bottom center, above branding) ──
    total_slides = len(SLIDE_CONFIGS)
    cur_slide    = list(s[0] for s in SLIDE_CONFIGS).index(slide_type)
    dot_y = IMG_H - 175
    dot_spacing = 22
    start_x = IMG_W // 2 - (total_slides - 1) * dot_spacing // 2
    for i in range(total_slides):
        dx = start_x + i * dot_spacing
        if i == cur_slide:
            draw.ellipse([(dx - 7, dot_y - 7), (dx + 7, dot_y + 7)], fill=ANON_ORANGE)
        else:
            draw.ellipse([(dx - 5, dot_y - 5), (dx + 5, dot_y + 5)], fill=C_MUTED)

    # ── Bottom branding ──
    brand_y = IMG_H - 138

    # Left: cactus + "Featured from" + community name
    draw_cactus(draw, x=pad_x, y=brand_y, size=52)
    feat_font = get_font(25, bold=False)
    com_font  = get_font(30, bold=True)
    draw.text((pad_x + 68, brand_y + 6),  "Featured from",
              font=feat_font, fill=C_MUTED)
    draw.text((pad_x + 68, brand_y + 36), COMMUNITY_NAME,
              font=com_font,  fill=C_OFFWHITE)

    return img


def create_all_slides(story: dict, category: str) -> list[Image.Image]:
    """Create all 6 slides for the reel."""
    print(f"  📷 Fetching background photo for {category}…")
    bg = fetch_background_photo(category)

    # Pick one fake name per reel so it stays consistent across all slides
    gender = random.choice(["female", "male"])
    fake_name = get_fake_name(gender)
    print(f"  🪪 Anonymous identity for this reel: {fake_name}")

    images = []
    for i, (slide_type, hook_only, body_key) in enumerate(SLIDE_CONFIGS):
        img = create_slide(slide_type, story, bg, category,
                           body_key=body_key, hook_only=hook_only,
                           fake_name=fake_name)
        images.append(img)
        print(f"   Slide {i+1}/{len(SLIDE_CONFIGS)} ({slide_type}) ✓")
    return images


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO ASSEMBLY (static frames — no animation)
# ─────────────────────────────────────────────────────────────────────────────
def get_background_music(category: str) -> str | None:
    """
    Pick a random MP3 from assets/music/<mood>/ matching this category's mood.
    Returns a file path, or None if no folder/tracks exist (video just renders
    silent — same graceful fallback pattern as the background photo).
    """
    mood = CATEGORY_MUSIC_MOOD.get(category, "melancholy")
    folder = os.path.join(MUSIC_DIR, mood)
    if not os.path.isdir(folder):
        print(f"  ℹ️  No music folder for mood '{mood}' (looked in {folder}) — rendering silent.")
        return None
    tracks = [f for f in os.listdir(folder) if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac"))]
    if not tracks:
        print(f"  ℹ️  Music folder '{mood}' is empty — rendering silent. "
              f"Drop a few royalty-free tracks into {folder}/")
        return None
    chosen = random.choice(tracks)
    print(f"  🎵 Background music: [{mood}] {chosen}")
    return os.path.join(folder, chosen)


def build_reel(images: list, output_path: str, category: str = None) -> str:
    print(f"\n🎬 Stitching {len(images)} static slides into video…")
    clips = []
    for i, pil_img in enumerate(images):
        arr  = np.array(pil_img)
        clip = ImageClip(arr).set_duration(SLIDE_DURATION).set_fps(FPS)
        clips.append(clip)
        print(f"   Clip {i+1}/{len(images)} prepared ✓")

    video = concatenate_videoclips(clips, method="compose")

    # ── Background music ──
    music_path = get_background_music(category) if category else None
    audio_enabled = False
    if music_path:
        try:
            audio = AudioFileClip(music_path)
            if audio.duration < video.duration:
                audio = audio_loop(audio, duration=video.duration)
            else:
                audio = audio.subclip(0, video.duration)
            audio = audio.volumex(MUSIC_VOLUME)
            audio = audio.audio_fadein(MUSIC_FADE).audio_fadeout(MUSIC_FADE)
            video = video.set_audio(audio)
            audio_enabled = True
        except Exception as e:
            print(f"  ⚠️  Could not attach background music ({e}) — rendering silent.")

    print(f"\n🎞️  Rendering MP4 → {output_path}…")
    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio=audio_enabled,
        audio_codec="aac" if audio_enabled else None,
        preset="medium",
        ffmpeg_params=["-crf", "20", "-pix_fmt", "yuv420p"],
        logger=None,
    )
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  ✅ Video rendered! Size: {size_mb:.1f} MB")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB RELEASE UPLOAD (same as original — public direct-download URL)
# ─────────────────────────────────────────────────────────────────────────────
def create_github_release(tag: str, repo: str, token: str) -> dict:
    r = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "tag_name": tag,
            "name": tag,
            "body": "Auto-generated Love Stories Reel video asset — safe to delete.",
            "draft": False,
            "prerelease": False,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def upload_asset_to_release(upload_url: str, video_path: str, token: str) -> str:
    upload_url = upload_url.split("{")[0]
    filename = os.path.basename(video_path)
    with open(video_path, "rb") as f:
        data = f.read()
    r = requests.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "video/mp4",
        },
        params={"name": filename},
        data=data,
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["browser_download_url"]


def delete_github_release(release_id: int, repo: str, token: str) -> None:
    try:
        requests.delete(
            f"https://api.github.com/repos/{repo}/releases/{release_id}",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json"},
            timeout=30,
        )
    except Exception as e:
        print(f"  ⚠️  Could not clean up release: {e}")


def upload_video_to_github_release(video_path: str) -> tuple:
    repo  = os.environ["GITHUB_REPOSITORY"]
    token = GH_RELEASE_TOKEN
    if not token:
        raise RuntimeError("No GH_RELEASE_TOKEN or GITHUB_TOKEN — can't upload.")

    size_mb = os.path.getsize(video_path) / 1024 / 1024
    print(f"  ☁️  Uploading video ({size_mb:.1f} MB) to GitHub Release…")

    tag     = f"love-reel-{int(time.time())}"
    release = create_github_release(tag, repo, token)
    print(f"  📦 Release created: {tag} (id={release['id']})")

    url = upload_asset_to_release(release["upload_url"], video_path, token)
    print(f"  ✅ Video hosted at: {url}")
    return url, release["id"]


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK GRAPH API — PAGE VIDEO POSTING
# ─────────────────────────────────────────────────────────────────────────────
def fb_post(path: str, **params) -> dict:
    r = requests.post(
        f"{FB_BASE}/{path}",
        params={"access_token": FB_ACCESS_TOKEN, **params},
        timeout=60,
    )
    if not r.ok:
        print(f"  FB API error: {r.status_code} — {r.text}")
    r.raise_for_status()
    return r.json()


def fb_get(path: str, **params) -> dict:
    r = requests.get(
        f"{FB_BASE}/{path}",
        params={"access_token": FB_ACCESS_TOKEN, **params},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def upload_video_to_page(video_url: str, description: str) -> str:
    data = fb_post(
        f"{FB_PAGE_ID}/videos",
        file_url=video_url,
        description=description,
    )
    return data["id"]


def wait_for_video_ready(video_id: str, retries: int = 24, interval: int = 10):
    for attempt in range(retries):
        status = fb_get(video_id, fields="status").get("status", {})
        video_status = status.get("video_status", "unknown")
        print(f"    Video {video_id}: {video_status}  (attempt {attempt+1}/{retries})")
        if video_status == "ready":
            return
        if video_status == "error":
            raise RuntimeError(f"Video {video_id} errored during processing.")
        time.sleep(interval)
    print("    ⚠️  Didn't confirm 'ready' in time — continuing anyway.")


def post_comment(video_id: str, message: str) -> str:
    r = requests.post(
        f"{FB_BASE}/{video_id}/comments",
        params={"access_token": FB_ACCESS_TOKEN, "message": message},
        timeout=30,
    )
    if not r.ok:
        print(f"  ⚠️  Comment API error: {r.status_code} — {r.text}")
    return r.json().get("id", "")


# ─────────────────────────────────────────────────────────────────────────────
# CAPTION
# ─────────────────────────────────────────────────────────────────────────────
def build_caption(story: dict, category: str) -> str:
    hashtags = CATEGORY_HASHTAGS.get(category, "#LoveStory #Pagmamahal #RelationshipGoals")
    hook     = story.get("hook", "")
    question = story.get("question", "Ano ang masasabi ninyo tungkol dito?")
    cta      = story.get("cta", "I-share ito sa inyong mga kaibigan! 💬")

    return (
        "💬 ANONYMOUS STORY\n\n"
        f'"{hook}"\n\n'
        f"{question}\n\n"
        f"{cta}\n\n"
        "👇 Comment your thoughts below!\n"
        "❤️ React kung ma-relate ka!\n"
        "📤 Share sa mga taong kailangan ito marinig!\n\n"
        f"Follow our pages para sa mas maraming love stories at confessions every day! 💌\n\n"
        f"{hashtags} #AnonymousStory #LoveConfessionsPH #PilipinoLoveStory"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  💌 Love Stories Facebook REEL Bot — Boiling Waters Style")
    print("=" * 60)

    # Diagnostic: confirm secrets actually reached the script, without ever
    # printing the real values. If this shows length=0 for PIXABAY_API_KEY,
    # the secret isn't reaching this run — re-check the GitHub Actions secret
    # name/scope and re-run the workflow (secrets added mid-run aren't picked
    # up by runs that already started).
    pix_len = len(PIXABAY_API_KEY)
    groq_len = len(GROQ_API_KEY)
    print(f"\n🔑 Secret check — PIXABAY_API_KEY: {'set, length ' + str(pix_len) if pix_len else 'EMPTY/NOT SET'}")
    print(f"🔑 Secret check — GROQ_API_KEY:    {'set, length ' + str(groq_len) if groq_len else 'EMPTY/NOT SET'}")

    if not MOVIEPY_OK:
        print("❌ moviepy not installed! Run: pip install 'moviepy<2' numpy")
        sys.exit(1)

    print("\n📦 Setting up fonts…")
    setup_fonts()

    # Pick a random category
    category = random.choice(CATEGORIES)
    print(f"\n🎯 Today's category: {category}")

    print(f"\n✍️  Generating AI story (Groq)…")
    story = generate_story(category)
    print(f"   Hook: {story.get('hook', '')[:70]}…")

    print(f"\n🎨 Creating {len(SLIDE_CONFIGS)} slides (1080×1920)…")
    images = create_all_slides(story, category)

    print(f"\n🎬 Building video reel…")
    build_reel(images, OUTPUT_PATH, category=category)

    print("\n☁️  Uploading to GitHub Release…")
    video_url, release_id = upload_video_to_github_release(OUTPUT_PATH)

    caption = build_caption(story, category)

    print("\n📱 Posting video to Facebook Page…")
    video_id = upload_video_to_page(video_url, caption)
    print(f"   Video ID: {video_id}")

    print("\n⏳ Waiting for video to process…")
    wait_for_video_ready(video_id, retries=24, interval=10)
    print(f"\n✅ SUCCESS! Love Story Reel posted! Video ID: {video_id}")

    time.sleep(5)
    print("\n💬 Posting first comment (hashtags & engagement)…")
    try:
        bonus_tags = (
            "#BoilingWatersPH #LoveStoryPH #AnonymousPH #RelationshipPH "
            "#PagmamahalNamin #LoveConfessions #TotooNgPuso #FilipinoCouples"
        )
        post_comment(video_id,
            f"📌 Para sa lahat ng gustong mag-share ng kanilang kwento, "
            f"DM kami o comment below! Lahat ng submissions ay anonymous. 💌\n\n{bonus_tags}")
        print("   ✅ Comment posted!")
    except Exception as e:
        print(f"   ⚠️  Comment failed: {e}")

    print("\n🧹 Cleaning up GitHub release asset…")
    delete_github_release(release_id, os.environ["GITHUB_REPOSITORY"], GH_RELEASE_TOKEN)

    print("\n💌 Done! Love Stories automation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
