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

SLIDE_DURATION  = 8.0   # seconds per static slide — longer so readers actually finish
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
    "AGE GAP":              "romantic",
    "COUSIN LOVE":          "dramatic",
    "THIRD PARTY":          "dramatic",
    "SECRET ADMIRER":       "romantic",
    "FRIENDZONE":           "melancholy",
    "BALIK-LOVER":          "hopeful",
    "ONLINE LOVE":          "romantic",
    "BROKEN ENGAGEMENT":    "heartbreak",
    "SUGAR RELATIONSHIP":   "dramatic",
    "SITUATIONSHIP":        "melancholy",
    "ASAWA VS KABIT":       "heartbreak",
    "IN-LAW CONFLICT":      "melancholy",
    "LONG DISTANCE":        "melancholy",
    "CHILDHOOD SWEETHEART": "romantic",
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
    "THIRD PARTY",
    "SECRET ADMIRER",
    "FRIENDZONE",
    "BALIK-LOVER",
    "ONLINE LOVE",
    "BROKEN ENGAGEMENT",
    "SUGAR RELATIONSHIP",
    "SITUATIONSHIP",
    "ASAWA VS KABIT",
    "IN-LAW CONFLICT",
    "LONG DISTANCE",
    "CHILDHOOD SWEETHEART",
]

CATEGORY_HASHTAGS = {
    "LOVE STORY":    "#LoveStory #Pagmamahal #RelationshipGoals #LoveConfessionsPH #TotooNgPuso",
    "CHEATING":      "#Cheating #Kabit #Infidelity #LoveAndPain #RealTalk #Pagtataksil",
    "STRUGGLES":     "#RelationshipStruggles #LDR #LoveHurts #MahalKitaPeroBakit #BagalKo",
    "ADVICE":        "#RelationshipAdvice #LoveAdvice #TanongSaInyo #HelpMe #SabihinMo",
    "HIDDEN DESIRE": "#HiddenDesire #SecretFeeling #NaramdamanKo #HindiKoMasabi #Gusto",
    "CONFESSION":    "#Confession #Pagtatapat #AnonymousStory #LoveConfession #Totoo",
    "HEARTBREAK":    "#Heartbreak #SakitNgPuso #MovingOn #LoveHurts #Masakit #Nawala",
    "AGE GAP":              "#AgeGap #AgeGapLove #OlderAndYounger #LoveHasNoAge #AgeIsJustANumber #PagmamahalNaWalangHangganan",
    "COUSIN LOVE":          "#CousinLove #ForbiddenLove #PinaghindilangPagmamahal #SecretFeeling #HiddenHeart #TabooLove",
    "THIRD PARTY":          "#ThirdParty #Kabit #OtherWoman #OtherMan #LoveProblem #RealTalkPH #KabitStory",
    "SECRET ADMIRER":       "#SecretAdmirer #CrushKo #HindiKoMasabi #LihimNaPagmamahal #SecretLove #SinabayangPuso",
    "FRIENDZONE":           "#Friendzone #MahalKitaPeroBarkada #BarkadaLang #FriendzonedPH #LoveUnrequited #UmibigNa",
    "BALIK-LOVER":          "#BalikLover #ExBack #SecondChance #Bumalik #MahalinUlit #PagkakataonPa",
    "ONLINE LOVE":          "#OnlineLove #OnlineRelationship #MetOnline #LDROnline #DigitalLove #HindiPaNakikita",
    "BROKEN ENGAGEMENT":    "#BrokenEngagement #CancelledWedding #HindiNaTuloy #SanaOl #NasiraAngSimbahan #NagpaliwanagNa",
    "SUGAR RELATIONSHIP":   "#SugarRelationship #SugarDaddy #SugarMommy #ControversialLove #ConfessionPH #TotooIto",
    "SITUATIONSHIP":        "#Situationship #KamiPeroHindiKami #DefineTheRelationship #DTR #GenZLove #AnoTayoMga",
    "ASAWA VS KABIT":       "#AsawaVsKabit #Kabit #Asawa #InfidelityPH #WifeSide #HusbandSide #SabihinAngTotoo",
    "IN-LAW CONFLICT":      "#InLawConflict #BiyenangProblema #PamilyaNiya #RelationshipProblems #SabihinMo #TulunganNatin",
    "LONG DISTANCE":        "#LongDistance #LDR #MissKitaAraw #OFWLove #LongDistanceRelationship #KaylanManMuli",
    "CHILDHOOD SWEETHEART": "#ChildhoodSweetheart #FirstLove #BataNgKasama #ReunitedLove #UnangPagmamahal #NatuklasanUlit",
}

# Pixabay search queries per category — Asian people, slightly blurred bg
# Format: list of queries to try in order (fallback if first returns nothing)
# Split by gender so we can pick "pretty woman" or "handsome man" depending on the story.
CATEGORY_PHOTO_KEYWORDS_FEMALE = {
    "LOVE STORY":           ["asian couple romantic", "asian couple love", "asian couple"],
    "CHEATING":             ["asian woman sad", "asian woman alone sad", "asian woman crying"],
    "STRUGGLES":            ["asian woman thinking", "asian woman pensive", "asian woman melancholy"],
    "ADVICE":               ["asian beautiful woman", "asian woman coffee thinking", "asian woman contemplating"],
    "HIDDEN DESIRE":        ["asian woman mysterious", "asian beautiful woman", "asian woman longing"],
    "CONFESSION":           ["asian woman writing", "asian woman diary", "asian woman letter"],
    "HEARTBREAK":           ["asian woman crying", "asian woman heartbreak", "asian woman tears"],
    "AGE GAP":              ["asian couple age difference", "older man younger woman asian", "asian couple romantic"],
    "COUSIN LOVE":          ["asian woman secret love", "asian woman hidden feelings", "asian woman thinking"],
    "THIRD PARTY":          ["asian woman guilty", "asian woman conflicted", "asian woman looking away"],
    "SECRET ADMIRER":       ["asian woman shy smile", "asian woman blushing", "asian woman looking afar"],
    "FRIENDZONE":           ["asian woman and man friends", "asian friends laughing", "asian friends close"],
    "BALIK-LOVER":          ["asian woman looking back", "asian woman nostalgic", "asian woman reunion"],
    "ONLINE LOVE":          ["asian woman phone romantic", "asian woman texting smile", "asian woman laptop love"],
    "BROKEN ENGAGEMENT":    ["asian woman crying", "asian woman sad alone", "asian woman heartbroken"],
    "SUGAR RELATIONSHIP":   ["asian woman elegant", "asian woman luxury lifestyle", "asian woman thoughtful"],
    "SITUATIONSHIP":        ["asian woman confused love", "asian woman uncertain", "asian woman thinking"],
    "ASAWA VS KABIT":       ["asian woman confrontation", "asian woman angry sad", "asian woman betrayed"],
    "IN-LAW CONFLICT":      ["asian woman stressed", "asian woman family tension", "asian woman conflict"],
    "LONG DISTANCE":        ["asian woman missing someone", "asian woman alone window", "asian woman waiting"],
    "CHILDHOOD SWEETHEART": ["asian couple reunion", "asian couple nostalgic", "asian couple memories"],
}

