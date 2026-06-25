"""
post_fruit_benefits_ig.py
=========================
Benefits of Fruits — Instagram Carousel Poster

Required GitHub Secrets:
  IG_USER_ID           — Instagram Business/Creator User ID (posting account)
  FB_ACCESS_TOKEN      — Facebook Page Access Token (posting account)
  IMGBB_API_KEY        — Free at imgbb.com
  PAGE_NAME            — Your IG handle WITHOUT the @
  PIXABAY_API_KEY      — Free at https://pixabay.com/api/docs/

Optional:
  USDA_API_KEY         — Free at https://api.data.gov/signup/
  GROQ_API_KEY         — Free at console.groq.com
"""

import os, sys, json, random, requests, re, time, base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO
from datetime import datetime

def strip_emojis(text: str) -> str:
    """Remove emoji characters that Poppins can't render."""
    import unicodedata
    result = []
    for char in text:
        cp = ord(char)
        # Skip emoji ranges
        if (0x1F300 <= cp <= 0x1FBFF or   # Misc symbols, emoticons, transport, etc.
            0x2600  <= cp <= 0x27BF or    # Misc symbols & dingbats
            0xFE00  <= cp <= 0xFE0F or    # Variation selectors
            0x1F900 <= cp <= 0x1F9FF or   # Supplemental symbols
            cp in (0x200D, 0xFE0F)):      # ZWJ, variation selector
            continue
        result.append(char)
    return "".join(result).strip()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
IG_USER_ID      = os.environ["IG_USER_ID"]
FB_ACCESS_TOKEN = os.environ["FB_ACCESS_TOKEN"]
IMGBB_API_KEY   = os.environ["IMGBB_API_KEY"]
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
USDA_API_KEY    = os.environ.get("USDA_API_KEY", "")
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
PAGE_NAME       = os.environ.get("PAGE_NAME", "fruitfacts.daily")

IMG_W, IMG_H    = 1080, 1080
IG_BASE         = "https://graph.facebook.com/v21.0"

