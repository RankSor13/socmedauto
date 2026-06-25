"""
post_fruit_benefits_ig.py
=========================
Benefits of Fruits — Instagram Carousel Poster

Required GitHub Secrets:
  IG_USER_ID           — Instagram Business/Creator User ID (posting account)
  FB_ACCESS_TOKEN      — Facebook Page Access Token (posting account)
  IMGBB_API_KEY        — Free at imgbb.com
  PAGE_NAME            — Your IG handle WITHOUT the @
  PIXABAY_API_KEY      — Free instant signup at https://pixabay.com/api/docs/

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
        "slide_searches": ["strawberry fruit red", "strawberry sliced", "bowl fresh strawberries", "strawberry field", "strawberry smoothie"],
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
        "slide_searches": ["blueberry fruit", "handful blueberries", "bowl fresh blueberries", "blueberry smoothie", "blueberry bush"],
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
        "slide_searches": ["banana fruit yellow", "banana peeled", "banana smoothie healthy", "banana tree bunch", "banana slices"],
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
        "slide_searches": ["mango fruit ripe", "mango fruit sliced", "mango smoothie tropical", "mango tree", "ripe mango"],
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
        "slide_searches": ["pineapple fruit whole", "pineapple sliced", "pineapple juice fresh", "pineapple tropical", "pineapple pieces"],
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
        "slide_searches": ["red apple fruit", "apple fruit sliced", "apple tree orchard", "apple juice fresh", "basket red apples"],
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
        "slide_searches": ["avocado fruit green", "avocado halves pit", "avocado toast", "ripe avocado", "avocado sliced"],
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
        "slide_searches": ["kiwi fruit", "kiwi fruit sliced green", "kiwi halves", "kiwi smoothie", "golden kiwi"],
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
        "slide_searches": ["watermelon fruit", "watermelon slices red", "watermelon juice", "watermelon cut", "watermelon fresh"],
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
        "slide_searches": ["purple grapes bunch", "grapes vineyard", "bowl fresh grapes", "red grapes close", "grapes fruit"],
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
        "slide_searches": ["pomegranate fruit red", "pomegranate seeds arils", "pomegranate open half", "pomegranate juice", "pomegranate close up"],
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
        "slide_searches": ["cherry fruit red", "bowl fresh cherries", "cherry tree branch", "cherry close up", "cherry smoothie"],
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
        "slide_searches": ["papaya fruit", "papaya sliced half", "papaya pieces fresh", "papaya tree tropical", "papaya smoothie"],
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
        "slide_searches": ["dragon fruit pink", "dragon fruit sliced", "dragon fruit pieces", "dragon fruit smoothie", "red dragon fruit"],
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
        "slide_searches": ["guava fruit green", "guava fruit pink", "guava pieces fresh", "guava tree", "guava juice"],
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
# PIXABAY API — Free instant signup, search-based, accurate fruit photos
# ─────────────────────────────────────────────────────────────────────────────
def search_pixabay(query: str, per_page: int = 3) -> list[str]:
    """
    Search Pixabay for photos matching the query.
    Free API with instant signup: https://pixabay.com/api/docs/
    Returns a list of image URLs (webformat ~640px, then large ~1280px).
    5000 requests/hour — way more than we need.
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
                "min_width": 640,
                "editors_choice": "true",  # Better quality results
            },
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", [])
        urls = []
        for hit in hits:
            # webformatURL is ~640px, largeImageURL is ~1280px, fullHDURL is 1920px
            url = hit.get("largeImageURL") or hit.get("webformatURL") or hit.get("previewURL", "")
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
    Fetch a different image for each slide using Pixabay search API.
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
            time.sleep(0.3)
        
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
        if i == num_slides - 1:
            if last_successful:
                photos[i] = last_successful.copy()
                print(f"    ✅ Slide {i+1} reusing photo (CTA slide)")
            else:
                photos[i] = None
                print(f"    ℹ️  Slide {i+1} dark background (CTA)")
            continue
        
        photo = None
        url_idx = i
        while url_idx < len(all_urls) and photo is None:
            photo = fetch_single_image(all_urls[url_idx])
            if photo is None:
                url_idx += 1
        
        if photo:
            photos[i] = photo
            last_successful = photo
            print(f"    ✅ Slide {i+1} photo loaded!")
        elif last_successful:
            photos[i] = last_successful.copy()
            print(f"    ℹ️  Slide {i+1} reusing previous photo")
        else:
            photos[i] = None
            print(f"    ⚠️  Slide {i+1} no photo available")
    
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

def extract_fun_facts_from_wiki(wiki_text: str, fruit_name: str) -> list[str]:
    """Extract interesting fun facts from Wikipedia text."""
    if not wiki_text:
        return []
    sentences = wiki_text.replace("\n", " ").split(". ")
    facts = [s.strip() + "." for s in sentences if len(s.strip()) > 40]
    return facts[:5]