CATEGORY_PHOTO_KEYWORDS_MALE = {
    "LOVE STORY":           ["asian couple romantic", "asian couple love", "asian couple"],
    "CHEATING":             ["asian man sad", "asian man alone sad", "asian man serious"],
    "STRUGGLES":            ["asian man thinking", "asian man pensive", "asian man tired"],
    "ADVICE":               ["asian handsome man", "asian man coffee thinking", "asian man contemplating"],
    "HIDDEN DESIRE":        ["asian man mysterious", "asian handsome man", "asian man longing"],
    "CONFESSION":           ["asian man writing", "asian man diary", "asian man letter"],
    "HEARTBREAK":           ["asian man heartbreak", "asian man sad", "asian man alone"],
    "AGE GAP":              ["asian couple age difference", "older woman younger man asian", "asian couple romantic"],
    "COUSIN LOVE":          ["asian man secret love", "asian man hidden feelings", "asian man thinking"],
    "THIRD PARTY":          ["asian man guilty", "asian man conflicted", "asian man looking away"],
    "SECRET ADMIRER":       ["asian man shy smile", "asian man admiring", "asian man looking afar"],
    "FRIENDZONE":           ["asian man and woman friends", "asian friends laughing", "asian friends close"],
    "BALIK-LOVER":          ["asian man looking back", "asian man nostalgic", "asian man reunion"],
    "ONLINE LOVE":          ["asian man phone romantic", "asian man texting smile", "asian man laptop love"],
    "BROKEN ENGAGEMENT":    ["asian man crying sad", "asian man alone heartbreak", "asian man devastated"],
    "SUGAR RELATIONSHIP":   ["asian man elegant", "asian man luxury lifestyle", "asian man thoughtful"],
    "SITUATIONSHIP":        ["asian man confused love", "asian man uncertain", "asian man thinking"],
    "ASAWA VS KABIT":       ["asian man confrontation", "asian man angry sad", "asian man betrayed"],
    "IN-LAW CONFLICT":      ["asian man stressed", "asian man family tension", "asian man conflict"],
    "LONG DISTANCE":        ["asian man missing someone", "asian man alone window", "asian man waiting"],
    "CHILDHOOD SWEETHEART": ["asian couple reunion", "asian couple nostalgic", "asian couple memories"],
}

# Backwards-compat alias (some helper code/tests may still reference the old name)
CATEGORY_PHOTO_KEYWORDS = CATEGORY_PHOTO_KEYWORDS_FEMALE

# Categories that are always a couple shot regardless of gender roll
COUPLE_CATEGORIES = {
    "LOVE STORY", "AGE GAP", "BALIK-LOVER", "ONLINE LOVE",
    "LONG DISTANCE", "CHILDHOOD SWEETHEART", "FRIENDZONE",
}

# All photo queries now use "asian" consistently for broader, more inclusive results
ASIAN_NATIONALITIES = ["asian"]

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
            fallbacks = ["asian handsome man", "asian man portrait", "asian man"]
        else:
            fallbacks = ["asian beautiful woman", "asian woman portrait", "asian woman"]
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
    "hook":       "1 to 2 sentences — STOP-SCROLLING dramatic hook in Taglish. Must be controversial, punchy, or devastating. Think: the line a real person would screenshot and send to their group chat.",
    "part1":      "3 to 4 sentences — the situation/background. Specific details (ages, place). Start with the narrator establishing themselves, then pull the reader in with something relatable but slightly unexpected. Real Taglish, not textbook.",
    "part2":      "3 to 4 sentences — the TWIST, the revelation, or the ugliest moment of the story. This is where a blurred curse may naturally fall. The moment where everything changed. Make it physical — the narrator's body reacted, not just their mind.",
    "part3":      "3 to 4 sentences — the raw emotional aftermath. Include the narrator's CONTROVERSIAL OPINION or uncomfortable realization. Not just sad — angry, confused, ashamed, or still in love despite everything. End on a question the narrator is asking themselves.",
    "question":   "1 provocative question to the followers — something that will SPLIT the comment section. Start with 'Kayo ba...' or 'Sa inyong palagay...' or 'Ano ang gagawin ninyo...'",
    "cta":        "1 to 2 short lines of GENUINE NEUTRAL ADVICE — not 'tulungan natin' or 'kababayan' framing. Write it like a wise, calm older sister or kuya giving real advice. Taglish. Emotionally honest but neutral — no taking sides. Should feel like something someone would screenshot and save. End with one small emoji (💔 🤍 💬 🥺 or similar).",
    "closing":    "2 to 3 sentences — written directly to the page after the story ends. Starts with 'Dear Viral Video Challenge,'. Anonymous sender gives permission to post. They explain in casual, vulnerable Taglish that they can't talk to people who know them personally — they need honest perspectives from strangers. Feels raw and real.",
}