FONT_BOLD_URL   = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
FONT_REG_URL    = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf"
FONT_BOLD_PATH  = "/tmp/Poppins-Bold.ttf"
FONT_REG_PATH   = "/tmp/Poppins-Regular.ttf"
FONT_EMOJI_URL  = "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf"
FONT_EMOJI_PATH = "/tmp/NotoColorEmoji.ttf"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FruitBenefitsBot/1.0)"}

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCE DATABASE — Fruits & Vegetables
# ─────────────────────────────────────────────────────────────────────────────
FRUITS = [
    {
        "name": "Orange", "emoji": "🍊", "category": "CITRUS", "accent_rgb": (251, 146, 60),
        "slide_searches": ["orange fruit whole", "orange fruit sliced", "orange juice fresh", "orange tree fruit", "citrus oranges pile"],
        "wikipedia": "Orange_(fruit)", "usda_fdc_id": 747447,
        "angles": [
            {"hook": "One orange gives you MORE than a full day's Vitamin C.", "theme": "IMMUNITY", "label": "IMMUNITY BOOST", "points": ["116% daily Vitamin C in a single orange", "Stimulates white blood cell production", "Shortens cold duration by 8-14%", "Flavonoids fight respiratory infections", "Vitamin A strengthens mucous membranes"], "tip": "Eat the white pith — it contains the most flavonoids!"},
            {"hook": "Oranges can lower your blood pressure in just 4 weeks.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Potassium (326mg) relaxes blood vessels", "Hesperidin lowers diastolic BP by 5mmHg", "Fiber (3g) reduces LDL cholesterol", "Folate reduces homocysteine — heart risk marker", "Anti-inflammatory compounds protect arteries"], "tip": "Drink fresh-squeezed, not from concentrate — 40% more hesperidin!"},
            {"hook": "Oranges protect your skin from UV damage from the inside.", "theme": "SKIN", "label": "SKIN & BEAUTY", "points": ["Vitamin C builds collagen — firmer, younger skin", "Beta-carotene acts as internal UV protection", "Antioxidants prevent wrinkles & age spots", "Vitamin A speeds up skin cell turnover", "Hydration (87% water) keeps skin plump"], "tip": "Pair with almonds — vitamin E + C = 4x more antioxidant power!"},
            {"hook": "Oranges are one of the best fruits for preventing kidney stones.", "theme": "KIDNEY", "label": "KIDNEY HEALTH", "points": ["Citrate binds calcium — prevents stone formation", "Potassium reduces calcium excretion in urine", "87% water content keeps kidneys flushed", "Vitamin C reduces oxidative stress on kidneys", "Better than lemonade for stone prevention!"], "tip": "Fresh orange juice has MORE citrate than lemon juice — the stone fighter!"},
        ],
    },
    {
        "name": "Lemon", "emoji": "🍋", "category": "CITRUS", "accent_rgb": (250, 230, 80),
        "slide_searches": ["lemon fruit whole", "lemon sliced wedges", "fresh lemonade", "lemon tree yellow", "lemon halves"],
        "wikipedia": "Lemon", "usda_fdc_id": 9153,
        "angles": [
            {"hook": "Lemon water every morning can transform your digestion in 7 days.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["Citric acid stimulates stomach acid production", "Pectin fiber feeds beneficial gut bacteria", "Encourages bile production for fat breakdown", "Relieves bloating and water retention", "Warm lemon water activates digestive enzymes"], "tip": "Use WARM water, not cold — it activates the citric acid faster!"},
            {"hook": "Lemons have more sugar than strawberries — but they're still a superfood.", "theme": "NUTRITION", "label": "NUTRITION MYTHS", "points": ["1 lemon = 88% daily Vitamin C", "Only 17 calories per whole lemon", "Citric acid helps your body absorb iron from food", "Limonene in the peel fights cancer cells", "More potassium per calorie than grapes!"], "tip": "Freeze lemons and grate the whole thing — the peel has 10x more nutrients!"},
            {"hook": "The vitamin C in one lemon equals 3 days of antioxidant protection.", "theme": "IMMUNITY", "label": "IMMUNITY", "points": ["88% daily Vitamin C per lemon", "Antimicrobial properties kill oral bacteria", "Potassium supports nerve-brain communication", "Saponins have antimicrobial & antiviral effects", "Reduces phlegm and relieves sore throat"], "tip": "Gargle warm lemon water — it kills 90% of throat bacteria on contact!"},
            {"hook": "Lemon peel contains a compound that dissolves cholesterol in arteries.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Hesperidin in peel lowers LDL cholesterol", "Vitamin C prevents artery wall damage", "Potassium regulates heart rhythm", "Flavonoids reduce blood vessel inflammation", "Di-limonene dissolves arterial plaque buildup"], "tip": "Zest lemon peel into salads and tea — that's where hesperidin lives!"},
        ],
    },
    {
        "name": "Strawberry", "emoji": "🍓", "category": "BERRY", "accent_rgb": (244, 63, 94),
        "slide_searches": ["strawberry fruit whole red", "strawberry sliced", "bowl fresh strawberries", "strawberry field", "strawberry smoothie pink"],
        "wikipedia": "Strawberry", "usda_fdc_id": 9316,
        "angles": [
            {"hook": "Strawberries have MORE Vitamin C than oranges — per serving.", "theme": "IMMUNITY", "label": "IMMUNITY", "points": ["149% daily Vitamin C per cup — beats oranges!", "Ellagic acid neutralizes carcinogens on contact", "Anthocyanins reduce inflammation markers 18%", "Manganese activates superoxide dismutase enzyme", "Vitamin B6 supports antibody production"], "tip": "Eat strawberries within 2 days of purchase — they lose 30% Vitamin C by day 3!"},
            {"hook": "Women who eat 3+ servings of strawberries weekly have 34% less heart risk.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Anthocyanins lower blood pressure by 8%", "Polyphenols reduce LDL oxidation (artery clogging)", "Potassium (220mg) regulates heart rhythm", "Fiber (3g) lowers total cholesterol", "Quercetin reduces dangerous blood clots"], "tip": "3 servings/week = only 1.5 cups — that's all it takes for heart protection!"},
            {"hook": "Strawberries rank in the top 10 antioxidant-rich foods on Earth.", "theme": "ANTI-AGING", "label": "ANTI-AGING", "points": ["ORAC score: 4302 — top 10 of all foods", "Vitamin C builds collagen — reverses wrinkle formation", "Ellagic acid prevents collagen breakdown", "Alpha-hydroxy acid (AHA) naturally exfoliates skin", "Folate supports cell repair and regeneration"], "tip": "Mash strawberries + honey = DIY anti-aging face mask. Leave on 15 min!"},
            {"hook": "Strawberries can regulate blood sugar better than some medications.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Glycemic Index of only 40 — safe for diabetics", "Polyphenols slow carbohydrate digestion", "Improves insulin sensitivity by 24%", "Fiber prevents glucose spikes after meals", "Reduces HbA1c (3-month blood sugar average)"], "tip": "Eat strawberries AFTER a carb-heavy meal — they blunt the sugar spike by 36%!"},
        ],
    },
    {
        "name": "Blueberry", "emoji": "🫐", "category": "BERRY", "accent_rgb": (99, 102, 241),
        "slide_searches": ["blueberry fruit whole", "handful blueberries", "bowl fresh blueberries", "blueberry smoothie", "blueberry bush"],
        "wikipedia": "Blueberry", "usda_fdc_id": 9052,
        "angles": [
            {"hook": "Blueberries can improve your MEMORY in just 12 weeks — Harvard study.", "theme": "BRAIN", "label": "BRAIN POWER", "points": ["Anthocyanins cross the blood-brain barrier", "Improves delayed memory by 15% in older adults", "Increases BDNF — brain's growth hormone", "Protects neurons from oxidative stress damage", "1 cup/day = measurable cognitive improvement"], "tip": "Eat 1 cup daily — that's the exact dose used in the Harvard memory study!"},
            {"hook": "Blueberries have the HIGHEST antioxidant level of all popular fruits.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANTS", "points": ["ORAC score: 9621 — #1 among popular fruits", "Reduces DNA damage by 20% in just 4 weeks", "Pterostilbene activates longevity gene SIRT1", "Fights oxidative stress better than vitamin E", "Wild blueberries have 2x more antioxidants than farmed"], "tip": "Buy WILD blueberries (frozen is fine) — they have DOUBLE the antioxidants!"},
            {"hook": "Blueberries can lower your bad cholesterol by 27% — no drugs needed.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Lowers LDL cholesterol by up to 27%", "Reduces blood pressure by 6% systolic", "Improves endothelial function (blood vessel health)", "Anti-inflammatory reduces arterial plaque buildup", "Anthocyanins reduce heart attack risk by 32%"], "tip": "Eat blueberries with oats — the fiber + antioxidants double the heart benefit!"},
            {"hook": "Blueberries after exercise cut muscle damage recovery time in half.", "theme": "RECOVERY", "label": "EXERCISE RECOVERY", "points": ["Reduces exercise-induced muscle damage by 50%", "Anti-inflammatory lowers DOMS (soreness)", "Anthocyanins speed up muscle repair signaling", "Vitamin C reduces cortisol from intense exercise", "Manganese supports bone remodeling post-workout"], "tip": "Eat blueberries within 30 min after workout — that's when muscles absorb nutrients fastest!"},
        ],
    },
    {
        "name": "Banana", "emoji": "🍌", "category": "TROPICAL", "accent_rgb": (250, 204, 21),
        "slide_searches": ["banana fruit whole yellow", "banana peeled", "banana smoothie healthy", "banana tree bunch", "banana slices plate"],
        "wikipedia": "Banana", "usda_fdc_id": 778089,
        "angles": [
            {"hook": "Bananas are a natural antidepressant — science confirms it.", "theme": "MOOD", "label": "MOOD & MENTAL HEALTH", "points": ["Tryptophan converts to serotonin — the happy hormone", "Vitamin B6 helps synthesize dopamine & norepinephrine", "Magnesium relaxes muscles and calms anxiety", "Natural sugar provides steady brain energy", "Potassium oxygenates the brain — clearer thinking"], "tip": "Eat a banana when stressed — it raises serotonin levels within 45 minutes!"},
            {"hook": "A banana 30 minutes before exercise outperforms sports drinks for energy.", "theme": "ATHLETIC", "label": "ATHLETIC PERFORMANCE", "points": ["3 natural sugars: sucrose, fructose, glucose — timed release", "More potassium than most sports drinks", "Prevents muscle cramps during exercise", "Dopamine from vitamin B6 improves focus & drive", "Less inflammatory than 6% sugar sports drinks"], "tip": "Eat banana + peanut butter 30 min pre-workout — the #1 combo for sustained energy!"},
            {"hook": "Green bananas are one of the best foods for your gut microbiome.", "theme": "GUT HEALTH", "label": "GUT HEALTH", "points": ["Resistant starch feeds Bifidobacteria — your gut's best friend", "Acts as a prebiotic — grows beneficial bacteria 57%", "Produces butyrate — heals gut lining inflammation", "Less sugar than ripe bananas — gut-friendly", "Pectin normalizes bowel function (both diarrhea & constipation)"], "tip": "Slightly GREEN bananas have 20x more resistant starch than fully ripe ones!"},
            {"hook": "Bananas can help you fall asleep faster than some sleep aids.", "theme": "SLEEP", "label": "SLEEP AID", "points": ["Tryptophan → serotonin → melatonin (sleep hormone)", "Magnesium relaxes muscles — helps you unwind", "Potassium prevents night cramps and restlessness", "Carbohydrates help tryptophan cross the blood-brain barrier", "Vitamin B6 converts tryptophan to serotonin faster"], "tip": "Eat a banana 1 hour before bed — it's nature's sleeping pill!"},
        ],
    },
    {
        "name": "Mango", "emoji": "🥭", "category": "TROPICAL", "accent_rgb": (245, 158, 11),
        "slide_searches": ["mango fruit whole ripe", "mango fruit sliced", "mango smoothie tropical", "mango on tree", "ripe mango close up"],
        "wikipedia": "Mango", "usda_fdc_id": 9174,
        "angles": [
            {"hook": "Mango polyphenols can suppress breast and colon cancer cells in lab studies.", "theme": "CANCER", "label": "CANCER-FIGHTING", "points": ["Polyphenols suppress breast cancer cell growth", "Lupeol targets colon cancer cells selectively", "Gallotannins induce cancer cell death (apoptosis)", "Beta-carotene reduces lung cancer risk by 25%", "Mangiferin inhibits tumor blood vessel formation"], "tip": "Eat mango with black pepper — piperine increases polyphenol absorption by 200%!"},
            {"hook": "Mango is called the 'king of fruits' — and it protects your eyes like royalty.", "theme": "EYES", "label": "EYE HEALTH", "points": ["67% daily Vitamin A per cup — vision superhero", "Lutein & zeaxanthin filter harmful blue light", "Beta-cryptoxanthin prevents age-related macular degeneration", "Vitamin C reduces cataract risk by 20%", "Protects cornea from UV and oxidative damage"], "tip": "1 cup of mango = same Vitamin A as 2 cups of carrots — but way tastier!"},
            {"hook": "Mango contains digestive enzymes that work like a natural digestive supplement.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["Amylases break down complex carbs for easy absorption", "Mangiferin protects gut lining from inflammation", "3g fiber per cup promotes regular bowel movements", "Relieves constipation better than fiber supplements", "Enzymes help digest proteins — great after heavy meals"], "tip": "Eat mango AFTER a big meal — the amylase enzymes help you digest faster!"},
            {"hook": "Mango can clear acne and improve skin texture in just 2 weeks.", "theme": "SKIN", "label": "SKIN & BEAUTY", "points": ["Vitamin A reduces sebum production — less acne", "Vitamin C builds collagen — smoother skin texture", "Beta-carotene gives natural healthy glow", "Vitamin E repairs damaged skin cells", "Alpha-hydroxy acids exfoliate dead skin naturally"], "tip": "Apply mashed mango to face for 15 min — it's a natural AHA chemical peel!"},
        ],
    },
    {
        "name": "Pineapple", "emoji": "🍍", "category": "TROPICAL", "accent_rgb": (234, 179, 8),
        "slide_searches": ["pineapple fruit whole", "pineapple sliced rings", "pineapple juice fresh", "pineapple tropical", "pineapple cut pieces"],
        "wikipedia": "Pineapple", "usda_fdc_id": 9274,
        "angles": [
            {"hook": "Pineapple contains an enzyme that DIGESTS protein — it literally eats you back.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["Bromelain breaks down protein into amino acids", "Reduces bloating after heavy protein meals", "Survives stomach acid — works in intestines too", "Eases symptoms of IBS and indigestion", "More effective than over-the-counter digestive enzymes"], "tip": "Eat pineapple between meals — bromelain works best on an empty stomach!"},
            {"hook": "Bromelain from pineapple reduces post-surgery swelling by 72%.", "theme": "RECOVERY", "label": "RECOVERY & HEALING", "points": ["Reduces swelling after surgery by 72%", "Speeds recovery from sports injuries", "Anti-inflammatory works like ibuprofen (without side effects)", "Thins mucus — great for sinus infections", "Accelerates wound healing by boosting collagen"], "tip": "Take bromelain supplements after dental surgery — reduces swelling better than medication!"},
            {"hook": "One cup of pineapple has MORE than your entire daily Vitamin C needs.", "theme": "IMMUNITY", "label": "IMMUNITY", "points": ["131% daily Vitamin C per cup", "Bromelain activates immune system T-cells", "Manganese (76% DV) creates antioxidant enzyme SOD", "Reduces duration of sinus infections by 60%", "Vitamin B6 produces antibodies against pathogens"], "tip": "Eat pineapple at the FIRST sign of a cold — bromelain kills sinus bacteria on contact!"},
            {"hook": "Pineapple is nature's answer to joint pain — and studies prove it.", "theme": "JOINTS", "label": "JOINT HEALTH", "points": ["Bromelain reduces arthritis pain by 29%", "Comparable to diclofenac (NSAID) but no stomach damage", "Blocks prostaglandins — the inflammation messengers", "Manganese builds cartilage and connective tissue", "Vitamin C produces collagen for joint repair"], "tip": "Have pineapple DAILY for 3 weeks — that's how long studies took to show joint improvement!"},
        ],
    },
    {
        "name": "Apple", "emoji": "🍎", "category": "TREE", "accent_rgb": (220, 38, 38),
        "slide_searches": ["red apple fruit whole", "apple fruit sliced half", "apple tree orchard", "apple juice fresh", "basket red apples"],
        "wikipedia": "Apple", "usda_fdc_id": 778079,
        "angles": [
            {"hook": "An apple a day lowers stroke risk by 52% — that's not a myth.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Quercetin lowers stroke risk by up to 52%", "Pectin reduces LDL cholesterol by 5-13%", "Polyphenols improve blood vessel elasticity", "Potassium helps maintain healthy blood pressure", "Fiber (4g) binds cholesterol in the gut"], "tip": "Eat the SKIN — 50% of the fiber and ALL the quercetin is in the peel!"},
            {"hook": "Apple polyphenols can block tumor growth in colon cancer cells.", "theme": "CANCER", "label": "CANCER-FIGHTING", "points": ["Quercetin triggers apoptosis in cancer cells", "Pectin produces butyrate — kills colon cancer cells", "Procyanidins block tumor growth signaling", "Reduces risk of lung cancer by 25% in non-smokers", "Amygdalin in apple seeds shows anti-tumor activity"], "tip": "Choose RED apples over green — they have 40% more polyphenols!"},
            {"hook": "Eating an apple before a meal cuts calorie intake by 15%.", "theme": "WEIGHT LOSS", "label": "WEIGHT LOSS", "points": ["Eating one before meals = 15% fewer calories consumed", "High pectin content triggers fullness hormones (GLP-1)", "Low GI (36) — stable blood sugar, no crashes", "Water + fiber = volume that physically fills stomach", "Ursolic acid in peel increases brown fat (calorie-burning)"], "tip": "Eat an apple 15 minutes before lunch — studies show you'll eat 187 fewer calories!"},
            {"hook": "Apples protect your brain from age-related decline — Oxford study.", "theme": "BRAIN", "label": "BRAIN HEALTH", "points": ["Quercetin protects neurons from oxidative damage", "Reduces beta-amyloid plaque (Alzheimer's marker)", "Ursolic acid preserves brain cell membranes", "Acetylcholine boost improves memory & learning", "Anti-inflammatory reduces neuroinflammation"], "tip": "Drink cloudy apple juice — it has 4x more brain-protecting polyphenols than clear!"},
        ],
    },
    {
        "name": "Avocado", "emoji": "🥑", "category": "SUPERFOOD", "accent_rgb": (34, 197, 94),
        "slide_searches": ["avocado fruit whole green", "avocado halves pit", "avocado toast healthy", "ripe avocado green", "avocado sliced"],
        "wikipedia": "Avocado", "usda_fdc_id": 778075,
        "angles": [
            {"hook": "Avocados have MORE potassium than bananas — and that's just the start.", "theme": "NUTRITION", "label": "NUTRITION POWERHOUSE", "points": ["14% DV potassium per half — beats bananas", "13g fiber per avocado — 52% daily value!", "Monounsaturated fat (oleic acid) = heart-healthy", "20 vitamins and minerals in one fruit", "More protein than any other fruit (4g per avocado)"], "tip": "Half an avocado = 160 calories of pure nutrition. Don't fear the fat!"},
            {"hook": "Avocado makes nutrients from OTHER foods 4x more absorbable.", "theme": "ABSORPTION", "label": "NUTRIENT BOOSTER", "points": ["Increases carotenoid absorption by 200-400%", "Fat-soluble vitamins (A, D, E, K) need fat to absorb", "Pair with tomatoes = 4.4x more lycopene absorbed", "Pair with carrots = 6.6x more beta-carotene absorbed", "Oleic acid enhances antioxidant bioavailability"], "tip": "Always add avocado to salads — without it, you absorb only a fraction of the nutrients!"},
            {"hook": "People who eat avocados daily have 34% less belly fat than those who don't.", "theme": "WEIGHT", "label": "WEIGHT MANAGEMENT", "points": ["Oleic acid activates PPAR-alpha fat-burning receptor", "High fiber + fat = extreme satiety (fullness)", "AVAT (avocado anti-fat toxin) targets abdominal fat", "Reduces desire to eat for 3-5 hours", "Lowers BMI, waist circumference, and body fat %"], "tip": "Eat half an avocado at lunch — you'll feel full for 5 hours and snack 40% less!"},
            {"hook": "Avocados can lower cholesterol as effectively as some statins.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Lowers LDL cholesterol by 22% in 1 week", "Raises HDL (good) cholesterol by 11%", "Beta-sitosterol blocks cholesterol absorption", "Potassium reduces blood pressure naturally", "Monounsaturated fats reduce arterial inflammation"], "tip": "1 avocado a day for 1 week — that's the dose used in cholesterol studies!"},
        ],
    },
    {
        "name": "Kiwi", "emoji": "🥝", "category": "SUPERFOOD", "accent_rgb": (34, 197, 94),
        "slide_searches": ["kiwi fruit whole", "kiwi fruit sliced green", "kiwi halves green", "kiwi smoothie", "golden kiwi fruit"],
        "wikipedia": "Kiwifruit", "usda_fdc_id": 9277,
        "angles": [
            {"hook": "Just 2 kiwis give you more Vitamin C than 2 oranges combined.", "theme": "IMMUNITY", "label": "IMMUNITY", "points": ["273% daily Vitamin C per cup — vitamin BOMB", "Stimulates neutrophil production (infection fighters)", "More Vitamin C per gram than ANY citrus fruit", "Antioxidants reduce duration of upper respiratory infections", "Vitamin E supports immune cell membranes"], "tip": "2 kiwis at breakfast = more Vitamin C than your entire day needs, twice over!"},
            {"hook": "Kiwis can cure constipation better than psyllium fiber — clinical trial.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["Actinidin enzyme breaks down protein faster", "Beats psyllium for constipation relief in studies", "Increases stool frequency by 1.5x naturally", "Softens stool without cramping or bloating", "Prebiotic fiber grows Lactobacillus gut bacteria"], "tip": "Eat 2 kiwis daily for constipation — it works better than fiber supplements!"},
            {"hook": "Kiwis help you fall asleep 35% faster — and sleep more deeply.", "theme": "SLEEP", "label": "SLEEP AID", "points": ["High serotonin levels regulate sleep-wake cycle", "Falling asleep 35% faster in sleep studies", "Total sleep time increases by 13%", "Sleep efficiency improves by 5.4%", "Works within 4 weeks of daily consumption"], "tip": "Eat 2 kiwis 1 hour before bed — that's the exact protocol from sleep studies!"},
            {"hook": "Golden kiwis have 3x more Vitamin C than green kiwis.", "theme": "NUTRITION", "label": "GOLDEN VS GREEN", "points": ["Golden kiwi: 161mg Vitamin C vs Green: 93mg", "Golden is sweeter and less acidic", "Green has more fiber (3g vs 2g per kiwi)", "Both are excellent — but golden wins for Vitamin C", "Golden kiwi was developed in New Zealand in 1992"], "tip": "Choose golden for Vitamin C, green for fiber — both are superfoods!"},
        ],
    },
    {
        "name": "Watermelon", "emoji": "🍉", "category": "MELON", "accent_rgb": (34, 197, 94),
        "slide_searches": ["watermelon fruit whole", "watermelon slices red", "watermelon juice glass", "watermelon cut red", "watermelon fresh pieces"],
        "wikipedia": "Watermelon", "usda_fdc_id": 9326,
        "angles": [
            {"hook": "Watermelon is nature's best post-workout drink — beats sports drinks.", "theme": "RECOVERY", "label": "EXERCISE RECOVERY", "points": ["L-citrulline reduces muscle soreness by 40%", "92% water + electrolytes = instant rehydration", "Natural sugars replenish glycogen faster", "Reduces heart rate recovery time after exercise", "Less inflammatory than commercial sports drinks"], "tip": "Drink watermelon juice within 30 min after exercise — that's when muscles need it most!"},
            {"hook": "Watermelon has more lycopene than raw tomatoes — 1.5x more!", "theme": "ANTIOXIDANTS", "label": "LYCOPENE CHAMPION", "points": ["1.5x more lycopene per cup than raw tomatoes", "Lycopene reduces prostate cancer risk by 35%", "Protects skin from UV damage — internal sunscreen", "Beta-cryptoxanthin reduces lung cancer risk", "Vitamin A + C = powerful antioxidant combo"], "tip": "Refrigerated watermelon has 40% MORE lycopene than room temperature!"},
            {"hook": "Watermelon can lower blood pressure as effectively as medication in some people.", "theme": "HEART", "label": "BLOOD PRESSURE", "points": ["L-citrulline converts to L-arginine — dilates blood vessels", "Reduces systolic BP by 9mmHg in prehypertensive adults", "Lycopene reduces arterial stiffness", "Potassium (320mg) counteracts sodium", "92% water flushes excess sodium from kidneys"], "tip": "Eat 2 cups of watermelon daily for 6 weeks — that's the BP study dose!"},
            {"hook": "Watermelon is technically both a fruit AND a vegetable.", "theme": "FUN FACTS", "label": "DID YOU KNOW?", "points": ["It's a vegetable — cousin of cucumbers & pumpkins", "Every part is edible: flesh, rind, seeds, juice", "Rind has MORE citrulline than the red flesh!", "Seeds are rich in protein, iron, and magnesium", "Yellow watermelon has more beta-carotene than red"], "tip": "Pick up the rind — it's edible! Pickled watermelon rind is delicious and nutritious!"},
        ],
    },
    {
        "name": "Grapes", "emoji": "🍇", "category": "BERRY", "accent_rgb": (139, 92, 246),
        "slide_searches": ["purple grapes bunch", "grapes vineyard branch", "bowl fresh grapes", "red grapes close", "grapes market pile"],
        "wikipedia": "Grape", "usda_fdc_id": 9189,
        "angles": [
            {"hook": "Resveratrol in grapes activates the same longevity gene as fasting.", "theme": "ANTI-AGING", "label": "LONGEVITY", "points": ["Resveratrol activates SIRT1 — the longevity gene", "Mimics caloric restriction without actually fasting", "Extends lifespan 30% in animal studies", "Protects telomeres — the aging clock in your DNA", "Reduces cellular senescence (zombie cells)"], "tip": "Red & purple grapes have 3x more resveratrol than green — always choose dark!"},
            {"hook": "Grapes protect your brain from Alzheimer's — University of Switzerland study.", "theme": "BRAIN", "label": "BRAIN PROTECTION", "points": ["Resveratrol clears amyloid-beta plaques", "Polyphenols improve cerebral blood flow", "Protects hippocampus — the memory center", "Reduces neuroinflammation by 35%", "Improves memory recall in age-related decline"], "tip": "Concord grape juice = brain benefits without alcohol. 2 cups daily for 12 weeks!"},
            {"hook": "Grape seed extract is 20x more powerful than Vitamin C and 50x more than Vitamin E.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT POWER", "points": ["OPC (oligomeric proanthocyanidins) are the magic compounds", "20x more powerful antioxidant than Vitamin C", "50x more powerful antioxidant than Vitamin E", "Crosses blood-brain barrier — protects brain directly", "Strengthens collagen in blood vessels & skin"], "tip": "Don't spit out the seeds — they contain the MOST antioxidants in the grape!"},
            {"hook": "Grapes can reduce blood sugar spikes by 30% when eaten with meals.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Resveratrol improves insulin sensitivity", "Reduces fasting blood glucose by 15%", "Protects pancreatic beta cells from damage", "Fiber slows glucose absorption from food", "Low GI (53) — moderate impact on blood sugar"], "tip": "Freeze grapes and eat them frozen — slower sugar release + refreshing treat!"},
        ],
    },
    {
        "name": "Pomegranate", "emoji": "🔴", "category": "SUPERFOOD", "accent_rgb": (190, 18, 60),
        "slide_searches": ["pomegranate fruit whole red", "pomegranate seeds arils", "pomegranate open half", "pomegranate juice red", "pomegranate close up"],
        "wikipedia": "Pomegranate", "usda_fdc_id": 9287,
        "angles": [
            {"hook": "Pomegranate juice has 3x more antioxidants than green tea or red wine.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT KING", "points": ["Punicalagins — among the most powerful antioxidants known", "3x more antioxidant capacity than green tea", "2x more than red wine", "Protects LDL cholesterol from oxidation", "ORAC score: 2860 per 100g — exceptional"], "tip": "Drink 8oz pomegranate juice daily — that's the dose used in heart studies!"},
            {"hook": "Pomegranate may slow prostate cancer growth by 50% — UCLA study.", "theme": "CANCER", "label": "CANCER-FIGHTING", "points": ["Doubles PSA doubling time (slows cancer growth)", "Apoptosis induction — triggers cancer cell death", "Inhibits angiogenesis (tumor blood supply)", "Reduces breast cancer cell proliferation by 80%", "Ellagic acid blocks estrogen-driven cancer pathways"], "tip": "8oz pomegranate juice daily for prostate health — used in the UCLA clinical trial!"},
            {"hook": "Pomegranate reduces blood pressure by 12% in just 2 weeks.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Reduces systolic BP by 5-12% in 2 weeks", "ACE inhibitor effect — naturally blocks angiotensin", "Reduces arterial plaque thickness by 30%", "Improves endothelial function (blood vessel health)", "Prevents oxidation of LDL cholesterol"], "tip": "Drink pomegranate juice BEFORE meals — the nitrates work best on an empty stomach!"},
            {"hook": "Pomegranate improves memory in older adults after just 4 weeks.", "theme": "BRAIN", "label": "MEMORY BOOSTER", "points": ["Improves visual memory by 30% in older adults", "Urolithin A clears damaged mitochondria from brain cells", "Reduces beta-amyloid plaque formation", "Enhances verbal and visual memory recall", "Anti-inflammatory protects brain tissue"], "tip": "8oz juice daily for 4 weeks — that's the protocol used in memory improvement studies!"},
        ],
    },
    {
        "name": "Cherry", "emoji": "🍒", "category": "BERRY", "accent_rgb": (185, 28, 28),
        "slide_searches": ["cherry fruit whole red", "bowl fresh cherries", "cherry tree branch fruit", "cherry close up", "cherry smoothie"],
        "wikipedia": "Cherry", "usda_fdc_id": 9270,
        "angles": [
            {"hook": "Tart cherry juice reduces insomnia severity by 45% — no pills needed.", "theme": "SLEEP", "label": "SLEEP AID", "points": ["Natural melatonin — regulates sleep-wake cycle", "Increases sleep time by 84 minutes", "Reduces insomnia severity by 45%", "Tryptophan + melatonin + serotonin = sleep trifecta", "Works better than valerian root in studies"], "tip": "Drink tart cherry juice 30 min before bed — it's nature's sleeping pill!"},
            {"hook": "Cherries reduce gout attacks by 35% — the #1 natural gout remedy.", "theme": "GOUT", "label": "GOUT RELIEF", "points": ["Reduces uric acid levels by 15% in 4 hours", "Anthocyanins block COX-1 and COX-2 enzymes", "Anti-inflammatory = 10x more potent than aspirin", "Cuts gout attack risk by 35% when eaten daily", "Vitamin C increases uric acid excretion by kidneys"], "tip": "Eat 15-20 cherries at the FIRST sign of a gout flare!"},
            {"hook": "Cherries have the highest anti-inflammatory content of any food.", "theme": "INFLAMMATION", "label": "ANTI-INFLAMMATORY", "points": ["Anthocyanins block NF-kB inflammation pathway", "COX inhibition comparable to ibuprofen (no stomach damage)", "Reduces CRP (inflammation marker) by 25%", "Works for arthritis, muscle pain, and joint stiffness", "Tart cherries have 5x more anti-inflammatory power than sweet"], "tip": "Choose TART cherries for inflammation — they have 5x more anthocyanins than sweet!"},
            {"hook": "Cherries speed up muscle recovery faster than ice baths.", "theme": "RECOVERY", "label": "MUSCLE RECOVERY", "points": ["Reduces post-race muscle pain by 24%", "Accelerates strength recovery after exercise", "Lowers creatine kinase (muscle damage marker) by 19%", "Anti-inflammatory reduces DOMS (delayed soreness)", "Antioxidants repair micro-tears in muscle fibers"], "tip": "Drink tart cherry juice for 7 days BEFORE a big race — proven to cut recovery time!"},
        ],
    },
    {
        "name": "Papaya", "emoji": "🍈", "category": "TROPICAL", "accent_rgb": (251, 146, 60),
        "slide_searches": ["papaya fruit whole", "papaya sliced half seeds", "papaya pieces fresh", "papaya tree tropical", "papaya smoothie"],
        "wikipedia": "Papaya", "usda_fdc_id": 9252,
        "angles": [
            {"hook": "Papaya has an enzyme 200x more powerful than pepsin for digestion.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["Papain digests protein 200x stronger than your own pepsin", "Used medically to treat pancreatic insufficiency", "Tenderizes meat — imagine what it does for your stomach", "Fiber + enzymes = perfect digestion combo", "Relieves chronic indigestion in 7 days"], "tip": "Eat papaya seeds too — they kill intestinal parasites effectively!"},
            {"hook": "Papaya can reverse sun damage and reduce wrinkles by 20%.", "theme": "SKIN", "label": "SKIN & BEAUTY", "points": ["Papain removes dead skin cells naturally", "Lycopene (more than tomatoes!) fights UV damage", "Vitamin C (144% DV) builds collagen fast", "Vitamin A reduces hyperpigmentation and dark spots", "Enzymes unclog pores — prevents acne breakouts"], "tip": "Rub papaya skin (inside) on your face — leave 10 min for natural enzyme peel!"},
            {"hook": "Papaya is one of the best fruits for heart disease prevention.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Lycopene prevents cholesterol oxidation in arteries", "Potassium (257mg) regulates blood pressure", "Fiber binds cholesterol in the digestive tract", "Vitamin C prevents arterial wall damage", "Folate reduces homocysteine — major heart risk factor"], "tip": "Red papaya has more lycopene than pink grapefruit — choose the reddest ones!"},
            {"hook": "Papaya seeds are a natural dewormer used in traditional medicine for centuries.", "theme": "PARASITES", "label": "ANTIPARASITIC", "points": ["Seeds contain caricin — kills intestinal worms", "Studies show 75% parasite clearance in children", "Antibacterial against E. coli, Salmonella, Staph", "Protects kidneys from toxin damage", "Rich in oleic and palmitic acids (anti-inflammatory)"], "tip": "Blend 1 tablespoon papaya seeds into your smoothie — taste like black pepper!"},
        ],
    },
    {
        "name": "Dragon Fruit", "emoji": "🐉", "category": "TROPICAL", "accent_rgb": (219, 39, 119),
        "slide_searches": ["dragon fruit whole pink", "dragon fruit sliced half", "dragon fruit pieces bowl", "dragon fruit smoothie pink", "red dragon fruit cut"],
        "wikipedia": "Pitaya", "usda_fdc_id": 778077,
        "angles": [
            {"hook": "Dragon fruit feeds your gut bacteria better than most probiotics.", "theme": "GUT HEALTH", "label": "GUT HEALTH", "points": ["Prebiotic oligosaccharides feed Lactobacillus & Bifidobacteria", "Boosts beneficial bacteria by up to 34%", "7g fiber per cup — excellent for digestion", "Seeds contain healthy omega-3 & omega-9 fatty acids", "Reduces gut inflammation markers significantly"], "tip": "The tiny black seeds are where the omega-3s live — chew them, don't swallow whole!"},
            {"hook": "Red dragon fruit can stabilize blood sugar for up to 6 hours.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Red variety reduces blood glucose by 30%", "Betalains improve insulin receptor sensitivity", "Fiber creates slow, steady glucose release", "Low GI — won't cause sugar spikes", "Prebiotic fiber reduces metabolic syndrome markers"], "tip": "Choose RED dragon fruit over white — it has 10x more betacyanins for blood sugar!"},
            {"hook": "Dragon fruit's betacyanins are being studied as cancer-fighting compounds.", "theme": "CANCER", "label": "CANCER RESEARCH", "points": ["Betacyanins induce cancer cell apoptosis", "Red dragon fruit has 10x more betacyanins than white", "Phytoalbumins prevent cell mutation", "Vitamin C boosts NK (natural killer) cell activity", "Antioxidant protection reduces DNA damage by 35%"], "tip": "Red dragon fruit = the most powerful variety. The deeper the color, the more betacyanins!"},
            {"hook": "Dragon fruit is one of the few natural sources of iron for vegetarians.", "theme": "ANEMIA", "label": "IRON & BLOOD", "points": ["0.65mg iron per cup — rare for fruit", "Vitamin C (34% DV) increases iron absorption by 6x", "Iron + Vitamin C in the same food = perfect combo", "Promotes red blood cell production", "Prevents iron-deficiency anemia in plant-based diets"], "tip": "Dragon fruit + citrus = maximum iron absorption. The vitamin C does the heavy lifting!"},
        ],
    },
    {
        "name": "Guava", "emoji": "🍈", "category": "TROPICAL", "accent_rgb": (34, 197, 94),
        "slide_searches": ["guava fruit whole green", "guava fruit sliced pink", "guava pieces fresh", "guava tree fruit", "guava juice pink"],
        "wikipedia": "Guava", "usda_fdc_id": 9186,
        "angles": [
            {"hook": "One guava has 4x more Vitamin C than an orange — the ultimate immune fruit.", "theme": "IMMUNITY", "label": "IMMUNITY", "points": ["4x more Vitamin C than oranges (228mg vs 53mg)", "380% daily Vitamin C per guava — INSANE", "Fights infections by boosting white blood cell count", "Vitamin A protects mucous membranes — first defense", "Antimicrobial properties kill H. pylori bacteria"], "tip": "1 guava = 4 oranges worth of Vitamin C. And it tastes way better!"},
            {"hook": "Guava leaves are scientifically proven to lower blood sugar by 20%.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Guava leaf tea lowers blood sugar by 20%", "Inhibits alpha-glucosidase (carb-digesting enzyme)", "Improves insulin sensitivity in type 2 diabetes", "Fiber (9g per cup) slows glucose absorption", "Low GI (12!) — one of the lowest of all fruits"], "tip": "Brew guava LEAF tea after meals — it cuts blood sugar spikes better than the fruit!"},
            {"hook": "Guava has more potassium than a banana AND more fiber than an apple.", "theme": "NUTRITION", "label": "NUTRITION DENSITY", "points": ["417mg potassium per cup — beats bananas", "9g fiber per cup — beats apples", "228mg Vitamin C — beats oranges 4x", "Folate, B6, Vitamin A, Vitamin K — all in one", "Only 112 calories per cup — nutrient density champion"], "tip": "Guava is pound-for-pound the most nutrient-dense fruit on Earth!"},
            {"hook": "Guava can improve thyroid function — it's rich in selenium and copper.", "theme": "THYROID", "label": "THYROID HEALTH", "points": ["Copper helps convert T4 to active T3 thyroid hormone", "Selenium protects thyroid gland from oxidative damage", "Vitamin C reduces thyroid inflammation", "Iodine content supports thyroid hormone production", "Anti-inflammatory reduces Hashimoto's symptoms"], "tip": "Eat guava regularly if you have thyroid issues — copper + selenium is the key combo!"},
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────


VEGETABLES = [
    {
        "name": "Broccoli", "emoji": "🥦", "category": "CRUCIFEROUS", "accent_rgb": (34, 197, 94),
        "slide_searches": ["broccoli fresh green", "broccoli florets close", "broccoli vegetable raw", "broccoli bunch market", "broccoli steamed"],
        "wikipedia": "Broccoli", "usda_fdc_id": 170379,
        "angles": [
            {"hook": "Broccoli has a compound that kills cancer stem cells — Johns Hopkins study.", "theme": "CANCER", "label": "CANCER-FIGHTING", "points": ["Sulforaphane eliminates cancer stem cells at the root", "Reduces breast cancer risk by 28% in regular eaters", "Activates NRF2 — the body's master antioxidant switch", "Indole-3-carbinol blocks estrogen-driven cancers", "42mg Vitamin C per cup boosts NK cell cancer defense"], "tip": "Steam broccoli for 3-4 min only — overcooking destroys 60% of sulforaphane!"},
            {"hook": "Eating broccoli twice a week can reverse early arterial damage.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Sulforaphane repairs damaged artery lining", "Fiber (2.4g) lowers LDL cholesterol significantly", "Potassium (288mg) regulates blood pressure", "Folate reduces homocysteine — key heart risk marker", "Kaempferol reduces arterial inflammation by 20%"], "tip": "Pair broccoli with mustard — myrosinase in mustard activates more sulforaphane!"},
            {"hook": "Broccoli is more effective than any supplement for detoxification.", "theme": "DETOX", "label": "DETOX POWER", "points": ["Activates Phase II detox enzymes in the liver", "Glucoraphanin binds and removes airborne pollutants", "Doubles the rate of benzene excretion from the body", "Sulforaphane crosses the blood-brain barrier to detox neurons", "Glutathione precursors regenerate the body's master antioxidant"], "tip": "Eat broccoli sprouts for 10x more detox power than mature broccoli!"},
            {"hook": "Broccoli can protect your eyesight from age-related decline.", "theme": "EYES", "label": "EYE HEALTH", "points": ["Lutein & zeaxanthin filter harmful blue light", "Reduces macular degeneration risk by 26%", "Vitamin A maintains cornea health and night vision", "Beta-carotene converts to retinol — essential for vision", "Vitamin C reduces cataract progression by 33%"], "tip": "Eat broccoli with olive oil — fat doubles lutein and zeaxanthin absorption!"},
        ],
    },
    {
        "name": "Spinach", "emoji": "🥬", "category": "LEAFY", "accent_rgb": (21, 128, 61),
        "slide_searches": ["spinach leaves fresh", "spinach bunch green", "baby spinach bowl", "spinach salad fresh", "spinach raw green"],
        "wikipedia": "Spinach", "usda_fdc_id": 168462,
        "angles": [
            {"hook": "One cup of spinach has more iron than a 3oz steak — Popeye was right.", "theme": "IRON", "label": "IRON & ENERGY", "points": ["3.5mg iron per cup — exceptional for a vegetable", "Vitamin C in spinach increases iron absorption 3x", "Folate produces red blood cells that carry oxygen", "B vitamins convert food into sustained energy", "Magnesium activates 300+ energy-producing enzymes"], "tip": "Add lemon juice to spinach — the Vitamin C triples your iron absorption!"},
            {"hook": "Spinach protects your brain from shrinking as you age.", "theme": "BRAIN", "label": "BRAIN PROTECTION", "points": ["Lutein slows cognitive decline by up to 11 years", "Folate reduces brain atrophy and depression risk", "Vitamin K builds sphingolipids — brain cell membrane fat", "Alpha-lipoic acid prevents Alzheimer's plaque formation", "Nitrates improve cerebral blood flow within 90 minutes"], "tip": "1 cup spinach daily — that's the exact dose that slowed brain aging in studies!"},
            {"hook": "Spinach is the most powerful vegetable for lowering blood pressure.", "theme": "HEART", "label": "BLOOD PRESSURE", "points": ["Dietary nitrates dilate blood vessels in 90 minutes", "Lowers systolic BP by 8-10mmHg in studies", "Potassium (558mg) flushes sodium from the body", "Magnesium relaxes arterial smooth muscle", "Peptides in spinach inhibit ACE (like BP medications)"], "tip": "Raw spinach has 30% more nitrates than cooked — mix raw into salads!"},
            {"hook": "Spinach can rebuild bone density better than calcium supplements.", "theme": "BONES", "label": "BONE HEALTH", "points": ["Vitamin K activates osteocalcin — the bone-building protein", "1 cup provides 145% daily Vitamin K", "Calcium (30mg) + magnesium = better absorption than dairy", "Folate reduces bone-weakening homocysteine", "Phytoecdysteroids stimulate bone-forming osteoblast cells"], "tip": "Cook spinach with dairy — the fat improves Vitamin K absorption by 400%!"},
        ],
    },
    {
        "name": "Garlic", "emoji": "🧄", "category": "ALLIUM", "accent_rgb": (217, 119, 6),
        "slide_searches": ["garlic bulb fresh", "garlic cloves peeled", "garlic bunch market", "fresh garlic close up", "garlic head white"],
        "wikipedia": "Garlic", "usda_fdc_id": 169230,
        "angles": [
            {"hook": "Garlic is more effective than some antibiotics against drug-resistant bacteria.", "theme": "IMMUNITY", "label": "NATURAL ANTIBIOTIC", "points": ["Allicin kills MRSA (methicillin-resistant Staph aureus)", "Effective against 23 types of bacteria including E. coli", "Ajoene compound destroys fungal infections", "Reduces cold frequency by 63% with daily consumption", "Diallyl sulfide penetrates bacterial biofilms antibiotics can't reach"], "tip": "Crush garlic and wait 10 minutes before cooking — this maximizes allicin formation!"},
            {"hook": "Garlic can lower blood pressure as effectively as medication.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Allicin reduces systolic BP by 8-10mmHg", "Lowers LDL cholesterol by 10-15%", "Reduces platelet aggregation — prevents dangerous clots", "Hydrogen sulfide from garlic relaxes blood vessel walls", "Reduces arterial stiffness by 15% in 3 months"], "tip": "Eat 1-2 raw cloves daily — that's the dose used in blood pressure studies!"},
            {"hook": "Aged garlic extract cuts the size of arterial plaque by 80%.", "theme": "ARTERIES", "label": "ARTERY CLEANER", "points": ["Reduces coronary artery calcification progression by 80%", "S-allylcysteine reverses existing arterial plaque", "Prevents new plaque formation in high-risk patients", "Improves blood flow velocity by 20% within weeks", "Anti-inflammatory reduces CRP (inflammation marker) by 23%"], "tip": "Aged garlic supplements = max artery benefit. 1.2g daily is the clinical dose!"},
            {"hook": "Garlic reduces the risk of stomach and colorectal cancer by up to 50%.", "theme": "CANCER", "label": "CANCER PREVENTION", "points": ["Allicin induces apoptosis in cancer cells", "Diallyl disulfide blocks cell division in cancer lines", "Reduces stomach cancer risk by 52% in regular eaters", "H. pylori (stomach cancer cause) killed by allicin", "Organosulfur compounds detox carcinogens from the colon"], "tip": "Eat garlic 3x per week minimum — that's what defines 'regular eater' in cancer studies!"},
        ],
    },
    {
        "name": "Sweet Potato", "emoji": "🍠", "category": "ROOT", "accent_rgb": (234, 88, 12),
        "slide_searches": ["sweet potato whole", "sweet potato baked", "sweet potato sliced raw", "sweet potato orange flesh", "sweet potato harvest"],
        "wikipedia": "Sweet_potato", "usda_fdc_id": 168482,
        "angles": [
            {"hook": "One sweet potato has more Vitamin A than you need for an entire week.", "theme": "VISION", "label": "EYE HEALTH", "points": ["438% daily Vitamin A per medium sweet potato", "Beta-carotene reduces macular degeneration risk by 35%", "Zeaxanthin protects retina from UV light damage", "Vitamin A maintains corneal moisture and clarity", "Night blindness prevention — Vitamin A is essential"], "tip": "Eat sweet potato with fat — beta-carotene is fat-soluble, needs fat to absorb!"},
            {"hook": "Sweet potatoes stabilize blood sugar better than white potatoes by 50%.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Glycemic Index of 54 vs white potato's 82", "Caiapo extract improves insulin sensitivity 30%", "Fiber slows glucose release into bloodstream", "Adiponectin (hormone that improves insulin function) boosted", "Chromium enhances insulin's effectiveness at cells"], "tip": "Let cooked sweet potato COOL before eating — cooling increases resistant starch!"},
            {"hook": "Sweet potato is the #1 food recommended by NASA for long-term space missions.", "theme": "NUTRITION", "label": "NUTRITION POWERHOUSE", "points": ["Complete: Vitamin A, C, B6, potassium, fiber, iron", "Antioxidant ORAC score of 2115 — exceptional for a root veg", "Anthocyanins in purple variety surpass blueberries", "Only 103 calories — incredible nutrient-to-calorie ratio", "More potassium than a banana (448mg)"], "tip": "Purple sweet potatoes have 150% more antioxidants than orange ones!"},
            {"hook": "Sweet potatoes reduce inflammation as effectively as ibuprofen.", "theme": "INFLAMMATION", "label": "ANTI-INFLAMMATORY", "points": ["Beta-carotene reduces inflammatory cytokines by 30%", "Anthocyanins inhibit COX-2 enzyme (same as ibuprofen)", "Sporamins — unique proteins with powerful antioxidant activity", "Reduces CRP inflammation marker by 12%", "Vitamin C neutralizes free radicals before they trigger inflammation"], "tip": "Purple sweet potatoes have the highest anti-inflammatory power — seek them out!"},
        ],
    },
    {
        "name": "Carrot", "emoji": "🥕", "category": "ROOT", "accent_rgb": (249, 115, 22),
        "slide_searches": ["carrot fresh orange", "carrot bunch market", "carrot sliced raw", "carrot juice fresh", "baby carrots bowl"],
        "wikipedia": "Carrot", "usda_fdc_id": 170393,
        "angles": [
            {"hook": "Carrots have a compound that kills leukemia cells within 72 hours — Danish study.", "theme": "CANCER", "label": "CANCER RESEARCH", "points": ["Falcarinol kills leukemia cells and reduces tumor size 33%", "Beta-carotene reduces lung cancer risk by 40% in non-smokers", "Alpha-carotene linked to 39% lower cancer mortality risk", "Polyacetylenes prevent colon cancer cell proliferation", "Antioxidants prevent DNA damage that triggers mutation"], "tip": "Eat carrots whole, not baby carrots — they retain 25% more falcarinol!"},
            {"hook": "Cooking carrots INCREASES their nutritional value by 25%.", "theme": "NUTRITION", "label": "NUTRITION FACTS", "points": ["Cooking breaks cell walls — releases more beta-carotene", "Bioavailability of beta-carotene increases 25-40%", "Boiling > steaming > raw for beta-carotene absorption", "Lutein and zeaxanthin also more available after cooking", "Fiber becomes more fermentable, feeding gut bacteria better"], "tip": "Cook with olive oil — fat boosts beta-carotene absorption by up to 600%!"},
            {"hook": "Carrots protect your skin from sun damage from the inside out.", "theme": "SKIN", "label": "SKIN PROTECTION", "points": ["Beta-carotene acts as internal SPF protection", "High intake reduces sunburn severity by 40%", "Gives skin a healthy golden glow (carotenemia)", "Vitamin A speeds skin cell regeneration", "Antioxidants prevent UV-induced wrinkle formation"], "tip": "2 carrots daily for 6 weeks produces a visible skin glow — it's called carotenemia!"},
            {"hook": "Carrot juice lowers cholesterol faster than most medications.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Reduces total cholesterol by 11% in 3 months", "Raises HDL (good) cholesterol by 5-6%", "Potassium (410mg) lowers blood pressure", "Fiber binds bile acids — forces liver to use cholesterol", "Alpha-carotene reduces heart disease risk by 50%"], "tip": "Drink 16oz fresh carrot juice daily — that was the dose in the cholesterol study!"},
        ],
    },
    {
        "name": "Beet", "emoji": "🫚", "category": "ROOT", "accent_rgb": (190, 18, 60),
        "slide_searches": ["beet root fresh red", "beets whole raw", "beetroot sliced", "beet juice red glass", "fresh beets bunch"],
        "wikipedia": "Beetroot", "usda_fdc_id": 169145,
        "angles": [
            {"hook": "Beet juice improves athletic performance by 3% — equivalent to years of training.", "theme": "PERFORMANCE", "label": "ATHLETIC BOOST", "points": ["Nitrates improve oxygen efficiency in muscles by 19%", "Reduces time to exhaustion by 15% in cyclists", "Lowers oxygen cost of exercise at submaximal intensity", "Improves sprint performance in the final stage of races", "Nitric oxide from beets dilates blood vessels to muscles"], "tip": "Drink beet juice 2-3 hours BEFORE exercise — nitrates peak at 2-3 hours after ingestion!"},
            {"hook": "Beets lower blood pressure faster than any other food — within 3 hours.", "theme": "HEART", "label": "BLOOD PRESSURE", "points": ["Lowers systolic BP by 4-10mmHg within 3 hours", "Dietary nitrates convert to nitric oxide — vasodilator", "Effect lasts up to 24 hours from a single serving", "Betaine reduces homocysteine — a major heart risk factor", "Potassium (325mg) counteracts sodium's BP-raising effect"], "tip": "1 cup beet juice = the same BP drop as prescription medication in some studies!"},
            {"hook": "Beets are one of the only foods that regenerate liver cells.", "theme": "LIVER", "label": "LIVER HEALTH", "points": ["Betaine prevents fat accumulation in the liver", "Pectin fiber flushes toxins processed by the liver", "Glutathione precursors regenerate liver cell antioxidants", "Reduces liver enzyme markers (AST/ALT) in fatty liver disease", "Betalains reduce liver inflammation by 30%"], "tip": "Drink beet juice in the morning on an empty stomach for maximum liver detox!"},
            {"hook": "Beet juice improves brain blood flow in older adults within 90 minutes.", "theme": "BRAIN", "label": "BRAIN POWER", "points": ["Increases blood flow to frontal lobe by 20%", "Improves white matter connectivity in aging brains", "Nitrates cross the blood-brain barrier directly", "Reduces risk of dementia by improving vascular health", "Improves reaction time and working memory in elderly"], "tip": "Combine beets with leafy greens for synergistic nitrate effect on brain blood flow!"},
        ],
    },
    {
        "name": "Kale", "emoji": "🥬", "category": "LEAFY", "accent_rgb": (22, 163, 74),
        "slide_searches": ["kale fresh green leaves", "kale bunch raw", "kale salad bowl", "curly kale vegetable", "kale leaves dark green"],
        "wikipedia": "Kale", "usda_fdc_id": 323505,
        "angles": [
            {"hook": "Kale has more Vitamin C than an orange and more calcium than milk.", "theme": "NUTRITION", "label": "NUTRITION POWERHOUSE", "points": ["206% daily Vitamin C per cup — beats oranges", "180mg calcium per cup — beats milk per calorie", "Vitamin K (1021% DV) — highest of any vegetable", "33 calories per cup — lowest calorie density of any superfood", "More iron per calorie than beef"], "tip": "Massage raw kale with olive oil for 2 minutes — it breaks down fibrous texture and improves nutrient absorption!"},
            {"hook": "Kale reduces LDL cholesterol by 27% in just 12 weeks.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Bile acid sequestrants bind cholesterol for excretion", "Reduces LDL (bad cholesterol) by 27% in 12 weeks", "Raises HDL (good cholesterol) by 27% simultaneously", "Quercetin reduces arterial inflammation and plaque", "Potassium (299mg) lowers blood pressure naturally"], "tip": "Drink steamed kale juice daily for 12 weeks — that's the exact protocol from the cholesterol study!"},
            {"hook": "Kale has more antioxidants than almost any other vegetable on Earth.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT POWER", "points": ["ORAC score of 1770 — top 5 vegetables globally", "Quercetin crosses the blood-brain barrier to protect neurons", "Kaempferol reduces risk of chronic disease by 40%", "Beta-carotene + lutein + zeaxanthin = triple vision protection", "Glucosinolates activate the body's own antioxidant enzymes"], "tip": "Purple kale has 4x more antioxidants than green kale — worth seeking out!"},
            {"hook": "Kale is a complete protein source — with all 9 essential amino acids.", "theme": "PROTEIN", "label": "PLANT PROTEIN", "points": ["Contains all 9 essential amino acids", "3g protein per cup — exceptional for a leafy green", "Leucine content stimulates muscle protein synthesis", "More bioavailable protein than most legumes", "Perfect for plant-based athletes and vegans"], "tip": "Blend kale into smoothies to mask the bitterness while keeping all the protein!"},
        ],
    },
    {
        "name": "Turmeric", "emoji": "🫚", "category": "SPICE", "accent_rgb": (234, 179, 8),
        "slide_searches": ["turmeric root fresh", "turmeric powder yellow", "fresh turmeric rhizome", "turmeric root cut", "turmeric spice golden"],
        "wikipedia": "Turmeric", "usda_fdc_id": 172231,
        "angles": [
            {"hook": "Curcumin in turmeric is more effective than ibuprofen for arthritis pain.", "theme": "INFLAMMATION", "label": "ANTI-INFLAMMATORY", "points": ["Curcumin blocks NF-kB — the master inflammation switch", "Equally effective as ibuprofen for knee osteoarthritis", "Reduces CRP (inflammation marker) by 32%", "Inhibits COX-2 enzyme without stomach damage side effects", "500mg curcumin = 50mg diclofenac for arthritis pain"], "tip": "Always take turmeric with black pepper — piperine increases curcumin absorption by 2000%!"},
            {"hook": "Turmeric is the most studied natural compound for depression treatment.", "theme": "MENTAL HEALTH", "label": "MOOD & BRAIN", "points": ["As effective as Prozac for major depression in clinical trials", "Increases serotonin and dopamine levels simultaneously", "Reduces cortisol (stress hormone) by 20%", "Neurogenesis — stimulates growth of new brain cells", "Crosses blood-brain barrier to directly protect neurons"], "tip": "Take 1g curcumin with black pepper for 6 weeks — the timeline used in depression studies!"},
            {"hook": "Turmeric can prevent Alzheimer's disease — India has 4x lower rates than US.", "theme": "BRAIN", "label": "ALZHEIMER'S PREVENTION", "points": ["Curcumin dissolves amyloid plaques in the brain", "India's high turmeric consumption linked to lowest dementia rates globally", "Prevents tau protein tangles — the second Alzheimer's marker", "Anti-inflammatory protects synaptic connections", "Increases BDNF (brain growth hormone) like antidepressants"], "tip": "Golden milk (turmeric + warm milk + black pepper) nightly is the easiest habit for brain health!"},
            {"hook": "Turmeric reverses metabolic syndrome markers in just 30 days.", "theme": "METABOLISM", "label": "METABOLISM", "points": ["Reduces fasting blood sugar by 18% in pre-diabetics", "Prevents progression from pre-diabetes to type 2 diabetes", "Improves insulin sensitivity by activating PPAR-gamma", "Reduces belly fat accumulation by blocking fat cell formation", "Lowers triglycerides by 25% in metabolic syndrome patients"], "tip": "Turmeric + ginger + black pepper tea before meals = most powerful metabolic combination!"},
        ],
    },
    {
        "name": "Ginger", "emoji": "🫚", "category": "SPICE", "accent_rgb": (161, 98, 7),
        "slide_searches": ["ginger root fresh", "ginger sliced raw", "ginger root whole", "fresh ginger close up", "ginger tea warm"],
        "wikipedia": "Ginger", "usda_fdc_id": 169231,
        "angles": [
            {"hook": "Ginger eliminates nausea faster than Dramamine — with zero side effects.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["1g ginger eliminates pregnancy nausea in 90% of cases", "More effective than Dramamine for motion sickness", "Gingerols accelerate gastric emptying by 25%", "Relieves post-surgery nausea — used in hospitals", "Reduces bloating and intestinal cramping within 30 min"], "tip": "Chew a small piece of raw ginger for instant nausea relief — more effective than ginger ale!"},
            {"hook": "Ginger reduces muscle soreness by 25% after exercise — better than ice.", "theme": "RECOVERY", "label": "EXERCISE RECOVERY", "points": ["Reduces delayed-onset muscle soreness (DOMS) by 25%", "2g daily for 11 days reduces post-exercise pain significantly", "Anti-inflammatory effect comparable to ibuprofen", "Improves recovery speed for resistance training", "Reduces exercise-induced oxidative stress markers"], "tip": "Take 2g ginger powder daily for 5 days before intense training — it pre-loads the anti-inflammatory effect!"},
            {"hook": "Ginger lowers fasting blood sugar by 12% — the same as some medications.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Reduces fasting blood sugar by 12% in type 2 diabetics", "Lowers HbA1c (3-month blood sugar) by 10%", "Improves insulin sensitivity by activating GLUT4 transporters", "Reduces insulin resistance in skeletal muscle", "Anti-inflammatory protects pancreatic beta cells"], "tip": "2g ginger powder daily with meals — that's the clinically proven dose for blood sugar!"},
            {"hook": "6 gingerols in ginger directly inhibit cancer cell migration.", "theme": "CANCER", "label": "CANCER RESEARCH", "points": ["6-gingerol inhibits cancer cell invasion and metastasis", "Induces apoptosis in ovarian cancer cells", "Reduces prostate cancer cell growth by 56%", "Paradols in ginger prevent skin cancer from UV exposure", "Anti-angiogenic — cuts off blood supply to tumors"], "tip": "Fresh ginger has 6x more active gingerols than dried powder — use fresh whenever possible!"},
        ],
    },
    {
        "name": "Bell Pepper", "emoji": "🫑", "category": "NIGHTSHADE", "accent_rgb": (220, 38, 38),
        "slide_searches": ["bell pepper red whole", "bell peppers colorful mix", "red pepper sliced", "bell pepper fresh market", "yellow red bell peppers"],
        "wikipedia": "Bell_pepper", "usda_fdc_id": 170108,
        "angles": [
            {"hook": "Red bell peppers have 3x more Vitamin C than oranges — the most overlooked fact in nutrition.", "theme": "IMMUNITY", "label": "VITAMIN C CHAMPION", "points": ["190mg Vitamin C per red pepper — 211% daily value", "3x more Vitamin C than an orange (by weight)", "Green peppers have least; red have most (fully ripened)", "Vitamin C boosts collagen production for skin and joints", "Heat-stable Vitamin C — still potent after roasting"], "tip": "Choose RED over green bell peppers — same plant, 3x the Vitamin C and 9x more beta-carotene!"},
            {"hook": "Bell peppers contain a compound that boosts metabolism for 4 hours after eating.", "theme": "WEIGHT LOSS", "label": "FAT BURNING", "points": ["Capsanthin activates thermogenesis — fat burning", "Dihydrocapsiate boosts metabolic rate by 50 calories/day", "Low calorie (31 cal) with high water content — fills you up", "Fiber + water = appetite suppression for 3-4 hours", "Vitamin B6 optimizes fat metabolism at the cellular level"], "tip": "Add bell peppers to every meal — they boost metabolism without the heat of chili peppers!"},
            {"hook": "Bell peppers protect your eyes better than carrots gram for gram.", "theme": "EYES", "label": "EYE HEALTH", "points": ["Lutein + zeaxanthin — highest of any sweet vegetable", "Reduces macular degeneration risk by 43%", "Beta-carotene (red) provides Vitamin A for night vision", "Vitamin C reduces cataract formation risk by 32%", "Zeaxanthin filters blue light — protects retina from screens"], "tip": "Yellow bell peppers have the most lutein and zeaxanthin — great for screen-heavy days!"},
            {"hook": "Bell peppers can heal leaky gut and reduce intestinal inflammation by 30%.", "theme": "GUT HEALTH", "label": "GUT HEALTH", "points": ["Capsanthin reduces intestinal permeability (leaky gut)", "Fiber feeds beneficial Lactobacillus gut bacteria", "Quercetin reduces gut inflammation markers by 30%", "Vitamin C maintains intestinal lining integrity", "Antioxidants protect gut microbiome from oxidative stress"], "tip": "Eat raw bell peppers for maximum gut benefit — cooking reduces quercetin by 25%!"},
        ],
    },
    {
        "name": "Cucumber", "emoji": "🥒", "category": "NIGHTSHADE", "accent_rgb": (22, 163, 74),
        "slide_searches": ["cucumber fresh whole", "cucumber sliced thin", "cucumber water drink", "fresh cucumbers market", "cucumber salad green"],
        "wikipedia": "Cucumber", "usda_fdc_id": 168409,
        "angles": [
            {"hook": "Cucumbers are 96% water — the best food for kidney flushing and hydration.", "theme": "HYDRATION", "label": "HYDRATION", "points": ["96% water content — best food-source of hydration", "Electrolytes: potassium, magnesium, sodium in perfect balance", "Silica helps kidneys process uric acid and flush toxins", "Reduces kidney stone formation by keeping urine dilute", "More hydrating than plain water due to electrolyte content"], "tip": "Eat cucumber WITH the skin — the skin has 3x more silica than the flesh!"},
            {"hook": "Cucumbers contain lignans that reduce the risk of hormone-driven cancers by 34%.", "theme": "CANCER", "label": "CANCER PREVENTION", "points": ["Lignans reduce breast, uterine, ovarian cancer risk by 34%", "Cucurbitacins inhibit cancer cell signaling pathways", "Fisetin triggers apoptosis in prostate cancer cells", "Antioxidant beta-carotene prevents cellular DNA damage", "Silica supports immune cells that identify cancer cells"], "tip": "Eat the seeds too — they contain the most cucurbitacin, the cancer-fighting compound!"},
            {"hook": "Putting cucumbers on your skin reduces inflammation better than cortisone cream.", "theme": "SKIN", "label": "SKIN & BEAUTY", "points": ["Silica builds collagen and elastin in skin layers", "Reduces puffiness and inflammation when applied topically", "Vitamin K reduces dark circles under eyes", "Caffeic acid soothes skin irritation and sunburn", "Antioxidants prevent oxidative damage that ages skin"], "tip": "Cucumber + aloe vera gel = the most effective natural face mask for inflammation!"},
            {"hook": "Cucumbers lower blood sugar after meals as effectively as diabetic medication.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Inhibits alpha-glucosidase — the carb-digesting enzyme", "Reduces post-meal blood sugar spike by 28%", "Pectin fiber slows gastric emptying", "Cucurbitacins improve insulin secretion from the pancreas", "Extremely low GI (15) — safe for all diabetics"], "tip": "Eat cucumber WITH your carb-heavy meals — it dramatically blunts the blood sugar spike!"},
        ],
    },
    {
        "name": "Onion", "emoji": "🧅", "category": "ALLIUM", "accent_rgb": (180, 83, 9),
        "slide_searches": ["onion whole fresh", "red onion sliced", "onion layers raw", "onions market pile", "onion cut half"],
        "wikipedia": "Onion", "usda_fdc_id": 170000,
        "angles": [
            {"hook": "Onions contain quercetin — the most powerful natural antihistamine in existence.", "theme": "IMMUNITY", "label": "ALLERGY RELIEF", "points": ["Quercetin stabilizes mast cells — stops histamine release", "Reduces allergy symptoms better than Benadryl in studies", "Anti-inflammatory lowers hay fever symptoms by 35%", "Thiosulfinates kill bacteria including H. pylori", "Vitamin C boosts immune cell production by 50%"], "tip": "Red onions have 5x more quercetin than white — always choose red for immunity!"},
            {"hook": "Raw onions lower blood sugar by 40% within 4 hours of eating.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Reduces blood glucose by 40% — comparable to metformin", "Chromium enhances insulin sensitivity at receptor level", "Dipropyl disulfide boosts insulin secretion from pancreas", "Quercetin inhibits alpha-glucosidase enzyme", "Fiber slows carbohydrate digestion and glucose release"], "tip": "Eat onions RAW for maximum blood sugar effect — cooking reduces active compounds by 50%!"},
            {"hook": "Onions are the richest food source of quercetin — the compound that fights cancer.", "theme": "CANCER", "label": "CANCER PREVENTION", "points": ["Quercetin induces apoptosis in colon, lung, breast cancer cells", "Organosulfur compounds prevent DNA damage", "Reduces stomach cancer risk by 56% in high consumers", "Fisetin inhibits tumor growth and spread", "Anthocyanins in red onions 3x more potent than blueberries"], "tip": "Let cut onion sit for 15 minutes before cooking — this maximizes quercetin bioavailability!"},
            {"hook": "Onions rebuild bone density by activating bone-forming cells by 20%.", "theme": "BONES", "label": "BONE HEALTH", "points": ["Gamma-L-glutamyl peptides inhibit bone loss enzymes", "Increases bone density by 5% in postmenopausal women", "Quercetin inhibits osteoclasts (bone-dissolving cells)", "Calcium (25mg) + Vitamin C = better absorption than supplements", "Reduces risk of hip fracture by 20% in women over 50"], "tip": "Eat onions daily — the bone density study used daily onion consumption over 8 weeks!"},
        ],
    },
    {
        "name": "Tomato", "emoji": "🍅", "category": "NIGHTSHADE", "accent_rgb": (220, 38, 38),
        "slide_searches": ["tomato fresh red whole", "tomatoes bunch vine", "tomato sliced red", "cherry tomatoes bowl", "tomato market fresh"],
        "wikipedia": "Tomato", "usda_fdc_id": 170457,
        "angles": [
            {"hook": "Cooked tomatoes have 5x more lycopene than raw — cooking actually helps.", "theme": "CANCER", "label": "CANCER PREVENTION", "points": ["Lycopene reduces prostate cancer risk by 35%", "Cooking increases lycopene bioavailability by 500%", "Reduces breast cancer risk by 26% in high consumers", "Chlorogenic acid prevents DNA damage in colon cells", "Beta-carotene reduces risk of lung cancer in non-smokers"], "tip": "Cook tomatoes in olive oil — lycopene is fat-soluble, absorption increases 5x with fat!"},
            {"hook": "Eating tomatoes 5x per week reduces heart attack risk by 29%.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Lycopene prevents LDL oxidation — stops artery clogging", "Reduces platelet aggregation — prevents dangerous clots", "Potassium (292mg) lowers blood pressure naturally", "Folate reduces homocysteine — key heart risk marker", "Vitamin C prevents arterial wall inflammation"], "tip": "Tomato paste has 10x more lycopene than fresh tomatoes — use it freely in cooking!"},
            {"hook": "Tomatoes protect skin from sunburn better than SPF 4 sunscreen.", "theme": "SKIN", "label": "SKIN PROTECTION", "points": ["Lycopene reduces sunburn sensitivity by 33%", "Acts as internal SPF — absorbs UV radiation", "Vitamin C builds collagen — reduces wrinkle depth", "Beta-carotene provides golden skin tone from inside", "Antioxidants prevent UV-induced skin aging"], "tip": "5 tablespoons tomato paste daily for 12 weeks — that's the internal sunscreen dose from studies!"},
            {"hook": "Tomatoes restore bone density lost during menopause within 4 months.", "theme": "BONES", "label": "BONE HEALTH", "points": ["Lycopene reduces oxidative stress that weakens bones", "Increases osteocalcin — bone formation marker by 22%", "Reduces N-telopeptide — bone breakdown marker", "Vitamin K activates bone-building proteins", "Calcium + lycopene work synergistically for bone density"], "tip": "Eat tomatoes with dairy — the calcium + lycopene combination maximizes bone rebuilding!"},
        ],
    },
]

