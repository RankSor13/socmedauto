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

# Brand colors (Boiling Waters style)
ANON_ORANGE     = (220, 95, 35)
C_WHITE         = (255, 255, 255)
C_OFFWHITE      = (240, 235, 230)
C_MUTED         = (185, 175, 165)
C_DARK_BG       = (15,  12,  10)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LoveStoriesBot/1.0)"}

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
]

CATEGORY_HASHTAGS = {
    "LOVE STORY":    "#LoveStory #Pagmamahal #RelationshipGoals #LoveConfessionsPH #TotooNgPuso",
    "CHEATING":      "#Cheating #Kabit #Infidelity #LoveAndPain #RealTalk #Pagtataksil",
    "STRUGGLES":     "#RelationshipStruggles #LDR #LoveHurts #MahalKitaPeroBakit #BagalKo",
    "ADVICE":        "#RelationshipAdvice #LoveAdvice #TanongSaInyo #HelpMe #SabihinMo",
    "HIDDEN DESIRE": "#HiddenDesire #SecretFeeling #NaramdamanKo #HindiKoMasabi #Gusto",
    "CONFESSION":    "#Confession #Pagtatapat #AnonymousStory #LoveConfession #Totoo",
    "HEARTBREAK":    "#Heartbreak #SakitNgPuso #MovingOn #LoveHurts #Masakit #Nawala",
}

CATEGORY_PHOTO_KEYWORDS = {
    "LOVE STORY":    "couple-romantic",
    "CHEATING":      "sad-woman-alone",
    "STRUGGLES":     "woman-thinking-sad",
    "ADVICE":        "person-contemplating",
    "HIDDEN DESIRE": "mysterious-woman",
    "CONFESSION":    "sad-woman-writing",
    "HEARTBREAK":    "woman-crying-alone",
}

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
def draw_anon_badge(draw: ImageDraw, x: int, y: int):
    """
    Draw the orange circle + incognito spy icon + "Anonymous member" text.
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

    # ── "Anonymous member" text ──
    font = get_font(38, bold=False)
    draw.text((cx + r + 22, cy), "Anonymous member",
              font=font, anchor="lm", fill=C_WHITE)


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
def fetch_background_photo(category: str) -> Image.Image:
    """Download a moody background photo from Unsplash (no API key needed)."""
    keyword = CATEGORY_PHOTO_KEYWORDS.get(category, "sad-woman-alone")
    urls_to_try = [
        f"https://source.unsplash.com/{IMG_W}x{IMG_H}/?{keyword}",
        f"https://source.unsplash.com/{IMG_W}x{IMG_H}/?sad,woman,alone",
        f"https://source.unsplash.com/{IMG_W}x{IMG_H}/?person,dark,moody",
    ]
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img = img.resize((IMG_W, IMG_H), Image.LANCZOS)
                print(f"  ✅ Background photo fetched ({keyword})")
                return img
        except Exception as e:
            print(f"  ⚠️  Photo fetch failed ({url[:60]}): {e}")

    # Fallback: dark gradient background
    print("  ℹ️  Using dark gradient fallback background.")
    bg = Image.new("RGB", (IMG_W, IMG_H), C_DARK_BG)
    draw = ImageDraw.Draw(bg)
    for y in range(IMG_H):
        alpha = int(255 * (1 - y / IMG_H) * 0.3)
        draw.line([(0, y), (IMG_W, y)], fill=(30 + alpha, 20 + alpha, 15 + alpha))
    return bg


def apply_dark_overlay(bg: Image.Image) -> Image.Image:
    """Apply gradient dark overlay so text is readable on any photo."""
    overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    for y in range(IMG_H):
        frac = y / IMG_H
        if frac < 0.12:
            alpha = 140           # top: slightly dark for badge
        elif frac < 0.30:
            alpha = int(140 + (frac - 0.12) / 0.18 * 30)  # gradual
        elif frac < 0.42:
            alpha = int(170 + (frac - 0.30) / 0.12 * 60)  # ramps up
        else:
            alpha = 210           # bottom 58%: heavy dark for text
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
    "cta":        "1 short CTA line. Ask to comment, share, or follow. Keep it natural and Taglish.",
}

CATEGORY_PROMPTS = {
    "LOVE STORY":    "a sweet but emotional Tagalog love story about a couple navigating early relationship challenges",
    "CHEATING":      "a heartbreaking Tagalog story about discovering a partner's infidelity",
    "STRUGGLES":     "a relatable Tagalog story about relationship struggles like long distance, insecurity, or poor communication",
    "ADVICE":        "a Tagalog anonymous post asking for honest advice about a confusing relationship situation",
    "HIDDEN DESIRE": "a Tagalog story about secret feelings for someone — unrequited love or a crush the person can't confess",
    "CONFESSION":    "a Tagalog anonymous confession about a past mistake or hidden truth in a relationship",
    "HEARTBREAK":    "a raw emotional Tagalog story about a painful breakup and the struggle to move on",
}


def generate_story(category: str) -> dict:
    """Generate a multi-slide Taglish love story using Groq."""
    if not GROQ_API_KEY:
        print("  ⚠️  No GROQ_API_KEY — using fallback story.")
        return _fallback_story(category)

    prompt = f"""You are writing for a Filipino Facebook page similar to Boiling Waters PH.
Write {CATEGORY_PROMPTS.get(category, 'a relatable Tagalog relationship story')}.

The writing style is:
- Natural Taglish (mix of Tagalog and English, the way Filipinos actually text)
- Feels like a real anonymous submission from a real person
- Emotional, raw, and relatable
- Age and gender can vary (common formats: "22F and 27M" etc.)
- Avoid being too dramatic or formal — keep it conversational