CATEGORY_PROMPTS = {
    "LOVE STORY":    "a deeply emotional and controversial Tagalog love story — not just sweet, but messy, complicated, with real doubt and real fear. The narrator is falling hard but something feels off. Show the obsession, the overthinking, the 3am thoughts.",
    "CHEATING":      "a gut-wrenching Tagalog story about discovering betrayal — and the shameful part: part of them still loves the person who destroyed them. Controversial angle: the narrator is angry at THEMSELVES for still caring.",
    "STRUGGLES":     "a raw Tagalog story about a relationship on the edge of collapse — not just sad, but with accusations, silent treatment, screaming matches. Real ugly relationship struggles. The narrator is exhausted but refuses to give up.",
    "ADVICE":        "a controversial Tagalog anonymous post asking for advice — but the situation is morally grey. Maybe they did something wrong too. They want validation but deep down know the answer. Make it uncomfortable.",
    "HIDDEN DESIRE": "a haunting Tagalog story about secret feelings that are consuming the narrator — obsessive thoughts, jealousy watching that person with someone else, the physical ache of wanting someone you can't have.",
    "CONFESSION":    "a controversial and guilt-ridden Tagalog anonymous confession about something they did in a relationship that they're ashamed of — not just a mistake but a real moral failing. The narrator is torn between confessing and burying it forever.",
    "HEARTBREAK":    "a devastating Tagalog story about a breakup that broke more than just a relationship — it broke identity, future plans, who they thought they were. Raw anger mixed with deep love. The kind of pain that makes you numb.",
    "AGE GAP":              "a controversial Tagalog love story with a significant age gap (at least 10 years) — society is judging them, family is threatening to disown, but the feelings are undeniable. Show the ugly fight between love and what everyone else thinks is right.",
    "COUSIN LOVE":          "a deeply conflicted Tagalog anonymous confession about romantic feelings for a cousin — the shame, the confusion, the family dinners that feel like torture, the secret glances. The narrator is fighting against feelings they didn't choose and can never act on.",
    "THIRD PARTY":          "a raw Tagalog confession told from the 'third party' perspective — the other woman or man who knew they were wrong but stayed anyway. Explore the real feelings, the guilt they carry, the moments they almost walked away, and why they didn't. Controversial: make the reader almost understand even if they disagree.",
    "SECRET ADMIRER":       "a haunting Tagalog story about someone who has been silently in love with a close friend for years — watching them date other people, celebrating their happiness while dying inside. The obsessive thoughts, the almost-confessions, the cowardice disguised as protection.",
    "FRIENDZONE":           "a devastatingly relatable Tagalog story about being in love with a best friend who only sees you as a friend — the torture of being the shoulder they cry on after their breakups, of knowing them better than anyone, but being invisible as a lover.",
    "BALIK-LOVER":          "a complicated Tagalog story about an ex who came back — and the terrifying truth that the narrator's heart never fully healed. The war between 'ayoko nang masaktan ulit' and 'pero mahal ko pa rin siya'. Second chances that might be mistakes.",
    "ONLINE LOVE":          "a deeply emotional Tagalog story about falling in love with someone met online — calls at 2am, knowing every detail of each other's lives, feeling more understood than with anyone in real life, but never meeting. Is it real love or a beautiful illusion?",
    "BROKEN ENGAGEMENT":    "a heartbreaking Tagalog confession about a cancelled wedding or broken engagement — who called it off, what really happened behind closed doors, and the grief of mourning a future that had already been planned down to the last detail.",
    "SUGAR RELATIONSHIP":   "a controversial and honest Tagalog anonymous confession about being in a sugar relationship — blurred lines between money and real feelings, the judgment of others, the moments of genuine connection and the moments of deep shame. No easy answers.",
    "SITUATIONSHIP":        "a painfully relatable Tagalog story about a 'situationship' — two people clearly in love but too scared to define it. Mixed signals, almost-confessions, soft launches, and the slow torture of not knowing where you stand with the person you think about every day.",
    "ASAWA VS KABIT":       "a dramatic and raw Tagalog story told from the betrayed spouse's perspective — the discovery, the confrontation, the ugly truth of what the other person said, and the impossible decision of whether to stay, fight, or let go. No clean resolution.",
    "IN-LAW CONFLICT":      "a deeply frustrating Tagalog story about in-law interference threatening a relationship — controlling family members, impossible standards, a partner who keeps choosing their family over the relationship. The narrator loves their partner but is being slowly crushed by the family around them.",
    "LONG DISTANCE":        "a devastating Tagalog LDR story — the loneliness that becomes a third person in the relationship, the growing distance despite daily calls, the paranoia, the sacrifices, and the moment the narrator realized love alone might not be enough to survive the kilometers.",
    "CHILDHOOD SWEETHEART": "a nostalgic and emotionally complex Tagalog story about reconnecting with a first love years later — both changed, both carrying old wounds, old butterflies rushing back. The beautiful terror of getting a second chance with someone who once broke your world open.",
}

# Philippine cities/places to randomly inject for authenticity
PH_PLACES = [
    "Maynila", "Quezon City", "Cebu", "Davao", "Iloilo",
    "Cagayan de Oro", "Pampanga", "Batangas", "Bulacan", "Laguna",
    "Cavite", "Pasig", "Makati", "Taguig", "Valenzuela",
    "Antipolo", "Caloocan", "Bacolod", "General Santos", "Zamboanga",
]

# Blurred curse words — used in angry/emotional categories
BLURRED_CURSES = [
    "p*ta", "p**e", "p**g ina mo", "s*ng*ng* ka",
    "g*g* ka talaga", "t*ng*na", "w*lang-hiy*",
    "b**g*t", "a*og ka", "p*k* mo",
    "t*n*m* ka", "h*nd*-h*nd* niya ako k*t*n*wan",
    "p*ta 'to", "p*k* niya", "l*ntaw niya lang ako",
    "s*sumpain ko siya", "p**g ina niya talaga",
]

# Categories where blurred curses feel authentic
CURSE_CATEGORIES = {
    "CHEATING", "HEARTBREAK", "STRUGGLES", "CONFESSION", "HIDDEN DESIRE",
    "AGE GAP", "THIRD PARTY", "BROKEN ENGAGEMENT", "ASAWA VS KABIT",
    "SITUATIONSHIP", "BALIK-LOVER",
}

def get_random_female_age() -> int:
    return random.randint(20, 32)

def get_random_male_age() -> int:
    return random.randint(20, 45)

def get_random_place() -> str:
    return random.choice(PH_PLACES)