# Combined list for the selection logic

HERBS = [
    {
        "name": "Basil", "emoji": "🌿", "category": "HERB", "accent_rgb": (21, 128, 61),
        "slide_searches": ["fresh basil leaves", "basil herb green", "basil bunch market", "fresh basil close up", "basil plant leaves"],
        "wikipedia": "Basil", "usda_fdc_id": 172232,
        "angles": [
            {"hook": "Basil has more antioxidants per gram than blueberries.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT POWER", "points": ["Orientin and vicenin protect cells from DNA damage", "Eugenol blocks free radical chain reactions", "Beta-carotene converts to Vitamin A — immune defender", "Rosmarinic acid is 3x more potent than Vitamin E", "Anti-inflammatory lowers CRP by 21% in regular users"], "tip": "Use fresh basil, not dried — fresh has 4x more active antioxidants!"},
            {"hook": "Basil oil kills antibiotic-resistant bacteria that drugs can't touch.", "theme": "IMMUNITY", "label": "ANTIMICROBIAL", "points": ["Eugenol kills E. coli, Listeria, and Staphylococcus", "Effective against 23 strains of drug-resistant bacteria", "Linalool disrupts bacterial cell membrane integrity", "Antifungal against Candida albicans overgrowth", "Antiviral compounds inhibit herpes simplex replication"], "tip": "Add fresh basil to salads — eugenol remains active without heat processing!"},
            {"hook": "Basil lowers blood sugar by 17% without any side effects.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Reduces fasting blood glucose by 17% in studies", "Eugenol inhibits alpha-glucosidase enzyme", "Improves insulin sensitivity in pancreatic cells", "Magnesium (64mg/100g) activates insulin receptors", "Anti-inflammatory protects pancreatic beta cells from damage"], "tip": "Eat basil WITH carb-heavy meals — that is when its blood sugar blocking effect is strongest!"},
            {"hook": "Basil is a natural adaptogen that reduces cortisol and anxiety.", "theme": "STRESS", "label": "STRESS RELIEF", "points": ["Holy basil (tulsi) reduces cortisol by 30% in trials", "Linalool activates GABA receptors — natural calming effect", "Reduces anxiety scores equal to diazepam in animal studies", "Adaptogenic compounds normalize stress hormone response", "Ursolic acid protects brain from stress-induced damage"], "tip": "Brew fresh basil tea before bed — linalool activates GABA receptors within 30 minutes!"},
        ],
    },
    {
        "name": "Rosemary", "emoji": "🌿", "category": "HERB", "accent_rgb": (20, 184, 166),
        "slide_searches": ["rosemary herb fresh", "rosemary sprig green", "fresh rosemary close up", "rosemary bunch aromatic", "rosemary plant sprigs"],
        "wikipedia": "Rosemary", "usda_fdc_id": 172231,
        "angles": [
            {"hook": "Smelling rosemary for 5 minutes improves memory by 75% — University of Northumbria.", "theme": "BRAIN", "label": "MEMORY BOOST", "points": ["1,8-cineole crosses blood-brain barrier via inhalation", "Improves speed and accuracy on memory tests by 75%", "Inhibits acetylcholinesterase — same mechanism as Alzheimer drugs", "Carnosic acid protects neurons from oxidative damage", "Increases cerebral blood flow within minutes of exposure"], "tip": "Put a sprig of rosemary on your desk while studying — aroma alone boosts recall by 75%!"},
            {"hook": "Rosemary extract prevents Alzheimer's plaques better than some medications.", "theme": "ALZHEIMERS", "label": "BRAIN PROTECTION", "points": ["Carnosic acid activates Nrf2 — master brain antioxidant switch", "Rosmarinic acid inhibits amyloid-beta aggregation", "Prevents tau protein tangles — second Alzheimer marker", "Reduces neuroinflammation by 40% in brain tissue studies", "BDNF increase supports formation of new neural connections"], "tip": "Add rosemary to ALL cooked meats — it also prevents carcinogen formation during grilling!"},
            {"hook": "Rosemary oil applied to the scalp regrows hair as effectively as minoxidil.", "theme": "HAIR", "label": "HAIR GROWTH", "points": ["Equals minoxidil (Rogaine) for hair regrowth in 6-month trial", "Improves scalp circulation — feeds hair follicles", "Carnosic acid regenerates nerve growth in follicles", "Anti-inflammatory reduces scalp DHT (hair loss hormone)", "Results visible in 3-6 months of daily application"], "tip": "Mix rosemary essential oil with coconut oil, massage into scalp nightly — clinical dose is 15 drops!"},
            {"hook": "Rosemary has the highest antioxidant activity of any dried herb on Earth.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT KING", "points": ["ORAC score of 165,280 — highest of all dried herbs", "Carnosol inhibits cancer cell growth in 5 different cancer types", "Rosmarinic acid is 3x more potent than Vitamin E", "Ursolic acid prevents fat cell formation and muscle wasting", "Preserves food from oxidation better than BHA/BHT additives"], "tip": "Add rosemary to grilled meats — it reduces cancer-causing HCAs by up to 90%!"},
        ],
    },
    {
        "name": "Cilantro", "emoji": "🌿", "category": "HERB", "accent_rgb": (74, 222, 128),
        "slide_searches": ["cilantro fresh herb", "cilantro leaves green", "fresh cilantro bunch", "cilantro herb close up", "coriander leaves fresh"],
        "wikipedia": "Coriander", "usda_fdc_id": 169998,
        "angles": [
            {"hook": "Cilantro removes heavy metals from your brain and organs within 2 weeks.", "theme": "DETOX", "label": "HEAVY METAL DETOX", "points": ["Binds mercury, lead, aluminum, arsenic in tissue", "Mobilizes heavy metals from the brain and nervous system", "Removes more heavy metals than EDTA chelation in animal studies", "Antioxidants protect organs WHILE metals are being removed", "2 tablespoons daily for 2 weeks produces measurable detox effect"], "tip": "Blend cilantro into a smoothie daily for 2 weeks — that is the detox protocol timeframe!"},
            {"hook": "Cilantro lowers blood sugar faster than metformin in animal studies.", "theme": "DIABETES", "label": "BLOOD SUGAR", "points": ["Stimulates insulin secretion from pancreatic beta cells", "Inhibits alpha-glucosidase — slows carb digestion", "Reduces fasting blood glucose by 20% in trials", "Anti-inflammatory protects insulin-producing cells", "Magnesium activates 300+ glucose-regulating enzymes"], "tip": "Add cilantro to every meal — it works best when consumed consistently with carbohydrates!"},
            {"hook": "Cilantro is the most powerful natural food for killing Salmonella.", "theme": "IMMUNITY", "label": "ANTIMICROBIAL", "points": ["Dodecenal kills Salmonella with twice the potency of gentamicin", "Effective against 12 different infectious bacterial strains", "Antifungal compounds fight Candida and fungal infections", "Linalool disrupts bacterial cell membranes on contact", "Used medicinally for food poisoning prevention for 3000+ years"], "tip": "Add cilantro to raw fish dishes like ceviche — dodecenal kills bacteria on contact!"},
            {"hook": "Cilantro seed (coriander) lowers cholesterol as effectively as statin drugs.", "theme": "HEART", "label": "HEART HEALTH", "points": ["Reduces total cholesterol by 24% in 30-day studies", "Increases HDL (good) cholesterol by 17%", "Coriander seeds lower triglycerides by 15%", "Potassium (521mg/100g) lowers blood pressure", "Antioxidants prevent LDL oxidation in artery walls"], "tip": "Use both leaves AND seeds — they have different compounds that work synergistically for heart health!"},
        ],
    },
    {
        "name": "Mint", "emoji": "🌿", "category": "HERB", "accent_rgb": (52, 211, 153),
        "slide_searches": ["mint leaves fresh green", "fresh mint herb", "mint bunch close up", "peppermint leaves fresh", "spearmint herb fresh"],
        "wikipedia": "Mentha", "usda_fdc_id": 173474,
        "angles": [
            {"hook": "Peppermint oil relieves IBS as effectively as antispasmodic drugs.", "theme": "DIGESTION", "label": "DIGESTION", "points": ["Menthol relaxes intestinal smooth muscle — stops cramping", "Reduces IBS symptoms by 40% in double-blind trials", "Enteric-coated capsules outperform buscopan for IBS pain", "Kills H. pylori bacteria — root cause of stomach ulcers", "Speeds gastric emptying — relieves bloating within 30 minutes"], "tip": "Drink peppermint tea AFTER meals, not before — menthol works on food already in the gut!"},
            {"hook": "Smelling peppermint boosts athletic performance by 15% — inhale before exercise.", "theme": "PERFORMANCE", "label": "ATHLETIC BOOST", "points": ["Increases grip strength and jump performance by 15%", "Menthol reduces perceived exertion during exercise", "Improves oxygen uptake efficiency by 5%", "Reduces fatigue and improves motivation during workouts", "Brain activation from aroma increases muscle activation signals"], "tip": "Apply peppermint oil under your nose before training — the effect starts within 5 minutes!"},
            {"hook": "Mint kills oral bacteria and heals gum disease better than mouthwash.", "theme": "ORAL HEALTH", "label": "ORAL HEALTH", "points": ["Menthol kills Streptococcus mutans — the main cavity bacteria", "Reduces gum inflammation by 29% versus placebo rinse", "Inhibits plaque formation better than commercial mouthwash", "Rosmarinic acid heals gum tissue inflammation", "Antibacterial film lasts 3 hours after chewing fresh mint"], "tip": "Chew fresh mint leaves after meals — antibacterial effect lasts 3x longer than brushing!"},
            {"hook": "Peppermint oil applied to the forehead relieves tension headaches as well as acetaminophen.", "theme": "PAIN RELIEF", "label": "HEADACHE RELIEF", "points": ["As effective as 1000mg acetaminophen for tension headaches", "Menthol inhibits serotonin receptors that trigger head pain", "Increases skin blood flow — reduces pressure sensation", "Works within 15 minutes of topical application", "No liver damage risk unlike regular painkiller use"], "tip": "Dilute 2 drops peppermint oil in coconut oil, apply to temples and forehead — relief in 15 minutes!"},
        ],
    },
    {
        "name": "Parsley", "emoji": "🌿", "category": "HERB", "accent_rgb": (22, 163, 74),
        "slide_searches": ["parsley fresh green herb", "fresh parsley bunch", "parsley leaves close up", "flat leaf parsley", "curly parsley herb"],
        "wikipedia": "Parsley", "usda_fdc_id": 170416,
        "angles": [
            {"hook": "Parsley has more Vitamin C than an orange and more Vitamin K than any other herb.", "theme": "NUTRITION", "label": "NUTRITION POWERHOUSE", "points": ["133mg Vitamin C per 100g — beats oranges", "1640% daily Vitamin K per 100g — #1 of all herbs", "Rich in folate, iron, potassium, and magnesium", "Apigenin — a powerful flavonoid not found in most foods", "Only 36 calories per 100g — pure nutrition density"], "tip": "Add a whole cup of parsley to smoothies — the flavor disappears but the nutrients stay!"},
            {"hook": "Apigenin in parsley kills cancer cells and shrinks tumors in groundbreaking studies.", "theme": "CANCER", "label": "CANCER RESEARCH", "points": ["Apigenin triggers apoptosis in breast, colon, thyroid cancer cells", "Reduces tumor blood supply (anti-angiogenic effect)", "Inhibits cancer stem cell self-renewal", "Luteolin blocks cancer cell migration and metastasis", "Myristicin in parsley oil activates glutathione S-transferase"], "tip": "Eat parsley raw and in large amounts — cooking destroys 30% of apigenin!"},
            {"hook": "Parsley flushes kidneys and reduces kidney stone risk better than any drug.", "theme": "KIDNEY", "label": "KIDNEY HEALTH", "points": ["Diuretic compounds increase urine output by 24%", "Reduces urinary calcium excretion — prevents stone formation", "Apigenin relaxes ureter muscles for easier stone passage", "Antibacterial against E. coli — #1 cause of UTIs", "Reduces uric acid buildup that causes gout and kidney damage"], "tip": "Drink fresh parsley tea daily for 2 weeks to flush the kidneys — use 1 bunch per liter!"},
            {"hook": "Parsley reverses bone loss and prevents fractures better than calcium supplements.", "theme": "BONES", "label": "BONE HEALTH", "points": ["1640% daily Vitamin K activates osteocalcin — bone building protein", "Reduces fracture risk by 35% in postmenopausal women", "Boron in parsley reduces calcium excretion through urine", "Folate reduces homocysteine that weakens bone matrix", "Vitamin C essential for collagen synthesis in bone tissue"], "tip": "1/4 cup parsley daily gives you more than your entire Vitamin K needs for bone health!"},
        ],
    },
    {
        "name": "Thyme", "emoji": "🌿", "category": "HERB", "accent_rgb": (134, 239, 172),
        "slide_searches": ["thyme herb fresh", "fresh thyme sprigs", "thyme bunch green", "thyme herb close up", "thyme leaves sprig"],
        "wikipedia": "Thyme", "usda_fdc_id": 172233,
        "angles": [
            {"hook": "Thyme syrup outperforms codeine-based cough syrup in clinical trials.", "theme": "RESPIRATORY", "label": "LUNG HEALTH", "points": ["Thymol relaxes bronchial smooth muscle — stops coughing", "As effective as codeine syrup for acute bronchitis", "Kills Streptococcus pneumoniae — common pneumonia bacteria", "Expectorant effect clears mucus from airways naturally", "Anti-inflammatory reduces airway swelling and irritation"], "tip": "Brew thyme tea with honey for coughs — as effective as pharmacy syrups, no drowsiness!"},
            {"hook": "Thyme is the most potent natural antimicrobial against food-borne pathogens.", "theme": "IMMUNITY", "label": "ANTIMICROBIAL", "points": ["Thymol kills E. coli, Salmonella, and Campylobacter", "More effective than tea tree oil against Staphylococcus", "Carvacrol destroys fungal cell membranes on contact", "Antiviral against influenza A and B viruses", "Kills biofilm-protected bacteria that antibiotics miss"], "tip": "Add thyme to raw meat marinades — thymol kills surface bacteria within 5 minutes of contact!"},
            {"hook": "Thymol in thyme is the active ingredient in most commercial mouthwashes.", "theme": "ORAL HEALTH", "label": "ORAL HEALTH", "points": ["Thymol is the active ingredient in Listerine mouthwash", "Kills oral bacteria responsible for cavities and gum disease", "Reduces plaque formation equal to chlorhexidine rinse", "Anti-inflammatory heals gum tissue irritation", "Freshens breath for up to 6 hours after use"], "tip": "Make thyme mouthwash: steep 2 tsp thyme in hot water, cool, gargle 60 seconds!"},
            {"hook": "Thyme has the highest antioxidant density of any fresh herb per gram.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT POWER", "points": ["ORAC score of 27,426 per 100g — #1 fresh herb", "Luteolin prevents oxidative damage to brain cells", "Zeaxanthin protects eyes from UV-induced macular damage", "Rosmarinic acid suppresses inflammatory gene expression", "Vitamin C (160mg/100g) — higher than most citrus fruits"], "tip": "Use fresh thyme generously — a single tablespoon delivers more antioxidants than a cup of broccoli!"},
        ],
    },
    {
        "name": "Oregano", "emoji": "🌿", "category": "HERB", "accent_rgb": (163, 230, 53),
        "slide_searches": ["oregano herb fresh", "fresh oregano leaves", "oregano bunch green", "oregano sprig close up", "wild oregano plant"],
        "wikipedia": "Oregano", "usda_fdc_id": 171328,
        "angles": [
            {"hook": "Oregano oil kills Candida overgrowth as effectively as prescription antifungals.", "theme": "IMMUNITY", "label": "ANTIFUNGAL POWER", "points": ["Carvacrol disrupts fungal cell membranes on contact", "As effective as fluconazole (Diflucan) for Candida in studies", "Kills 16 different Candida strains including drug-resistant ones", "Thymol works synergistically with carvacrol — combo effect", "Eradicates biofilm-protected Candida that antifungals miss"], "tip": "Wild oregano oil has 5x more carvacrol than store-bought — look for Origanum vulgare!"},
            {"hook": "Oregano has 42x more antioxidants than apples — the most of any culinary herb.", "theme": "ANTIOXIDANTS", "label": "ANTIOXIDANT CHAMPION", "points": ["ORAC score of 175,295 — highest of all culinary herbs", "42x more antioxidants than apples per gram", "4x more than blueberries per gram of active compounds", "Rosmarinic acid prevents cell membrane oxidation", "Quercetin and luteolin protect DNA from double-strand breaks"], "tip": "Dried oregano has MORE antioxidants than fresh — heat concentrates the active compounds!"},
            {"hook": "Carvacrol in oregano stops cancer cells from spreading in 7 different cancer types.", "theme": "CANCER", "label": "CANCER RESEARCH", "points": ["Carvacrol induces apoptosis in prostate, breast, and lung cancer", "Inhibits cancer cell migration and invasion by 90%", "Ursolic acid prevents metastasis by blocking MMP-9 enzyme", "Beta-caryophyllene activates anti-tumor immune response", "Works synergistically with chemotherapy drugs in studies"], "tip": "Use oregano generously in cooking — even small culinary amounts deliver measurable carvacrol!"},
            {"hook": "Oregano reduces gut permeability (leaky gut) within 2 weeks of daily use.", "theme": "GUT HEALTH", "label": "GUT HEALTH", "points": ["Carvacrol kills harmful bacteria while preserving beneficial ones", "Reduces intestinal permeability markers by 35%", "Thymol heals tight junction proteins in gut lining", "Prebiotics in oregano feed Lactobacillus and Bifidobacterium", "Anti-parasitic — kills Giardia and Blastocystis hominis"], "tip": "Take oregano oil in capsules to protect gut lining on an antibiotic course!"},
        ],
    },
    {
        "name": "Lavender", "emoji": "💜", "category": "HERB", "accent_rgb": (139, 92, 246),
        "slide_searches": ["lavender flowers purple", "lavender herb fresh", "lavender field purple", "lavender bunch close up", "fresh lavender sprigs"],
        "wikipedia": "Lavandula", "usda_fdc_id": 172234,
        "angles": [
            {"hook": "Lavender oil reduces anxiety as effectively as lorazepam — with zero dependency risk.", "theme": "ANXIETY", "label": "ANXIETY RELIEF", "points": ["Linalool binds GABA-A receptors — the same target as benzodiazepines", "Silexan (lavender oil capsule) equals lorazepam for generalized anxiety", "Reduces cortisol levels by 24% after 15 minutes of inhalation", "No dependency, no withdrawal, no cognitive impairment", "Improves sleep quality alongside anxiety reduction"], "tip": "Inhale lavender essential oil for 15 minutes before stressful events — cortisol drops measurably!"},
            {"hook": "Lavender improves deep sleep by 20% and reduces nighttime awakenings.", "theme": "SLEEP", "label": "SLEEP AID", "points": ["Increases slow-wave (deep) sleep by 20% in studies", "Reduces nighttime awakenings by 31%", "Lowers heart rate and blood pressure before sleep onset", "Improves next-day alertness and vigor scores", "Works within 30 minutes of inhalation"], "tip": "Put 2 drops lavender oil on your pillow — deep sleep improvement is measurable by night 3!"},
            {"hook": "Lavender speeds wound healing and reduces scar formation by 40%.", "theme": "HEALING", "label": "SKIN HEALING", "points": ["Linalool accelerates wound closure by stimulating collagen synthesis", "Reduces scar tissue formation by 40% versus controls", "Anti-inflammatory prevents excessive healing response", "Antimicrobial prevents infection while wound heals", "Promotes faster granulation tissue formation"], "tip": "Dilute lavender oil in coconut oil (3 drops per tsp), apply to cuts and burns for faster healing!"},
            {"hook": "Lavender reduces chemotherapy-related nausea by 62% — used in cancer centers.", "theme": "NAUSEA", "label": "NAUSEA RELIEF", "points": ["Aromatherapy reduces chemo-induced nausea by 62%", "Used in oncology wards at major cancer treatment centers", "Works faster than anti-nausea medication in some patients", "Linalool normalizes serotonin signaling in the gut-brain axis", "No drug interactions — safe alongside chemotherapy"], "tip": "Inhale lavender oil directly from the bottle at the first sign of nausea — relief in under 5 minutes!"},
        ],
    },
]