Respond ONLY with valid JSON (no markdown, no extra text) matching this exact schema:
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
            "cta":      "I-share ito kung kaya mong i-relate! 💬 At follow na para sa mas maraming stories."
        },
        "CHEATING": {
            "hook":     "Nalaman ko sa isang chat ang lahat — at hindi ko inaasahan na siya pala yun...",
            "part1":    "25F ako. Tatlong taon kaming magkasama. Lagi akong nagtiwala sa kanya kahit may mga kaibigan akong nagsasabi na mag-ingat ako.",
            "part2":    "Isang gabi, nagpahiram ako ng phone niya para mag-call. Nakita ko ang messages. Matagal na pala silang nag-uusap ng isa pang babae.",
            "part3":    "Hindi ko malaman kung mananatili o lalayo. Nasaktan ako hindi lang sa ginawa niya, kundi sa lahat ng sinabi niyang mahal niya ako.",
            "question": "Kayo ba, magpapatawad kaya kayo sa ganitong sitwasyon?",
            "cta":      "Mag-comment ng iyong opinion. Lahat ng naramdaman mo ay valid. 💔"
        },
        "HEARTBREAK": {
            "hook":     "Apat na taon — tapos biglang 'we need to talk' na lang...",
            "part1":    "23F ako. Nagmahal ako nang buong-buo. Inakala ko na siya na ang magiging katabi ko habambuhay.",
            "part2":    "Sabi niya kailangan niya ng time para sa sarili niya. Na hindi na siya masaya. Na hindi niya kasalanan, hindi rin daw kasalanan ko.",
            "part3":    "Pero bakit parang kasalanan ko ang sakit? Bakit ako ang nag-iingat ng mga alaala namin habang siya ay sige lang?",
            "question": "Paano kayo nakakaalis sa ganito? Anong tumutulong sa inyo para gumalaw?",
            "cta":      "Para sa lahat ng may masakit sa puso ngayon — hindi ka nag-iisa. 🤍 Follow us."
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
                 hook_only: bool = False) -> Image.Image:
    """Create one static Boiling Waters-style slide."""
    img = apply_dark_overlay(bg)
    draw = ImageDraw.Draw(img)

    pad_x = 58   # left/right padding

    # ── Anonymous member badge (top-left) ──
    draw_anon_badge(draw, x=pad_x, y=72)

    # ── Category label pill (top-right) ──
    cat_font = get_font(30, bold=True)
    cat_text = f"  {category}  "
    cat_w = int(draw.textlength(cat_text, font=cat_font)) + 20
    cat_x = IMG_W - pad_x - cat_w
    cat_y = 72
    draw.rounded_rectangle([(cat_x, cat_y), (cat_x + cat_w, cat_y + 52)],
                             radius=10, fill=ANON_ORANGE)
    draw.text((cat_x + cat_w // 2, cat_y + 26), category,
              font=cat_font, anchor="mm", fill=C_WHITE)

    # ── HOOK HEADLINE (large bold italic) ──
    headline_y = int(IMG_H * 0.36)
    hook_text  = story.get("hook", "")

    if hook_only:
        # Slide 1: Very large hook, no body
        h_font = get_font(76, bold=True, italic=True)
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

    # Right: circle logo + page name
    logo_r  = 36
    logo_cx = IMG_W - pad_x - logo_r
    logo_cy = brand_y + logo_r + 5
    draw.ellipse([(logo_cx - logo_r, logo_cy - logo_r),
                  (logo_cx + logo_r, logo_cy + logo_r)],
                  fill=ANON_ORANGE)
    # Initials in circle
    init_font = get_font(24, bold=True)
    words     = PAGE_NAME.replace("_", " ").split()
    initials  = "".join(w[0].upper() for w in words[:2]) or PAGE_NAME[:2].upper()
    draw.text((logo_cx, logo_cy), initials, font=init_font,
              anchor="mm", fill=C_WHITE)
    # Page name text next to circle
    pname_font = get_font(28, bold=True)
    draw.text((logo_cx - logo_r - 12, logo_cy),
              PAGE_NAME.upper(), font=pname_font,
              anchor="rm", fill=C_OFFWHITE)

    return img


def create_all_slides(story: dict, category: str) -> list[Image.Image]:
    """Create all 6 slides for the reel."""
    print(f"  📷 Fetching background photo for {category}…")
    bg = fetch_background_photo(category)

    images = []
    for i, (slide_type, hook_only, body_key) in enumerate(SLIDE_CONFIGS):
        img = create_slide(slide_type, story, bg, category,
                           body_key=body_key, hook_only=hook_only)
        images.append(img)
        print(f"   Slide {i+1}/{len(SLIDE_CONFIGS)} ({slide_type}) ✓")
    return images


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO ASSEMBLY (static frames — no animation)
# ─────────────────────────────────────────────────────────────────────────────
def build_reel(images: list, output_path: str) -> str:
    print(f"\n🎬 Stitching {len(images)} static slides into video…")
    clips = []
    for i, pil_img in enumerate(images):
        arr  = np.array(pil_img)
        clip = ImageClip(arr).set_duration(SLIDE_DURATION).set_fps(FPS)
        clips.append(clip)
        print(f"   Clip {i+1}/{len(images)} prepared ✓")

    video = concatenate_videoclips(clips, method="compose")

    print(f"\n🎞️  Rendering MP4 → {output_path}…")
    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio=False,
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
        f"Follow @{PAGE_NAME} para sa mas maraming love stories at confessions every day! 💌\n\n"
        f"{hashtags} #AnonymousStory #LoveConfessionsPH #PilipinoLoveStory"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  💌 Love Stories Facebook REEL Bot — Boiling Waters Style")
    print("=" * 60)

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
    build_reel(images, OUTPUT_PATH)

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
