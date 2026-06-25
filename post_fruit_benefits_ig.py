"""
post_fruit_benefits_ig.py
=========================
Benefits of Fruits — Instagram Carousel Poster

Required GitHub Secrets:
  IG_USER_ID           — Instagram Business/Creator User ID (posting account)
  FB_ACCESS_TOKEN      — Facebook Page Access Token (posting account)
  IMGBB_API_KEY        — Free at imgbb.com
  PAGE_NAME            — Your IG handle WITHOUT the @
  PEXELS_API_KEY       — Free at https://www.pexels.com/api/ (for accurate fruit photos)

Optional:
  USDA_API_KEY         — Free at https://api.data.gov/signup/
  GROQ_API_KEY         — Free at console.groq.com
"""

import os, sys, json, random, requests, re, time, base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
IG_USER_ID      = os.environ["IG_USER_ID"]
FB_ACCESS_TOKEN = os.environ["FB_ACCESS_TOKEN"]
IMGBB_API_KEY   = os.environ["IMGBB_API_KEY"]
PEXELS_API_KEY  = os.environ.get("PEXELS_API_KEY", "")
USDA_API_KEY    = os.environ.get("USDA_API_KEY", "")
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
PAGE_NAME       = os.environ.get("PAGE_NAME", "fruitfacts.daily")

IMG_W, IMG_H    = 1080, 1080
IG_BASE         = "https://graph.facebook.com/v21.0"

FONT_BOLD_URL   = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
FONT_REG_URL    = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf"
FONT_BOLD_PATH  = "/tmp/Poppins-Bold.ttf"
FONT_REG_PATH   = "/tmp/Poppins-Regular.ttf"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FruitBenefitsBot/1.0)"}