PRODUCE = FRUITS + VEGETABLES + HERBS

CATEGORIES = {
    "CITRUS":    {"rgb": (251, 146,  60), "emoji": "🍊", "label": "CITRUS"},
    "BERRY":     {"rgb": (244,  63,  94), "emoji": "🫐", "label": "BERRY"},
    "TROPICAL":  {"rgb": (245, 158,  11), "emoji": "🌴", "label": "TROPICAL"},
    "TREE":      {"rgb": (220,  38,  38), "emoji": "🌳", "label": "TREE FRUIT"},
    "MELON":     {"rgb": ( 34, 197,  94), "emoji": "🍉", "label": "MELON"},
    "SUPERFOOD":    {"rgb": ( 16, 185, 129), "emoji": "✨",  "label": "SUPERFOOD"},
    "CRUCIFEROUS":  {"rgb": ( 34, 197,  94), "emoji": "🥦",  "label": "CRUCIFEROUS"},
    "LEAFY":        {"rgb": ( 21, 128,  61), "emoji": "🥬",  "label": "LEAFY GREEN"},
    "ROOT":         {"rgb": (234,  88,  12), "emoji": "🥕",  "label": "ROOT VEG"},
    "ALLIUM":       {"rgb": (217, 119,   6), "emoji": "🧄",  "label": "ALLIUM"},
    "NIGHTSHADE":   {"rgb": (220,  38,  38), "emoji": "🍅",  "label": "NIGHTSHADE"},
    "SPICE":        {"rgb": (234, 179,   8), "emoji": "🌿",  "label": "SPICE"},
    "HERB":         {"rgb": ( 74, 222, 128), "emoji": "🌿",  "label": "HERB"},
}