def get_blurred_curse() -> str:
    return random.choice(BLURRED_CURSES)


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

    female_age = get_random_female_age()
    male_age   = get_random_male_age()

    # For AGE GAP — enforce a realistic gap of 10–18 years and make it consistent
    if category == "AGE GAP":
        female_age = random.randint(20, 28)          # younger narrator
        gap        = random.randint(10, 18)           # the gap itself
        male_age   = female_age + gap                 # older partner = exact match
        age_gap_note = (
            f"- CRITICAL: The age gap is exactly {gap} years ({female_age}F ako, {male_age}M siya). "
            f"The hook or part1 MUST mention '{gap} taon ang agwat namin' or '{gap}-year age gap' — "
            f"the exact number must appear in the story so it feels real and specific."
        )
    else:
        age_gap_note = ""

    place      = get_random_place()
    curse      = get_blurred_curse() if category in CURSE_CATEGORIES else ""

    curse_instruction = (
        f'- The story should feel emotionally charged and raw. Naturally include one blurred curse like "{curse}" '
        f'somewhere in part1, part2, or part3 where it fits — the way a real angry or hurt person would type it.'
        if curse else
        "- Keep the tone warm and emotional but not angry."
    )

    prompt = f"""You are writing an anonymous submission for a Filipino Facebook page like Boiling Waters PH.
Write {CATEGORY_PROMPTS.get(category, 'a relatable Tagalog relationship story')}.

Important details to use:
- The narrator (the one submitting) is a {female_age}-year-old female. In the story she is "ako". When showing her age, write "{female_age}F ako" (meaning: I am {female_age}, Female). NEVER write "{female_age}F siya" — she is ako, not siya.
- The other person is a {male_age}-year-old male. In the story they are "siya". When showing their age, write "{male_age}M siya" (meaning: they are {male_age}, Male).
- The story happens in or around {place}
- Always refer to the narrator as "ako" and the other person as "siya" — NEVER use "kami" to describe them both together
{age_gap_note}

Writing style RULES (critically important — break any of these and the story fails):
- Write like a real person whose hands are trembling while typing this — lowercase, broken sentences, some run-ons, real emotion leaking through every word
- Taglish — mostly Tagalog, but English words drop in the way they naturally do in Filipino texts ("I mean", "honestly", "pero like")
- MIX sentence lengths dramatically: short punchy sentences after long emotional run-ons create real rhythm (example: "Sinabi niya mahal niya ako, na palagi siyang nandoon para sa akin, na ako lang ang gusto niya. Tapos may iba pala siya. Tapos.")
- Use ellipsis (...) for trailing thoughts. Use em-dash (—) for sudden interruptions. These are how real hurt people type.
- Include at least ONE moment of physical sensation — nanginginig (trembling), hindi makahinga (can't breathe), sumuka (felt sick), nanlalamig ang katawan — the body's reaction to emotional pain
- Include the narrator's CONTROVERSIAL OPINION — not just what happened, but their raw unfiltered take on it. Something that might make people argue in the comments.
- The hook must be PUNCHY and CONTROVERSIAL — like a headline that makes you STOP scrolling. Not sweet. Dramatic. A punch to the gut.
- Introduce ages like: "{female_age}F ako, {male_age}M siya" — narrator is always ako, other person is always siya
- Mention {place} naturally at least once
{curse_instruction}
- Do NOT use any markdown formatting like **bold**, *italic*, or _underline_ — plain text only
- For the "cta" field: give SHORT, GENUINE NEUTRAL ADVICE in Taglish. Write like a calm, caring older sister or kuya. No "tayo", "natin", or "kababayan" framing. No asking for comments or shares. Just real, emotionally honest wisdom that feels like something worth saving. Neutral — don't take sides, but don't be cold either. End with one small emoji (💔 🤍 💬 🥺 ✨).
- For the "closing" field: this is a short personal note from the anonymous sender to the page, written AFTER the story ends. It must start with "Dear Viral Video Challenge," and give the page permission to share the story. The sender should explain in casual Taglish that they're sharing because it's hard to open up to people they know personally, and they're hoping for insights, advice, or a different perspective from strangers. Make it feel raw and real — vulnerable, not polished. Here are some varied examples to rotate from (DO NOT copy these verbatim — use them as INSPIRATION only):
  • "Dear Viral Video Challenge, okay lang po ba i-share ninyo 'to sa page? Nahihirapan kasi akong kausapin ang mga taong kilala ko tungkol dito — parang mas madali pag strangers ang sasagot. Baka may makatulong sa akin dito. 🙏"
  • "Dear Viral Video Challenge, sana okay lang i-post ninyo 'to. Wala akong matanungan na talagang honest kasi lahat ng kakilala ko may bias. Gusto ko lang marinig ang totoo mula sa ibang tao."
  • "Dear Viral Video Challenge, i-share na po kaya ninyo ito? Minsan mas komportable kang buksan sa mga hindi mo kilala kesa sa sariling pamilya o barkada. Umaasa lang ako na may makapagbigay ng insight."
  • "Dear Viral Video Challenge, puwede po ba itong i-post? Hindi ko kayang kausapin ang mga kaibigan ko dito, masyado silang close sa sitwasyon. Baka ang mga followers ninyo ang makatulong sa akin."

Respond ONLY with valid JSON (no markdown, no extra text, no code fences) matching this exact schema:
{{
  "hook": "{SLIDE_SCHEMA['hook']}",
  "part1": "{SLIDE_SCHEMA['part1']}",
  "part2": "{SLIDE_SCHEMA['part2']}",
  "part3": "{SLIDE_SCHEMA['part3']}",
  "question": "{SLIDE_SCHEMA['question']}",
  "cta": "{SLIDE_SCHEMA['cta']}",
  "closing": "{SLIDE_SCHEMA['closing']}"
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
    female_age = get_random_female_age()
    male_age   = get_random_male_age()
    place      = get_random_place()
    stories = {
        "LOVE STORY": {
            "hook":     f"bakit yung tao na hindi mo dapat mahalin... siya pa yung pinaka-safe na lugar mo?",
            "part1":    f"{female_age}F ako, {male_age}M siya. nagkita kami sa {place} sa paraan na hindi ko inaasahan — hindi siya type ko sa papel, honestly. pero something about how he listened. hindi siya naghahanap ng chance na magsalita — nakikinig talaga siya sa akin.",
            "part2":    "at doon nagsimula yung problema ko. kasi habang lumalim yung aming usapan, nararamdaman ko na hindi lang friendship yung gusto ko. nanginginig ako tuwing may nag-iitext sa kanya sa harap ko. jealousy — pero wala naman kaming label. paano ko ipapaliwanag yun?",
            "part3":    "yung nakakatakot? hindi ko alam kung gusto ko siyang mahalin o takot lang akong mawala siya. controversial opinion ko: minsan ang love at attachment ay magkaibang bagay — pero pareho silang masakit.",
            "question": "kayo ba, paano ninyo nalaman kung love na talaga o takot lang na mawalan?",
            "cta":      "Sometimes the problem isn't that you love each other. The problem is, love alone doesn't always make things work. Baka kailangan ninyong both decide to be better — not just feel more. 🤍",
            "closing":  "Dear Viral Video Challenge, okay lang po ba i-share ninyo 'to? Hindi ko kayang kausapin ang mga kaibigan ko tungkol dito — sila rin kilala niya. Gusto ko lang marinig ang totoo mula sa mga taong walang bias sa aming sitwasyon. Kahit isang salita lang ng clarity, malaki na yun para sa akin. 🙏",
        },
        "CHEATING": {
            "hook":     f"p**g ina — tatlong taon. tatlong taon ako nagpakatanga.",
            "part1":    f"{female_age}F ako. nakilala namin sa {place}, nung pareho kaming bata pa't walang alam. {male_age}M siya. mabait, seryoso, laging may masasabi na tama. inakala ko — siya na. tatlong taon. p*ta, tatlong taon.",
            "part2":    "nung nakita ko ang messages sa phone niya — hindi accident. naghahanap ako ng screenshot ng resibo ng grocery namin. at doon ko nakita ang iba. hindi isang beses. hindi dalawang beses. isang taon sila nagkikita. isang taon akong natutulog sa tabi ng isang taong may iba pala. nanlalamig pa rin ako tuwing naalala ko.",
            "part3":    "ang pinaka-masakit? hindi ang kataksilan. ang masakit ay nagmahal pa rin ako kahit alam ko na. at ayaw ko pang aminin yun sa sarili ko — p*ta ano ba ako.",
            "question": "kayo ba — magpapatawad kayo sa ganito? at kung nagpatawad na kayo noon, regret ba kayo o hindi?",
            "cta":      "Cheating is never an accident. It's a choice they made, over and over. You don't have to understand why they did it — you just need to decide what you deserve. 💔",
            "closing":  "Dear Viral Video Challenge, puwede po ba itong i-post? Wala akong matanungan na talagang honest — lahat ng kakilala ko ay may bias. Gusto ko lang marinig ang totoo mula sa mga taong hindi kami kilala. Kahit masakit ang sasabihin ninyo — okay lang. Kailangan ko ng totoo.",
        },
        "HEARTBREAK": {
            "hook":     f"sinabi niyang hindi na siya masaya. tapos umalis. tapos nagpost ng selfie after 3 days.",
            "part1":    f"{female_age}F ako. apat na taon kami. nagsimula sa {place}, sa isang bagay na parang fairy tale noon. nagbigay ako ng lahat — time, pera, pride. literally lahat. at hindi ako nagsisi... noon.",
            "part2":    "'we need to talk.' iyon lang. walang explanation na sapat. 'hindi na daw siya masaya.' hindi kasalanan ko, hindi rin daw kasalanan niya. p*ta — kung walang may kasalanan, bakit ako yung nag-iiyak sa sahig ng CR namin nang mag-isang gabi? sino ang may kasalanan sa sakit na ito?",
            "part3":    "ang hindi ko matanggap: tatlong araw lang pagkatapos niyang umalis, nagpost siya ng smiley selfie. masaya na agad. parang wala. apat na taon... wala. at ako? hindi pa rin ako makakain ng tama. controversial: minsan ang taong pinaka-desperado mong ibalik ay yung taong pinaka-malaya kang pakawalan.",
            "question": "paano kayo gumalaw pagkatapos ng ganitong uri ng breakup — yung para bang tinanggal nila ang isang parte ng inyong sarili?",
            "cta":      "Healing doesn't mean you stop missing them. It means one day, the missing doesn't hurt as much anymore. Bigyan mo ang sarili mo ng oras — hindi rush, hindi pressure. 🥺",
            "closing":  "Dear Viral Video Challenge, sana okay lang i-share ninyo ito. Nahihirapan akong buksan sa mga kaibigan ko — alam nila siya personally at ayaw kong ma-awkward. Mas madali para sa akin na marinig ang pananaw ng mga taong hindi involved. Salamat kung i-share ninyo.",
        },
        "AGE GAP": {
            "hook":     f"sabi ng lahat mali kami. pero wala silang alam kung gaano kami kabuti para sa isa't isa.",
            "part1":    f"{female_age}F ako, {female_age + 12}M siya — 12 taon ang agwat namin, alam ko. nagkakilala kami sa trabaho dito sa {place}. hindi ko sinadyang mahulog — honest. pero siya lang yung tao na nagparamdam sa akin na okay lang ako as I am. hindi siya naghanap ng iba. nandoon lang siya.",
            "part2":    "nung nalaman ng pamilya ko? p*ta. 'manyakis yan.' 'ginagamit ka lang.' 'bata ka pa, hindi mo pa alam ang mundo.' sinasabi nila na protektahan ako nila — pero parang hinuhubaran nila ako ng karapatan kong pumili. ano, kasi bata ako hindi na ba ako pwedeng makaalam kung mahal na mahal ako?",
            "part3":    "controversial ang sasabihin ko: minsan mas matanda ang tao, mas alam niya ang sarili niya. mas alam niya kung ano ang gusto niya. at gusto niya ako. yung real na gusto — hindi yung kind na naghahanap ng iba pagkapagod. pero lahat sila nagbibingi-bingihan dahil sa numero.",
            "question": "sa inyong palagay — ang edad ba talaga ang sukatan ng kung tama o mali ang isang relasyon?",
            "cta":      "Age is just a number — but maturity, intentions, and respect are not. Tingnan mo kung paano ka niya tinrato sa pinakamahirap na sandali. Doon mo malalaman kung totoo siya. 💬",
            "closing":  "Dear Viral Video Challenge, puwede po bang i-post ninyo 'to? Hindi ko kayang kausapin ang pamilya at barkada ko — masyado silang may judgment na bago pa man marinig ang buong kwento. Gusto ko lang marinig ang ibang pananaw. Kahit anong insights, malaki na yun para sa akin. 🙏",
        },
        "COUSIN LOVE": {
            "hook":     f"pinsan ko siya. at kahit ilang ulit ko ito ipinagbawal sa sarili ko... hindi pa rin titigil.",
            "part1":    f"{female_age}F ako. mula pagkabata, palagi kaming magkasama sa family reunions dito sa {place}. siya ang pinaka-comfortable na tao sa aking mundo. pag malungkot ako — siya yung first na nasa isip ko. ngayon mas malalaki na kami... at naging mas mahirap na huwag pansinin.",
            "part2":    "minahal ko siyang hindi ko dapat mahalin. at hindi ko alam kung kailan nagsimula — pero dumating yung araw na nakatingin siya sa ibang babae at nanginginig ang puso ko. p*ta... bakit ito ang nararamdaman ko? lagi ko sinasabi sa sarili ko 'family lang siya' pero parang gusto kong tumawa sa sarili ko sa kasinungalingan.",
            "part3":    "hindi ko sasabihin sa kanya. ever. ito ang pinaka-tiyak na desisyon ko sa buhay — itatanim ko na lang ito nang malalim. pero alam ninyo kung ano ang pinaka-masakit? every family gathering, makikita ko siya. at kailangan ko pa ring ngumiti. kailangan ko pang maging 'pinsan'.",
            "question": "sa inyong palagay — may pagkakataon bang labanan ng isang tao ang ganitong uri ng pakiramdam? o kailangan na lang talaga nilang tanggapin?",
            "cta":      "Some feelings are real, but not all real feelings are meant to be acted on. There's a difference between feeling something and choosing what to do with it. Take your time. ✨",
            "closing":  "Dear Viral Video Challenge, sana i-share po ninyo ito. Talagang hindi ko kaya itong ikwento sa kahit sino — baka pag-usapan pa ako ng buong pamilya. Pero kailangan ko ng makakarinig. Kailangan ko malaman na hindi ako nag-iisa sa ganitong uri ng sakit. Salamat.",
        },
        "THIRD PARTY": {
            "hook":     f"alam ko na may asawa siya. alam ko. pero bakit hindi ko pa rin kaya?",
            "part1":    f"{female_age}F ako. nakilala namin sa {place} — hindi ko alam noon na may iba siya. nung nalaman ko, dapat umalis na ako. dapat. pero nanatili ako, at yun ang pinakamahirap na aminin ngayon.",
            "part2":    "hindi ako bida dito. alam ko yun. pero gusto ko lang sabihin — hindi rin ako basta-basta napasok sa sitwasyong ito. may naramdaman akong tunay. may sinabi siya sa akin na hindi niya sinasabi sa kanya. at maling-mali man ito, yung pakiramdam... totoo.",
            "part3":    "controversial: hindi lahat ng 'third party' ay monster. minsan tao ka lang na nahulog sa maling oras, maling sitwasyon. pero ang sakit ng ginagawa mo sa iba — hindi rin mapapawi ng kahit anong rasyonalisasyon. iyon ang pinaka-masakit na totoo na kailangan kong harapin.",
            "question": "sa inyong palagay — puwede bang maging biktima din ang third party? o dapat walang awa sa kanila?",
            "cta":      "Walang madaling sagot dito. Pero kung may masakit sa puso ngayon — ikaw man ang asawa, ang kabit, o ang nasa gitna — hindi ka nag-iisa. Mag-comment tayo para makatulong sa ating kababayan. 💬",
            "closing":  "Dear Viral Video Challenge, alam ko na maraming mang-judge sa akin. Okay lang. Gusto ko lang marinig ang totoo — hindi yung puro pagmumura, kundi yung tunay na pananaw. Sana po i-post ninyo ito. Kailangan ko ng clarity.",
        },
        "SECRET ADMIRER": {
            "hook":     f"pitong taon ko siyang minahal nang tahimik. pitong taon.",
            "part1":    f"{female_age}F ako. magkaklase kami noon sa {place}. siya yung uri ng tao na hindi mo mapigilan na pagmasdan — hindi kasi siya nagpapanggap. totoo siya. at doon ako unang nahulog. hindi ko sinabi. matagal na akong sanay sa hindi pagsasabi.",
            "part2":    "nakita ko siyang umibig sa iba. nakita ko siyang masaya. at ang trabaho ko sa tabi niya — ngumiti. palakpak para sa kanya. maging 'best friend' na laging nandoon. bawat 'crush ko siya' na ikinukwento niya sa akin — parang karayom na tusok sa dibdib, pero ngumingiti pa rin ako.",
            "part3":    "pitong taon. sa wakas sinabi ko sa kanya — isang sulat, kasi takot akong makita ang mukha niya habang binabasa. ang sagot niya? 'alam ko na.' hindi pa rin ako nakakaalam hanggang ngayon kung mas mabuti o mas masakit ang sagot na iyon.",
            "question": "kayo ba — mas pipiliin ninyong sabihin o itago na lang magpakailanman? alin ang mas hindi makakasakit?",
            "cta":      "Kung mayroon kang sinasabihang 'sana sinabi ko' — baka oras na. Tulungan natin ang ating kababayan — mag-comment ng inyong payo. 💛",
            "closing":  "Dear Viral Video Challenge, sana po i-share ninyo ito. Gusto ko lang malaman kung normal ba ang ganito — ang mahalin nang ganoon katagal nang tahimik. Salamat.",
        },
        "FRIENDZONE": {
            "hook":     f"sabi niya 'ikaw yung pinaka-gets sa akin.' tapos iniyak niya sa akin ang lahat ng heartbreak niya.",
            "part1":    f"{female_age}F ako. tatlong taon na kaming magkaibigan. {male_age}M siya — yung uri ng lalaki na mabait sa lahat pero espesyal ang galawan sa akin. o kaya naman iyon ang inaakala ko. dito sa {place}, lagi kaming magkasama. siya ang hinahanap ko sa lahat ng bagay.",
            "part2":    "nung nagbreak siya sa dati niyang girlfriend, ako ang kinausap niya hanggang 3am. niyakap niya ako nang mahigpit at sabi niya 'sana lahat ng babae ay katulad mo.' p*ta — ano ba yun? anong ibig sabihin nun? kaya ba niya sinabi yun? o 'friend' lang talaga ako sa kanya?",
            "part3":    "hindi ko alam kung kailan ko ito susukuan. baka hindi na. baka hanggang sa manligaw siya ng iba at ako ang maging best man... o bridesmaid. yung tipong ngingiti ka pa rin sa labas pero sa loob mo ay isang bagay lang ang iniisip mo: dapat sana kami.",
            "question": "sa mga nakaranas ng ganito — paano ninyo nalaman kung oras na para lumayo o subok pa ng mas matagal?",
            "cta":      "Hindi lahat ng 'best friend' ay nararapat lang doon. Pero hindi rin lahat ng pagmamahal ay kailangang sabihin para maging totoo. Tulungan natin siya — mag-comment ng inyong payo. 🤍",
            "closing":  "Dear Viral Video Challenge, sana po i-post ninyo ito. Hindi ko kayang kausapin ang mga kaibigan namin — kilala nila siyang pareho. Gusto ko lang marinig ang outsider na pananaw. Salamat.",
        },
        "BALIK-LOVER": {
            "hook":     f"bumalik siya. at yung sinabi kong 'hindi na' — napatunayang kasinungalingan ko sa sarili ko.",
            "part1":    f"{female_age}F ako. nagbreak kami after {random.randint(1,3)} taon. {male_age}M siya. inakala ko na okay na ako — nagtatrabaho na sa {place}, nagsisimulang mag-move on, nagiging masaya na uli. tapos isang message lang niya... lahat bumagsak.",
            "part2":    "'miss kita. mali ako. huwag mo akong bibitawan.' — yun ang sinabi niya. at ang tanong ko sa sarili ko: totoo ba ito o gusto lang niya ng familiar? kasi ganyan siya noon — bumabalik pag nag-iisa. pero baka naman... nagbago na talaga?",
            "part3":    "ang pinakamasakit na katotohanan: hindi ko pa rin siya mahalin nang mas kaunti. kahit gusto ko. kahit subukan ko. p*ta, bakit ganyan ang puso? binibigyan ko siya ng another chance — at takot na takot ako na maging tanga na naman.",
            "question": "sa mga nakaranas ng ganitong 'balik-lover' moment — regret ba kayo o hindi? nagbago ba talaga sila?",
            "cta":      "Second chances are beautiful — but only if the reason they left is gone. Tulungan natin ang ating kababayan na madesisyon. Mag-comment ng inyong tunay na karanasan. 💬",
            "closing":  "Dear Viral Video Challenge, puwede po ba i-share ninyo ito? Gusto ko marinig ang mga nakaranas ng same thing — hindi yung teorya, kundi ang tunay na nangyari. Kailangan ko ng katotohanan ngayon.",
        },
        "ONLINE LOVE": {
            "hook":     f"hindi namin pa nakikita ang isa't isa. pero siya ang pinaka-nakakaalam sa akin sa buong mundo.",
            "part1":    f"{female_age}F ako, {male_age}M siya. nagkita kami sa isang Facebook group tungkol sa mga libro — random, walang intensyon. nagsimula sa isang comment, tapos DM, tapos tawag. ngayon, halos araw-araw na kaming nag-uusap. siya ay nasa ibang lungsod. hindi kami nagkita kahit minsan.",
            "part2":    "pero alam niya ang pangalan ng nanay ko. alam niya kung anong oras ako nagigising. narinig niya na akong umiyak — totoong umiyak, hindi nagpapanggap. at ako rin — narinig ko ang ingay ng bahay niya, ang boses niya pag gising pa lang. paano mo sasabihing hindi totoo iyon?",
            "part3":    "ang tanong na palagi naming iniiwasan: paano kung nagkita tayo at... naiiba? paano kung ang lahat ng ito ay mas maganda sa screen kaysa sa totoo? takot akong malaman ang sagot. pero takot din akong hindi na malaman.",
            "question": "kayo ba naniniwala sa online love? may nakaranas ba sa inyo ng ganitong uri ng koneksyon — at ano ang nangyari?",
            "cta":      "Real feelings don't need a physical address. Pero tulungan natin ang ating kababayan — mag-comment ng inyong pananaw at karanasan. 💙",
            "closing":  "Dear Viral Video Challenge, sana po i-share ninyo ito. Gusto ko malaman kung hindi lang ako sa ganitong sitwasyon. At kung may nakaranas na — ano ang ginawa ninyo?",
        },
        "BROKEN ENGAGEMENT": {
            "hook":     f"ang singsing — nakalagay pa rin sa kahon. hindi ko pa kaya itapon.",
            "part1":    f"{female_age}F ako. dapat kasal na kami nitong taon. lahat naka-plano na — venue sa {place}, entourage, catering, kahit yung vows ko, sinulat ko na. {male_age}M siya. dalawang taon kaming engaged. tapos isang gabi, binago niya ang lahat.",
            "part2":    "sabi niya 'hindi pa siya ready.' hindi pa ready — pagkatapos ng dalawang taon ng engagement, pagkatapos ng lahat ng binalak namin. hindi niya sinabi kung may iba. hindi niya sinabi kung ano talaga. 'hindi pa ready' lang. paano mo tatanggapin iyon?",
            "part3":    "ang singsing ay nasa kahon pa rin sa drawer ko. hindi ko alam kung bakit hindi ko itinapon — baka kasi pag itinapon ko, final na. at hindi pa rin ako handa sa final. pero hindi rin ako handang manatili sa limbo na ito. p*ta, paano ko to tatagalin?",
            "question": "sa mga nakaranas ng broken engagement — paano kayo nakaahon? at paano ninyo natapos ang pag-ikot ng isip ninyo?",
            "cta":      "Ang pagplanong ibinagsak ay isang uri ng pagkawala na hindi laging naiintindihan ng iba. Tulungan natin ang ating kababayan — mag-comment ng inyong puso. 💔",
            "closing":  "Dear Viral Video Challenge, sana po i-post ninyo ito. Wala akong matanungan na hindi nalalaman ang buong kwento. Gusto ko lang marinig ang mga hindi involved — yung mga makakasabi ng totoo.",
        },
        "SUGAR RELATIONSHIP": {
            "hook":     f"binibigyan niya ako ng lahat ng hindi ko kaya. at hindi ko alam kung kasama ba diyan ang pagmamahal.",
            "part1":    f"{female_age}F ako. nakilala namin sa {place}. {male_age}M siya — mas matanda, matagumpay, at mabait sa paraan na hindi ko sanay. sinabi ko sa sarili ko sa simula: transaksyon lang ito. pero hindi ko inakala na magiging ganito kagulo.",
            "part2":    "may oras siya para sa akin. tinatanong niya kung kumain na ako. naalala niya ang mga bagay na sinabi ko minsan lang. at ngayon hindi ko na alam kung nagmamahal na siya sa akin o ginagawa lang niya ito dahil kaya niya. at ang mas nakakatakot — hindi ko na alam kung ano ang nararamdaman ko.",
            "part3":    "controversial na sasabihin ko: hindi lahat ng sugar relationship ay walang tunay na damdamin. pero hindi rin lahat ng tunay na damdamin ay sapat na basehan ng isang relasyon. at habang tinatanggap ko ang mga regalo niya, tinatanong ko ang sarili ko — binibili ba niya ang aking oras, o ang aking pagmamahal?",
            "question": "sa inyong palagay — puwede bang lumabas ang tunay na pagmamahal sa ganitong uri ng setup? o lagi na lang itong komplikado?",
            "cta":      "Walang simpleng sagot dito — at lahat tayo may karapatang marinig ang iba't ibang pananaw. Huwag hatulan — tulungan natin ang ating kababayan. Mag-comment ng inyong saloobin. 💬",
            "closing":  "Dear Viral Video Challenge, sana po i-share ninyo ito nang walang judgment. Alam ko hindi ito popular. Pero totoo ito, at kailangan ko ng honest na pananaw mula sa mga hindi kilala ang aming sitwasyon.",
        },
        "SITUATIONSHIP": {
            "hook":     f"'ano tayo?' — yung tanong na pareho naming alam ang sagot pero pareho ring ayaw sabihin.",
            "part1":    f"{female_age}F ako, {male_age}M siya. dito sa {place}, ilang beses na kaming nag-uwian, nagtawagan hanggang umaga, nagkamay nang mahigpit sa cinema. pero kung tatanungin mo kung 'kami ba' — walang malinaw na sagot. 'ganyan talaga kami' daw.",
            "part2":    "p*ta ang 'ganyan talaga kami.' kasi ang 'ganyan' ay ibig sabihin — pwede siyang makipagdate sa iba at wala akong karapatang masaktan. pwede akong mag-introduce ng iba at siya ay pagtitinginan lang ako. paano ka mabubuhay sa grey area na yan nang walang masisira?",
            "part3":    "gusto kong itanong sa kanya — pero takot ako sa sagot. kasi kung 'wala tayo' ang sagot, mawawala ang lahat. at mas matakot akong mawala siya kaysa manatili sa limbo na ito. pero hanggang kailan? hanggang kailan ako magsasabing okay lang ito?",
            "question": "kayo ba — mas pipiliin ninyong tanungin at riskin ang lahat, o titiisin ang situationship para hindi masira ang meron?",
            "cta":      "Deserves kang ng isang taong sigurado sa iyo. Tulungan natin ang ating kababayan — mag-comment ng inyong advice at karanasan. 💛",
            "closing":  "Dear Viral Video Challenge, sana po i-post ninyo ito. Nahihirapan akong pag-usapan ito sa mga kaibigan ko — kilala nila kaming dalawa. Gusto ko lang marinig ang totoo mula sa labas.",
        },
        "ASAWA VS KABIT": {
            "hook":     f"nalaman ko sa isang text. isang text lang — at lahat ng nagtayo ko sa loob ng {random.randint(5,15)} taon, gumuho.",
            "part1":    f"{female_age}F ako. {random.randint(5,15)} taon kaming kasal. may anak kami. nagtatrabaho kami pareho dito sa {place}. inakala ko — maayos tayo. hindi perpekto, pero maayos. tapos yung text. hindi niya basta-basta naiwan ang phone — sinabihan niya akong hawakan habang nagbabago siya. at naroon ito.",
            "part2":    "hindi ko sinabi kaagad. tatlong araw akong nagdala ng sikreto — naghanda pa ako ng pagkain, natulog sa tabi niya, ngumiti sa mga bata. tatlong araw na alam ko na pero hindi pa siya. nang sabi ko sa kanya — hindi siya tumanggi. sinabi niya lang: 'sori.' p*ta. 'sori.'",
            "part3":    "ang tanong na hindi ko masagot: mananatili ba ako para sa mga bata, o lalayo para sa sarili ko? kasi kahit anong desisyon ang gawin ko — may masisira. at kahit galit na galit ako sa kanya ngayon — mahal ko pa rin siyang p*ta. yun ang pinakamasama.",
            "question": "sa mga nakaranas ng ganito — paano kayo nagdesisyon? at kung mag-iwan kayo ulit ng pagkakataon — paano ninyo naayos ang tiwala?",
            "cta":      "Walang tamang sagot sa ganito — at hindi mo dapat pinagdesisyon ang sarili mo nang mag-isa. Tulungan natin ang ating kababayan — mag-comment ng inyong tunay na karanasan. 💔",
            "closing":  "Dear Viral Video Challenge, sana po i-post ninyo ito. Wala akong mapag-usapan — lahat ng kaibigan ko ay kilala kami pareho. Kailangan ko ng outsider na pananaw. Kahit masakit — kailangan ko ng totoo.",
        },
        "IN-LAW CONFLICT": {
            "hook":     f"mahal ko siya nang buo. pero ang pamilya niya — parang aktibong sinisigurado nilang hindi ito gagana.",
            "part1":    f"{female_age}F ako, {male_age}M siya. dalawang taon na kaming magkasama dito sa {place}. siya ay mabait, mahal niya ako — sigurado ako doon. ang problema ay hindi kami dalawa lang sa relasyong ito. ang nanay niya ay palaging kasama.",
            "part2":    "sinasabi ng nanay niya na hindi ako angkop. hindi daw ako galing sa 'magandang pamilya.' tinatanggal niya ang mga regalo ko sa bahay nila. sinasabihan siya na huwag akong pakasalan. at ang pinaka-masakit? inilalagay niya sa ulo ng anak niya na kailangan niyang pumili — at hindi pa rin siya pumipili nang malinaw.",
            "part3":    "hindi ko siya hinihiling na tanggihan ang pamilya niya. mahal ko siya nang sapat para hindi ko iyon hihilingin. pero kailangan ko siyang pumili para sa amin — hindi laban sa pamilya niya, kundi para sa atin. at hindi ko alam kung kayang gawin iyon ng taong pinalaki sa ganyang kultura.",
            "question": "sa mga nakaranas ng in-law conflict — paano ninyo nasolusyunan ito? o paano ninyo nalaman kung oras na para lumayo?",
            "cta":      "Ang pag-ibig ay hindi lang para sa dalawa — minsan kailangan nilang harapin ang buong pamilya. Tulungan natin ang ating kababayan — mag-comment ng inyong karanasan. 🤍",
            "closing":  "Dear Viral Video Challenge, sana po i-share ninyo ito. Hindi ko kayang pag-usapan ito sa mga kaibigan — alam nila ang pamilya niya. Kailangan ko ng neutral na pananaw. Salamat.",
        },
        "LONG DISTANCE": {
            "hook":     f"lahat sabi 'kaya ninyo 'yan.' pero sila hindi nararamdaman ang gabi na mag-isa ka at ang tawag ay hindi nasasagot.",
            "part1":    f"{female_age}F ako, {male_age}M siya. nagsimula kaming mag-LDR nung lumipat siya ng trabaho sa ibang bansa — kailangan, hindi choice. dito sa {place} ako naiwan. sabi namin: anim na buwan lang. tapos naging isang taon. tapos naging dalawa.",
            "part2":    "ang simula — may schedule tayo ng tawag. may 'goodnight' tayo lagi. tapos dahan-dahang nawala ang schedule. 'busy lang' palagi. at ang tanong na hindi ko sinasabi nang malakas: busy ba talaga siya, o unti-unting lumalayo na?",
            "part3":    "ang pinakamasakit na bagay sa LDR — hindi ang distansya. ang masakit ay ang pakiramdam na kahit nasa tawag kayo, may distansya pa rin. parang nandoon ang katawan niya sa screen — pero hindi na nandoon ang tao na mahal mo. at hindi mo alam kung kailan nagsimula ang pagbabago.",
            "question": "sa mga nakasecond na LDR — ano ang nagpanatili sa inyo? at may point ba na sabi ninyo 'hindi na talaga kaya'?",
            "cta":      "Distansya ay hindi palaging hadlang — pero hindi rin ito laging malalampasan. Tulungan natin ang ating kababayan — mag-comment ng inyong totoong karanasan sa LDR. ✈️",
            "closing":  "Dear Viral Video Challenge, sana po i-post ninyo ito. Gusto ko marinig ang mga nakaranas ng same — hindi yung 'kaya ninyo,' kundi yung totoo. Yung ugly truth ng LDR. Salamat.",
        },
        "CHILDHOOD SWEETHEART": {
            "hook":     f"sampung taon ang nakaitan. tapos nagtext siya. at parang wala ni isang araw ang lumipas.",
            "part1":    f"{female_age}F ako. siya yung first love ko — noong bata pa kami dito sa {place}. {male_age}M siya ngayon. nagbreak kami nung high school, yung uri ng breakup na hindi mo pa lubos na nauunawaan pero lubos na nakakasakit. akala ko — tapos na. sampung taon nang tapos na.",
            "part2":    "isang araw, nag-message siya. 'kumusta ka na?' — tatlong salita. tatlong salita at parang bumalik lahat ng nakalimutan ko. nagkita kami. iba na siya — mas mature, mas kalmado. pero yung ngiti? yung paraan ng pakikinig niya? yun — yun pa rin. at doon nagsimula ang problema ko.",
            "part3":    "kasi hindi lang first love ang nararamdaman ko ngayon. nararamdaman ko rin ang lahat ng dating sakit. ang lahat ng dahilan kung bakit nagbreak kami. at ang takot — na baka ulitin namin ang lahat. pero baka naman... nagbago na tayo. baka naman tama na ang timing ngayon.",
            "question": "sa mga nakaranas ng 'second chance' sa first love — mas maganda ba ang ending kaysa dati? o mas masakit?",
            "cta":      "First love never really leaves — they just make room. Tulungan natin ang ating kababayan na malaman kung sulit ang another try. Mag-comment ng inyong karanasan. 🌸",
            "closing":  "Dear Viral Video Challenge, sana po i-share ninyo ito. Gusto ko marinig ang mga nakaranas ng ganitong reunion — yung totoo, hindi yung pelikula. Salamat.",
        },
    }
    return stories.get(category, stories["HEARTBREAK"])


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
    ("closing",  False, "closing"),  # Slide 7: sender's note to the page
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

    # (Category pill removed — looked automated; story speaks for itself)

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