# ─────────────────────────────────────────────────────────────────────────────
# FRUIT DATABASE — Each slide gets a different search query for variety
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
CATEGORIES = {
    "CITRUS":    {"rgb": (251, 146,  60), "emoji": "🍊", "label": "CITRUS"},
    "BERRY":     {"rgb": (244,  63,  94), "emoji": "🫐", "label": "BERRY"},
    "TROPICAL":  {"rgb": (245, 158,  11), "emoji": "🌴", "label": "TROPICAL"},
    "TREE":      {"rgb": (220,  38,  38), "emoji": "🌳", "label": "TREE FRUIT"},
    "MELON":     {"rgb": ( 34, 197,  94), "emoji": "🍉", "label": "MELON"},
    "SUPERFOOD": {"rgb": ( 16, 185, 129), "emoji": "✨", "label": "SUPERFOOD"},
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
    for url, path in [(FONT_BOLD_URL, FONT_BOLD_PATH), (FONT_REG_URL, FONT_REG_PATH)]:
        if not os.path.exists(path):
            print(f"  Downloading font from {url} …")
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
# FRUIT SELECTION
# ─────────────────────────────────────────────────────────────────────────────
RECENT_FILE = "/tmp/recent_fruit_angles.txt"
MAX_RECENT = 30

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
    for fruit in FRUITS:
        for angle_idx in range(len(fruit["angles"])):
            key = f"{fruit['name']}:{angle_idx}"
            if key not in recent:
                combos.append((fruit, angle_idx, key))
    if not combos:
        try: os.remove(RECENT_FILE)
        except OSError: pass
        combos = []
        for fruit in FRUITS:
            for angle_idx in range(len(fruit["angles"])):
                key = f"{fruit['name']}:{angle_idx}"
                combos.append((fruit, angle_idx, key))
    fruit, angle_idx, key = random.choice(combos)
    save_recent(key)
    return fruit, angle_idx


# ─────────────────────────────────────────────────────────────────────────────
# PEXELS API — Free, instant signup, search-based, accurate photos
# ─────────────────────────────────────────────────────────────────────────────
def search_pexels(query: str, per_page: int = 3, page: int = 1) -> list[str]:
    """
    Search Pexels for photos matching the query.
    Returns a list of image URLs (original size).
    Free API: 200 requests/hour. Signup at https://www.pexels.com/api/
    """
    if not PEXELS_API_KEY:
        return []
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": query,
                "per_page": per_page,
                "page": page,
                "orientation": "square",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        photos = data.get("photos", [])
        urls = []
        for p in photos:
            # Use 'large2x' (800px) or 'original' — both are high quality
            url = p.get("src", {}).get("large2x", "")
            if url:
                urls.append(url)
        return urls
    except Exception as e:
        print(f"    ⚠️  Pexels search failed for '{query}': {e}")
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
    
    print(f"  📷 Fetching {num_slides} fruit photos via Pexels API…")
    
    # Pre-fetch: Collect URLs from all search queries
    if PEXELS_API_KEY:
        for i, query in enumerate(slide_searches):
            print(f"    🔍 Searching Pexels for: '{query}'")
            urls = search_pexels(query, per_page=2, page=1)
            all_urls.extend(urls)
            time.sleep(0.3)  # Be nice to the API
        
        # Also search generic fruit name as backup
        if len(all_urls) < num_slides:
            print(f"    🔍 Backup search: '{fruit_name} fruit fresh'")
            backup_urls = search_pexels(f"{fruit_name} fruit fresh", per_page=5)
            all_urls.extend(backup_urls)
    else:
        print("    ⚠️  No PEXELS_API_KEY set — photos will use dark background!")
        print("    → Get free key at: https://www.pexels.com/api/")
    
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

    # Category pill
    pill_font = get_font(24)
    pill_text = f"{fruit['emoji']}  {cat_label}"
    pill_bbox = draw.textbbox((0, 0), pill_text, font=pill_font)
    pw = pill_bbox[2] + 36
    ph = 44
    px, py = 48, 32
    draw_rounded_rect(draw, px, py, px + pw, py + ph, 10, accent)
    draw.text((px + 18, py + 9), pill_text, font=pill_font, fill=C_WHITE)

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
        e_font = get_font(100)
        draw.text((IMG_W // 2, 240), fruit["emoji"], font=e_font, anchor="mm")

        font, lines = fit_text(draw, text.upper(), 62, IMG_W - 120, 4)
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
        theme_text = f"🎯 {angle['theme']}"
        draw.text((IMG_W // 2, IMG_H - 160), theme_text, font=theme_font, anchor="mm", fill=accent)

        prompt_font = get_font(24, bold=False)
        draw.text((IMG_W // 2, IMG_H - 130), "Swipe to learn why →", font=prompt_font, anchor="mm", fill=C_GRAY)

    # ══════════════ CTA SLIDE ══════════════
    elif is_cta:
        e_font = get_font(120)
        draw.text((IMG_W // 2, 240), fruit["emoji"], font=e_font, anchor="mm")

        draw.text((IMG_W // 2, 450), "EAT MORE FRUIT", font=get_font(34, bold=False), anchor="mm", fill=C_GRAY)
        draw.text((IMG_W // 2, 530), f"Follow @{PAGE_NAME}", font=get_font(58), anchor="mm", fill=C_WHITE)
        draw.text((IMG_W // 2, 620), "For daily fruit health facts! 🍎🍊🫐", font=get_font(28, bold=False), anchor="mm", fill=C_GRAY)
        draw.rectangle([(160, 690), (IMG_W - 160, 697)], fill=accent)
        draw.text((IMG_W // 2, 740), "Save this post for your next grocery run! 🛒", font=get_font(24, bold=False), anchor="mm", fill=C_GRAY)

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
        font, lines = fit_text(draw, text, 54, max_w, 8)
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
    tags = f"#{name.lower()} #fruitbenefits #healthyeating #nutrition #fruitfacts #eatmorefruit #healthylifestyle #{theme.lower()} #wellness #healthtips #fruitlover #vitamins #antioxidants #cleaneating #plantbased"
    return f"{emoji} {name} — {angle['hook']}\n\n👉 Swipe to discover what this fruit does for your {theme.lower()}!\n\n💾 Save this for your next grocery trip!\n\n{tags}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print(f"  🍎 Benefits of Fruits — Instagram Carousel Bot")
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

    print("\n🎲 Selecting today's fruit & angle…")
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

    # Fetch DIFFERENT photos for each slide via Pexels
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