SLIDE_LABELS = ["", "WHY IT MATTERS", "TOP BENEFITS", "DID YOU KNOW?", "NUTRITION FACTS", ""]

BG_DARK  = (13,  17,  28)
BG_CARD  = (22,  33,  56)
C_WHITE  = (255, 255, 255)
C_GRAY   = (148, 163, 184)
C_BLACK  = (  0,   0,   0)


# ─────────────────────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────────────────────
def setup_fonts():
    for url, path in [(FONT_BOLD_URL, FONT_BOLD_PATH), (FONT_REG_URL, FONT_REG_PATH), (FONT_EMOJI_URL, FONT_EMOJI_PATH)]:
        if not os.path.exists(path):
            print(f"  Downloading font from {url} …")
            r = requests.get(url, timeout=60)
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

def get_emoji_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_EMOJI_PATH, size)
    except Exception:
        return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# FRUIT SELECTION
# ─────────────────────────────────────────────────────────────────────────────
RECENT_FILE = "/tmp/recent_produce_angles.txt"
MAX_RECENT = 88

def get_recent() -> list[str]:
    try:
        with open(RECENT_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def save_recent(key: str):
    recent = get_recent()
    recent.append(key)
    if len(recent) > MAX_RECENT:
        recent = recent[-MAX_RECENT:]
    with open(RECENT_FILE, "w") as f:
        f.write("\n".join(recent))

def pick_fruit_and_angle() -> tuple[dict, int]:
    recent = get_recent()
    combos = []
    for fruit in PRODUCE:
        for angle_idx in range(len(fruit["angles"])):
            key = f"{fruit['name']}:{angle_idx}"
            if key not in recent:
                combos.append((fruit, angle_idx, key))
    if not combos:
        try: os.remove(RECENT_FILE)
        except OSError: pass
        combos = []
        for fruit in PRODUCE:
            for angle_idx in range(len(fruit["angles"])):
                key = f"{fruit['name']}:{angle_idx}"
                combos.append((fruit, angle_idx, key))
    fruit, angle_idx, key = random.choice(combos)
    save_recent(key)
    return fruit, angle_idx


# ─────────────────────────────────────────────────────────────────────────────
# PIXABAY API — Free, instant signup, search-based, accurate photos
# ─────────────────────────────────────────────────────────────────────────────
def search_pixabay(query: str, per_page: int = 3) -> list[str]:
    """
    Search Pixabay for photos matching the query.
    Returns a list of image URLs.
    Free API: 5000 requests/hour. Signup at https://pixabay.com/api/docs/
    """
    if not PIXABAY_API_KEY:
        return []
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "per_page": per_page,
                "safesearch": "true",
                "lang": "en",
                "min_width": 800,
            },
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", [])
        urls = []
        for hit in hits:
            url = hit.get("largeImageURL") or hit.get("webformatURL", "")
            if url:
                urls.append(url)
        return urls
    except Exception as e:
        print(f"    ⚠️  Pixabay search failed for '{query}': {e}")
        return []


def fetch_single_image(url: str) -> Image.Image | None:
    """Download a single image and return as 1080×1080 cropped PIL image."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            return None
        img = Image.open(BytesIO(r.content)).convert("RGB")
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img  = img.crop((left, top, left + side, top + side))
        img  = img.resize((IMG_W, IMG_H), Image.LANCZOS)
        return img
    except Exception as e:
        print(f"    ⚠️  Image download failed: {e}")
        return None


def fetch_fruit_images(slide_searches: list[str], fruit_name: str, num_slides: int) -> list[Image.Image | None]:
    """
    Fetch a different image for each slide using Pexels search API.
    
    Strategy:
    1. Pre-fetch ALL photo URLs for ALL search queries at once (fewer API calls)
    2. Assign different photos to different slides
    3. If Pexels fails, use a generic fruit search
    4. If all fails, return None (will use dark background)
    """
    photos: list[Image.Image | None] = [None] * num_slides
    all_urls: list[str] = []
    
    print(f"  📷 Fetching {num_slides} fruit photos via Pixabay API…")
    
    # Pre-fetch: Collect URLs from all search queries
    if PIXABAY_API_KEY:
        for i, query in enumerate(slide_searches):
            print(f"    🔍 Searching Pixabay for: '{query}'")
            urls = search_pixabay(query, per_page=2)
            all_urls.extend(urls)
            time.sleep(0.3)  # Be nice to the API
        
        # Also search generic fruit name as backup
        if len(all_urls) < num_slides:
            print(f"    🔍 Backup search: '{fruit_name} fruit fresh'")
            backup_urls = search_pixabay(f"{fruit_name} fruit fresh", per_page=5)
            all_urls.extend(backup_urls)
    else:
        print("    ⚠️  No PIXABAY_API_KEY set — photos will use dark background!")
        print("    → Get free key at: https://pixabay.com/api/docs/")
    
    # Download and assign photos to slides
    last_successful: Image.Image | None = None
    for i in range(num_slides):
        # CTA slide (last) reuses previous photo
        if i == num_slides - 1:
            if last_successful:
                photos[i] = last_successful.copy()
                print(f"    ✅ Slide {i+1} reusing photo (CTA slide)")
            else:
                photos[i] = None
                print(f"    ℹ️  Slide {i+1} dark background (CTA)")
            continue
        
        # Try to get a photo for this slide
        photo = None
        url_idx = i  # Each slide gets a different URL from the pre-fetched list
        while url_idx < len(all_urls) and photo is None:
            photo = fetch_single_image(all_urls[url_idx])
            if photo is None:
                url_idx += 1  # Try next URL
        
        if photo:
            photos[i] = photo
            last_successful = photo
            print(f"    ✅ Slide {i+1} photo loaded!")
        elif last_successful:
            photos[i] = last_successful.copy()
            print(f"    ℹ️  Slide {i+1} reusing previous photo")
        else:
            photos[i] = None
            print(f"    ⚠️  Slide {i+1} no photo available (dark background)")
    
    return photos


# ─────────────────────────────────────────────────────────────────────────────
# WIKIPEDIA API
# ─────────────────────────────────────────────────────────────────────────────
def fetch_wikipedia_extract(article_title: str) -> str:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{article_title}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        extract = data.get("extract", "")
        if extract: print(f"  📖 Wikipedia: {extract[:100]}…")
        return extract
    except Exception as e:
        print(f"  ⚠️  Wikipedia fetch failed: {e}")
        return ""

def extract_fun_facts_from_wiki(wiki_text: str, fruit_name: str) -> str:
    if not wiki_text:
        return f"{fruit_name} is one of the most nutritious fruits you can eat!"
    sentences = re.split(r'(?<=[.!?])\s+', wiki_text)
    fact = " ".join(sentences[:2])
    if len(fact) > 150: fact = fact[:147] + "..."
    return fact


# ─────────────────────────────────────────────────────────────────────────────
# USDA API
# ─────────────────────────────────────────────────────────────────────────────
def fetch_usda_nutrition(fdc_id: int) -> dict | None:
    if not USDA_API_KEY: return None
    try:
        url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
        r = requests.get(url, params={"api_key": USDA_API_KEY}, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        nutrients = {}
        for n in data.get("foodNutrients", []):
            name = n.get("nutrient", {}).get("name", "")
            amount = n.get("amount", 0)
            unit = n.get("nutrient", {}).get("unitName", "")
            if name and amount: nutrients[name] = f"{amount:.0f}{unit}"
        if nutrients: print(f"  🥗 USDA: Found {len(nutrients)} nutrients")
        return nutrients
    except Exception as e:
        print(f"  ⚠️  USDA fetch failed: {e}")
        return None

def format_nutrition_line(fruit: dict, usda_data: dict | None) -> str:
    if usda_data:
        vit_c  = usda_data.get("Vitamin C, total ascorbic acid", "")
        fiber  = usda_data.get("Fiber, total dietary", "")
        potas  = usda_data.get("Potassium, K", "")
        cal    = usda_data.get("Energy", "")
        parts = []
        if cal:    parts.append(f"{cal} kcal")
        if fiber:  parts.append(f"{fiber} fiber")
        if vit_c:  parts.append(f"{vit_c} Vit C")
        if potas:  parts.append(f"{potas} potassium")
        if parts: return " | ".join(parts[:4])
    return "Packed with vitamins, minerals, and antioxidants!"


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE CONTENT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def generate_slides_groq(fruit: dict, angle: dict) -> list[str] | None:
    prompt = f"""You are a health & wellness social media content writer.
Create content for a 6-slide Instagram carousel about: {fruit['name']} ({fruit['emoji']})
Focus angle: {angle['theme']} — {angle['hook']}

KEY FACTS TO INCLUDE:
{chr(10).join(f'- {p}' for p in angle['points'])}

INSTRUCTIONS:
- Write in English, casual & engaging tone
- Keep each slide SHORT (max 20 words)
- Slide 1: Punchy hook headline
- Slide 2: Why this matters
- Slide 3: Top 3 key benefits
- Slide 4: A surprising fact
- Slide 5: Nutrition highlight + practical tip
- Slide 6: CTA — "Follow for daily fruit facts!"

Format as JSON array only:
[
  {{"slide": 1, "text": "..."}},
  {{"slide": 2, "text": "..."}},
  {{"slide": 3, "text": "..."}},
  {{"slide": 4, "text": "..."}},
  {{"slide": 5, "text": "..."}},
  {{"slide": 6, "text": "..."}}
]"""
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.75, "max_tokens": 600},
            timeout=30,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        m = re.search(r"\[.*?\]", raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return [s["text"].strip() for s in data if "text" in s]
    except Exception as e:
        print(f"  ⚠️  Groq error: {e}")
    return None

def generate_slides(fruit: dict, angle: dict, wiki_text: str, nutrition_line: str) -> list[str]:
    if GROQ_API_KEY:
        print("  🤖 Generating content with Groq (Llama 3)…")
        texts = generate_slides_groq(fruit, angle)
        if texts and len(texts) >= 5: return texts
    print("  ✍️  Using curated fruit data + Wikipedia…")
    slide1 = angle["hook"]
    slide2 = f"{fruit['name']} is incredible for {angle['theme'].lower()} — here's what science says."
    benefits = angle["points"][:3]
    slide3 = " • ".join([f"✓ {b}" for b in benefits])
    if wiki_text:
        slide4 = extract_fun_facts_from_wiki(wiki_text, fruit["name"])
    else:
        slide4 = angle["points"][3] if len(angle["points"]) > 3 else f"{fruit['name']} is packed with surprising health benefits!"
    slide5 = f"📊 {nutrition_line}\n💡 {angle['tip']}"
    slide6 = f"Follow @{PAGE_NAME} for daily fruit health facts! 🍎🍊🫐"
    return [slide1, slide2, slide3, slide4, slide5, slide6]


# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND — NO OVERLAY, FRUIT 100% VISIBLE
# ─────────────────────────────────────────────────────────────────────────────
def make_bg(photo: Image.Image | None, accent: tuple) -> Image.Image:
    if photo:
        bg = photo.copy()
        bg = bg.resize((IMG_W, IMG_H), Image.LANCZOS)
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(1.05)
        tint = Image.new("RGB", (IMG_W, IMG_H), accent)
        bg = Image.blend(bg, tint, alpha=0.04)
        return bg
    else:
        bg = Image.new("RGB", (IMG_W, IMG_H), BG_DARK)
        draw = ImageDraw.Draw(bg)
        for y in range(IMG_H):
            alpha = int(30 * (1 - y / IMG_H))
            r = min(255, BG_DARK[0] + accent[0] * alpha // 255)
            g = min(255, BG_DARK[1] + accent[1] * alpha // 255)
            b = min(255, BG_DARK[2] + accent[2] * alpha // 255)
            draw.line([(0, y), (IMG_W, y)], fill=(r, g, b))
        return bg


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE GENERATION — NO OVERLAYS, TEXT WITH SHADOWS
# ─────────────────────────────────────────────────────────────────────────────
def draw_rounded_rect(draw, x0, y0, x1, y1, r, fill):
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
    draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)


def draw_text_with_shadow(draw, xy, text, font, fill, shadow_offset=4):
    x, y = xy
    for dx, dy in [(shadow_offset, shadow_offset), (shadow_offset+1, shadow_offset), (shadow_offset, shadow_offset+1)]:
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 200))
    draw.text((x, y), text, font=font, fill=fill)


def fit_text(draw, text: str, font_size: int, max_w: int, max_lines: int, bold=True):
    while font_size >= 28:
        font = get_font(font_size, bold=bold)
        words = text.split()
        lines, cur = [], []
        for word in words:
            test = " ".join(cur + [word])
            if draw.textbbox((0, 0), test, font=font)[2] > max_w and cur:
                lines.append(" ".join(cur))
                cur = [word]
            else: cur.append(word)
        if cur: lines.append(" ".join(cur))
        if len(lines) <= max_lines: return font, lines
        font_size -= 4
    return get_font(28, bold=bold), lines


def create_slide(text: str, idx: int, total: int, fruit: dict, angle: dict,
                 slide_photo: Image.Image | None = None) -> Image.Image:
    cat_data = CATEGORIES.get(fruit["category"], CATEGORIES["SUPERFOOD"])
    accent = cat_data["rgb"]
    cat_label = cat_data["label"]

    is_hook = idx == 0
    is_cta = idx == total - 1

    # Each slide gets its OWN photo (or None for dark bg)
    use_photo = slide_photo is not None and not is_cta
    bg = make_bg(slide_photo if use_photo else None, accent)

    img = bg.copy()
    draw = ImageDraw.Draw(img)

    # Top accent stripe
    draw.rectangle([(0, 0), (IMG_W, 10)], fill=accent)

    # Category pill — draw emoji + label separately so each uses the right font
    pill_font = get_font(24)
    emoji_font = get_emoji_font(24)
    pill_label = f"  {cat_label}"
    emoji_bbox = draw.textbbox((0, 0), fruit['emoji'], font=emoji_font)
    label_bbox = draw.textbbox((0, 0), pill_label, font=pill_font)
    pw = (emoji_bbox[2] - emoji_bbox[0]) + (label_bbox[2] - label_bbox[0]) + 36
    ph = 44
    px, py = 48, 32
    draw_rounded_rect(draw, px, py, px + pw, py + ph, 10, accent)
    draw.text((px + 18, py + 9), fruit['emoji'], font=emoji_font, fill=C_WHITE)
    emoji_w = emoji_bbox[2] - emoji_bbox[0]
    draw.text((px + 18 + emoji_w, py + 9), pill_label, font=pill_font, fill=C_WHITE)

    if not is_hook:
        name_font = get_font(22, bold=False)
        name_text = f"{fruit['name']} · {angle['theme']}"
        name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
        nw = name_bbox[2] + 30
        nx = px + pw + 12
        draw_rounded_rect(draw, nx, py, nx + nw, py + ph, 10, BG_CARD)
        draw.text((nx + 15, py + 9), name_text, font=name_font, fill=C_GRAY)

    # Slide counter
    ctr_font = get_font(24, bold=False)
    draw.text((IMG_W - 56, 42), f"{idx+1}/{total}", font=ctr_font, anchor="rm", fill=C_GRAY)

    # ══════════════ HOOK SLIDE ══════════════
    if is_hook:
        e_font = get_emoji_font(100)
        draw.text((IMG_W // 2, 240), fruit["emoji"], font=e_font, anchor="mm")

        font, lines = fit_text(draw, strip_emojis(text).upper(), 62, IMG_W - 120, 4)
        fs = font.size
        lh = fs + 16
        y = 420
        for line in lines:
            bx = draw.textbbox((0, 0), line, font=font)[2]
            x = (IMG_W - bx) // 2
            draw_text_with_shadow(draw, (x, y), line, font, C_WHITE, shadow_offset=5)
            y += lh

        draw.rectangle([(IMG_W//2 - 80, y + 20), (IMG_W//2 + 80, y + 26)], fill=accent)

        theme_font = get_font(22, bold=False)
        theme_text = angle['theme']
        draw.text((IMG_W // 2, IMG_H - 160), theme_text, font=theme_font, anchor="mm", fill=accent)

        prompt_font = get_font(24, bold=False)
        draw.text((IMG_W // 2, IMG_H - 130), "Swipe to learn why ->", font=prompt_font, anchor="mm", fill=C_GRAY)

    # ══════════════ CTA SLIDE ══════════════
    elif is_cta:
        e_font = get_emoji_font(120)
        draw.text((IMG_W // 2, 240), fruit["emoji"], font=e_font, anchor="mm")

        draw.text((IMG_W // 2, 450), "EAT MORE PLANTS", font=get_font(34, bold=False), anchor="mm", fill=C_GRAY)
        draw.text((IMG_W // 2, 530), f"Follow @{PAGE_NAME}", font=get_font(58), anchor="mm", fill=C_WHITE)
        draw.text((IMG_W // 2, 620), "Fruits, veggies & herbs - daily!", font=get_font(28, bold=False), anchor="mm", fill=C_GRAY)
        draw.rectangle([(160, 690), (IMG_W - 160, 697)], fill=accent)
        draw.text((IMG_W // 2, 740), "Save this post for your next grocery run!", font=get_font(24, bold=False), anchor="mm", fill=C_GRAY)

    # ══════════════ CONTENT SLIDES ══════════════
    else:
        label = SLIDE_LABELS[idx] if idx < len(SLIDE_LABELS) else ""

        if label:
            lbl_font = get_font(30)
            lbl_bbox = draw.textbbox((0, 0), label, font=lbl_font)
            lbl_w = lbl_bbox[2]
            lbl_x = (IMG_W - lbl_w) // 2
            lbl_y = 140
            draw_text_with_shadow(draw, (lbl_x, lbl_y), label, lbl_font, accent, shadow_offset=3)
            draw.rectangle([(lbl_x, lbl_y + lbl_bbox[3] + 6), (lbl_x + lbl_w, lbl_y + lbl_bbox[3] + 10)], fill=accent)

        # Body text — each line has a thin backdrop bar
        pad = 70
        max_w = IMG_W - pad * 2
        font, lines = fit_text(draw, strip_emojis(text), 54, max_w, 8)
        fs = font.size
        lh = fs + 18
        th = len(lines) * lh
        y = max(230, (IMG_H - th) // 2 + 10)

        # Draw backdrop bars behind text
        if use_photo:
            overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
            odraw = ImageDraw.Draw(overlay)
            for i, line in enumerate(lines):
                bbox = draw.textbbox((pad, y + i * lh), line, font=font)
                bar_padding = 6
                odraw.rectangle(
                    [(pad - 12, bbox[1] - bar_padding), (bbox[2] + 12, bbox[3] + bar_padding)],
                    fill=(0, 0, 0, 140)
                )
            img_rgba = img.convert("RGBA")
            img_rgba.alpha_composite(overlay)
            img = img_rgba.convert("RGB")
            draw = ImageDraw.Draw(img)

        # Draw text
        for i, line in enumerate(lines):
            colour = accent if i == 0 else C_WHITE
            draw_text_with_shadow(draw, (pad, y), line, font, colour, shadow_offset=3)
            y += lh

        # Accent left border
        bar_top = max(230, (IMG_H - th) // 2 + 10) - 8
        bar_bottom = bar_top + th + 8
        draw.rectangle([(36, bar_top), (42, bar_bottom)], fill=accent)

    # Bottom branding bar
    draw.rectangle([(0, IMG_H - 72), (IMG_W, IMG_H)], fill=BG_CARD)
    draw.rectangle([(0, IMG_H - 72), (IMG_W, IMG_H - 70)], fill=accent)
    brand_font = get_font(26, bold=False)
    draw.text((IMG_W // 2, IMG_H - 36), f"@{PAGE_NAME}", font=brand_font, anchor="mm", fill=C_GRAY)

    return img


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
def validate_access_token() -> bool:
    try:
        r = requests.get(
            f"{IG_BASE}/debug_token",
            params={"input_token": FB_ACCESS_TOKEN, "access_token": FB_ACCESS_TOKEN},
            timeout=10,
        )
        data = r.json()
        if r.ok and "data" in data:
            token_data = data["data"]
            is_valid = token_data.get("is_valid", False)
            expires_at = token_data.get("expires_at", 0)
            if not is_valid:
                print("  ❌ Token is INVALID or EXPIRED!")
                print("  → Go to: https://developers.facebook.com/tools/explorer/")
                return False
            current_time = int(time.time())
            days_left = (expires_at - current_time) // 86400
            if days_left <= 0:
                print("  ⚠️  Token expires VERY SOON!")
                return False
            elif days_left <= 7:
                print(f"  ⚠️  WARNING: Token expires in {days_left} days!")
            else:
                print(f"  ✅ Token is valid (expires in {days_left} days)")
            return True
        else:
            error_msg = data.get("error", {}).get("message", "Unknown error")
            print(f"  ❌ Token validation failed: {error_msg}")
            return False
    except Exception as e:
        print(f"  ⚠️  Could not validate token: {e}")
        return True


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE HOSTING
# ─────────────────────────────────────────────────────────────────────────────
def upload_to_imgbb(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=93)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    r = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API_KEY, "image": img_b64, "expiration": 600}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]["url"]


# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM GRAPH API
# ─────────────────────────────────────────────────────────────────────────────
def ig_post(path: str, **params) -> dict:
    r = requests.post(f"{IG_BASE}/{path}", params={"access_token": FB_ACCESS_TOKEN, **params}, timeout=30)
    if not r.ok: print(f"  IG API error: {r.status_code} — {r.text}")
    r.raise_for_status()
    return r.json()

def ig_get(path: str, **params) -> dict:
    r = requests.get(f"{IG_BASE}/{path}", params={"access_token": FB_ACCESS_TOKEN, **params}, timeout=15)
    r.raise_for_status()
    return r.json()

def upload_carousel_item(image_url: str) -> str:
    data = ig_post(f"{IG_USER_ID}/media", image_url=image_url, is_carousel_item="true")
    return data["id"]

def wait_for_container(cid: str, retries: int = 12, interval: int = 5):
    for attempt in range(retries):
        status = ig_get(cid, fields="status_code").get("status_code", "")
        print(f"    Container {cid}: {status}  (attempt {attempt+1}/{retries})")
        if status == "FINISHED": return
        if status == "ERROR": raise RuntimeError(f"Container {cid} errored during processing.")
        time.sleep(interval)
    raise TimeoutError(f"Container {cid} did not finish in time.")

def create_carousel(children: list[str], caption: str) -> str:
    data = ig_post(f"{IG_USER_ID}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)
    return data["id"]

def publish_media(creation_id: str) -> str:
    data = ig_post(f"{IG_USER_ID}/media_publish", creation_id=creation_id)
    return data["id"]

def post_comment(media_id: str, message: str) -> str:
    r = requests.post(f"{IG_BASE}/{media_id}/comments", params={"access_token": FB_ACCESS_TOKEN, "message": message}, timeout=30)
    if not r.ok: print(f"  ⚠️  Comment API error: {r.status_code} — {r.text}")
    r.raise_for_status()
    return r.json().get("id", "")


# ─────────────────────────────────────────────────────────────────────────────
# CAPTION
# ─────────────────────────────────────────────────────────────────────────────
def build_caption(fruit: dict, angle: dict) -> str:
    emoji = fruit["emoji"]
    name = fruit["name"]
    theme = angle["theme"]
    tags = f"#{name.lower().replace(' ', '')} #healthyeating #nutrition #healthfacts #eatrealfood #healthylifestyle #{theme.lower()} #wellness #healthtips #vitamins #antioxidants #cleaneating #plantbased #wholefoods #superfood"
    return f"{emoji} {name} — {angle['hook']}\n\n👉 Swipe to discover what {name} does for your {theme.lower()}!\n\n💾 Save this for your next grocery run!\n\n{tags}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print(f"  🌿 Benefits of Fruits, Vegetables & Herbs — Instagram Carousel Bot")
    print(f"  📅 {today}")
    print("=" * 60)

    # Validate token FIRST
    print("\n🔑 Validating Instagram access token…")
    if not validate_access_token():
        print("\n❌ ABORTING: Access token is expired or invalid.")
        print("   Fix: https://developers.facebook.com/tools/explorer/")
        sys.exit(1)

    print("\n📦 Setting up fonts…")
    setup_fonts()

    print("\n🎲 Selecting today's produce & angle…")
    fruit, angle_idx = pick_fruit_and_angle()
    angle = fruit["angles"][angle_idx]
    total_angles = len(fruit["angles"])
    print(f"   ✅ {fruit['emoji']} {fruit['name']} — Angle {angle_idx+1}/{total_angles}: {angle['theme']}")
    print(f"   Hook: {angle['hook']}")

    # Generate slide texts FIRST
    print("\n📖 Fetching Wikipedia data…")
    wiki_text = ""
    if fruit.get("wikipedia"): wiki_text = fetch_wikipedia_extract(fruit["wikipedia"])

    nutrition_line = ""
    if fruit.get("usda_fdc_id") and USDA_API_KEY:
        print("\n🥗 Fetching USDA nutrition data…")
        usda_data = fetch_usda_nutrition(fruit["usda_fdc_id"])
        nutrition_line = format_nutrition_line(fruit, usda_data)
    else:
        if not USDA_API_KEY: print("\nℹ️  No USDA_API_KEY — using curated nutrition data.")
        nutrition_line = "Per serving: packed with vitamins, minerals & antioxidants"

    print("\n✍️  Generating slide content…")
    slide_texts = generate_slides(fruit, angle, wiki_text, nutrition_line)
    num_slides = len(slide_texts)
    for i, t in enumerate(slide_texts): print(f"   Slide {i+1}: {t[:70]}…")

    # Fetch DIFFERENT photos for each slide via Pixabay
    print(f"\n📷 Fetching {num_slides} fruit photos…")
    fruit_photos = fetch_fruit_images(
        fruit.get("slide_searches", [fruit["name"].lower() + " fruit"]),
        fruit["name"],
        num_slides
    )

    print("\n🎨 Creating slide images…")
    images = []
    for i, text in enumerate(slide_texts):
        img = create_slide(text, i, num_slides, fruit, angle, slide_photo=fruit_photos[i])
        images.append(img)
        img.save(f"/tmp/slide_{i+1}.jpg", quality=95)
        print(f"   Slide {i+1}/{num_slides} ✓  → /tmp/slide_{i+1}.jpg")

    print("\n☁️  Uploading images to imgbb…")
    image_urls = []
    for i, img in enumerate(images):
        url = upload_to_imgbb(img)
        image_urls.append(url)
        print(f"   Slide {i+1} → {url}")
        time.sleep(1)

    print("\n📱 Creating Instagram carousel items…")
    children = []
    for i, url in enumerate(image_urls):
        try:
            cid = upload_carousel_item(url)
            children.append(cid)
            print(f"   Item {i+1} container ID: {cid}")
            time.sleep(4)
        except Exception as e:
            print(f"   ❌ Failed to upload carousel item {i+1}: {e}")
            sys.exit(1)

    print("\n⏳ Waiting for carousel items to process…")
    try:
        for cid in children: wait_for_container(cid)
    except Exception as e:
        print(f"   ❌ Carousel processing failed: {e}")
        sys.exit(1)

    caption = build_caption(fruit, angle)

    print("\n🎠 Creating carousel container…")
    try:
        carousel_id = create_carousel(children, caption)
        print(f"   Carousel ID: {carousel_id}")
    except Exception as e:
        print(f"   ❌ Failed to create carousel: {e}")
        sys.exit(1)

    print("\n⏳ Waiting for carousel to process…")
    try:
        wait_for_container(carousel_id)
    except Exception as e:
        print(f"   ❌ Carousel processing failed: {e}")
        sys.exit(1)

    print("\n🚀 Publishing to Instagram…")
    try:
        post_id = publish_media(carousel_id)
        print(f"\n✅ SUCCESS! Post ID: {post_id}")
    except Exception as e:
        print(f"   ❌ Failed to publish: {e}")
        sys.exit(1)

    # Single comment from main account only
    time.sleep(5)
    print("\n💬 Posting nutrition info comment…")
    try:
        comment = f"📊 {fruit['name']} Nutrition Highlights:\n{'─' * 30}\n"
        for p in angle["points"][:3]: comment += f"✓ {p}\n"
        comment += f"\n💡 {angle['tip']}"
        c = post_comment(post_id, comment)
        print(f"   ✅ Comment posted: {c}")
    except Exception as e:
        print(f"   ⚠️  Could not post comment: {e}")

    print(f"\n🍎 Posted: {fruit['emoji']} {fruit['name']} — {angle['theme']}")
    print(f"   Angle {angle_idx+1}/{total_angles} | Post ID: {post_id}")
    print("=" * 60)

if __name__ == "__main__":
    main()
