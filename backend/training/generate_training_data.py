"""
generate_training_data.py

Generates .txt training files from food_db.json and exercise_db.json
for the local coach transformer model.

Usage:
    python -m training.generate_training_data
"""

import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "coach_text"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load databases
with open(BASE_DIR / "db" / "food_db.json") as f:
    FOOD_DB = json.load(f)

with open(BASE_DIR / "db" / "exercise_db.json") as f:
    EXERCISE_DB = json.load(f)


def generate_nutrition_txt():
    """Generate nutrition facts from food_db.json."""
    lines = []
    lines.append("# Indian and Global Food Nutrition Facts\n")

    for key, item in FOOD_DB.items():
        name = item.get("name", key)
        cal = item.get("calories", 0)
        prot = item.get("protein_g", 0)
        carbs = item.get("carbs_g", 0)
        fat = item.get("fats_g", 0)
        fiber = item.get("fiber_g", 0)
        portion = item.get("typical_portion_g", 100)
        is_veg = item.get("is_veg", True)
        cuisine = item.get("cuisine_region", "Global")
        aliases = item.get("common_aliases", [])

        veg_str = "vegetarian" if is_veg else "non-vegetarian"
        lines.append(f"{name}: {cal} kcal, {prot}g protein, {carbs}g carbs, {fat}g fat, {fiber}g fiber per {portion}g. {veg_str}. {cuisine} cuisine.")
        if aliases:
            lines.append(f"Also known as: {', '.join(aliases)}.")

        # Generate Q&A pairs
        lines.append(f"User: How many calories in {name.lower()}?")
        lines.append(f"Coach: {name} has {cal} calories per {portion}g serving.")
        lines.append(f"User: How much protein in {name.lower()}?")
        lines.append(f"Coach: {name} provides {prot}g of protein per {portion}g.")
        lines.append(f"User: Is {name.lower()} good for weight loss?")
        if cal < 200 and prot > 5:
            lines.append(f"Coach: Yes, {name} is a good choice for weight loss with only {cal} kcal and {prot}g protein per {portion}g.")
        elif cal > 400:
            lines.append(f"Coach: {name} is high in calories ({cal} kcal per {portion}g). Enjoy in moderation if you're cutting.")
        else:
            lines.append(f"Coach: {name} has {cal} kcal per {portion}g. It can fit into a weight loss diet with portion control.")
        lines.append("")

    with open(DATA_DIR / "nutrition.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {DATA_DIR / 'nutrition.txt'} ({len(FOOD_DB)} foods)")


def generate_exercise_txt():
    """Generate exercise facts and form tips from exercise_db.json."""
    lines = []
    lines.append("# Exercise Library with Form Tips and Calorie Burns\n")

    for key, item in EXERCISE_DB.items():
        name = item.get("name", key)
        ex_type = item.get("type", "general")
        cal_per_min = item.get("calories_per_min", 5)
        muscles = item.get("muscle_groups", [])
        equipment = item.get("equipment", "none")
        difficulty = item.get("difficulty", "beginner")

        lines.append(f"{name} ({ex_type}): Burns {cal_per_min} kcal/min. Targets: {', '.join(muscles)}. Equipment: {equipment}. Difficulty: {difficulty}.")

        # Generate workout advice
        lines.append(f"User: Tell me about {name.lower()}.")
        lines.append(f"Coach: {name} is a {ex_type} exercise that burns approximately {cal_per_min} calories per minute. It targets {', '.join(muscles)}. You need {equipment} for this exercise. It's suitable for {difficulty} level.")
        lines.append(f"User: How many calories does {name.lower()} burn in 30 minutes?")
        lines.append(f"Coach: {name} burns approximately {round(cal_per_min * 30)} calories in 30 minutes.")
        lines.append("")

    # Add general workout templates
    lines.append("## Workout Plans\n")
    lines.append("User: Give me a full body workout.")
    lines.append("Coach: Full body workout (3x/week): Barbell squat 4x8-12, Bench press 4x8-12, Bent-over row 4x8-12, Overhead press 3x10, Romanian deadlift 3x10, Plank 3x60 sec. Rest 90 sec between sets.")
    lines.append("")
    lines.append("User: Give me a home workout with no equipment.")
    lines.append("Coach: Home workout (no equipment, ~45 min): Warm-up 5 min jumping jacks. Surya Namaskar 12 rounds. Circuit 3 rounds: Push-ups 15, Squats 20, Lunges 12 each leg, Burpees 10, Plank 45 sec, Mountain climbers 30 sec. Cool-down 5 min stretching. Burns ~300-400 kcal.")
    lines.append("")
    lines.append("User: What is a good cardio routine?")
    lines.append("Coach: Cardio options (30 min each, 3-4x/week): Brisk walking ~200 kcal, Jogging ~350 kcal, Cycling ~300 kcal, Swimming ~400 kcal, HIIT 20 min ~350 kcal, Surya Namaskar 12 rounds ~250 kcal.")
    lines.append("")

    with open(DATA_DIR / "exercises.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {DATA_DIR / 'exercises.txt'} ({len(EXERCISE_DB)} exercises)")


def generate_conversations_txt():
    """Generate sample coach conversations."""
    lines = []
    lines.append("# Sample Coach Conversations\n")

    conversations = [
        ("How am I doing today?", "Here's your summary: Steps 5000/8000 (62%), Water 1500/2500ml (60%), Calories 1200/2000 kcal (60%), Protein 80/150g (53%). Tip: Drink a glass of water now and have a protein-rich snack."),
        ("How much water should I drink?", "You've had 1500ml today. You need 1000ml more to hit your 2500ml goal. Try: Chaas, Nimbu Pani, or Coconut Water — they count towards hydration!"),
        ("Give me protein advice.", "You've had 80g protein today. You need about 70g more. Top Indian sources: Paneer 18g/100g, Chicken breast 31g/100g, Dal 9g/cup, Eggs 6g each, Soy chunks 52g/100g dried."),
        ("I want to lose weight.", "For sustainable fat loss: Create a 300-500 kcal daily deficit. Eat 1.6-2.2g protein per kg body weight. Strength train 3x/week plus walk 8000 steps/day. Avoid fried foods, maida, sugary drinks. Indian choices: dal, sabzi, roti portion control, chaas, salad."),
        ("I want to build muscle.", "For muscle building: Eat 200-400 kcal above maintenance. Protein 1.6-2.2g per kg body weight. Progressive overload each week. Sleep 7-9 hours. Best Indian protein: paneer, chicken, eggs, dal, rajma, curd."),
        ("How to do a squat?", "Squat form: Feet shoulder-width, toes slightly out. Chest up, back straight, core braced. Sit back as if into a chair, knees over ankles. Go to 90 degrees or parallel, drive through heels. Start 3x12 bodyweight squats."),
        ("How to do a push-up?", "Push-up form: Hands slightly wider than shoulders. Body straight from head to heels. Lower chest until elbows at 45 degrees. Push up explosively. Beginners start on knees. Progress to 3x10 then 3x15 then full push-ups."),
        ("Tell me about paneer.", "Paneer: 265 kcal, 18g protein, 21g fat per 100g. Vegetarian. Indian cuisine. Great for muscle building. Opt for grilled paneer tikka or bhurji instead of deep-fried paneer pakora."),
        ("Tell me about dal.", "Dal: 116 kcal, 9g protein, 20g carbs per cup cooked. Vegetarian. Indian cuisine. Rich in fiber and plant protein. Pair with rice for complete amino acids. Moong dal is easiest to digest."),
        ("How many calories in biryani?", "Chicken biryani has 210 calories per 100g serving. Often high in calories from ghee and rice. Enjoy as a treat, add raita for probiotics."),
        ("Motivate me.", "Consistency beats intensity. A 10-minute walk beats a skipped workout every time. You're building a lifestyle, not chasing a quick fix. One day at a time."),
        ("What should I eat for breakfast?", "Healthy Indian breakfast options: Idli-sambar 150 kcal with good protein, Poha with peanuts 180 kcal, 2 eggs plus 1 roti 250 kcal with 18g protein, Besan chilla 120 kcal each high protein vegetarian option, Oats upma with vegetables 200 kcal high fiber."),
        ("What should I eat for lunch?", "Balanced Indian lunch: 1 roti 120 kcal plus 1 cup dal 116 kcal plus sabzi 100 kcal plus curd 60 kcal equals about 400 kcal. Rajma rice is complete protein 350 kcal 15g protein. Avoid extra rice stick to 1 cup cooked 200 kcal."),
        ("What should I eat for dinner?", "Light Indian dinner: Soup plus salad plus 1 roti. Palak paneer without cream with 1 roti 350 kcal 15g protein. Avoid heavy gravies at night choose tandoori or steamed options. Finish dinner 2-3 hours before sleep."),
        ("What about supplements?", "Supplement basics: Creatine monohydrate 5g per day safe effective for strength. Whey protein convenient way to hit protein goals. Vitamin D3 1000-2000 IU per day many Indians deficient. Omega-3 fish oil anti-inflammatory. Always consult doctor first. Whole food first supplements only fill gaps."),
        ("How is my sleep?", "Sleep is crucial for recovery. Aim 7-9 hours nightly. No screens 1 hour before bed. Keep room cool and dark. Warm haldi doodh turmeric milk aids sleep. Consistent schedule even weekends. No caffeine after 2 PM."),
        ("What is my BMI?", "Your BMI depends on weight and height. Formula: weight kg divided by height meters squared. Under 18.5 is underweight, 18.5-24.9 normal, 25-29.9 overweight, 30+ obese. BMI is a rough guide muscle mass matters more."),
        ("Can I have a cheat meal?", "Cheat meals are fine once a week. Have protein-rich meal before to reduce overeating. Choose one indulgence not everything. Go for walk after. Pizza slice 280 kcal samosa 260 kcal. Get back on track next meal."),
        ("What about steps?", "Walking burns 50-70 kcal per 1000 steps. A 20-minute brisk walk adds 2000-2500 steps. Post-dinner walk helps digestion. Park further away take stairs pace while on calls."),
    ]

    for q, a in conversations:
        lines.append(f"User: {q}")
        lines.append(f"Coach: {a}")
        lines.append("")

    with open(DATA_DIR / "conversations.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {DATA_DIR / 'conversations.txt'} ({len(conversations)} conversations)")


def generate_tips_txt():
    """Generate fitness tips and motivational content."""
    lines = []
    lines.append("# Fitness Tips, Motivation, and Recovery Advice\n")

    tips = [
        "Protein timing matters. Spread your protein intake across 4-5 meals for optimal muscle synthesis.",
        "Sleep is when your muscles grow. Aim for 7-9 hours of quality sleep every night.",
        "Hydration affects performance. Even 2 percent dehydration reduces workout capacity by 20 percent.",
        "Progressive overload is key. Increase weight, reps, or sets each week to keep building muscle.",
        "Don't skip breakfast. A protein-rich breakfast stabilizes blood sugar and reduces cravings.",
        "Compound exercises are king. Squats, deadlifts, bench press, and rows work multiple muscles at once.",
        "Rest days are not lazy days. Muscles grow during recovery, not during the workout.",
        "Track your food. What gets measured gets managed. Log every meal in TrackFit.",
        "Consistency beats perfection. A 10-minute walk every day beats a 2-hour gym session once a week.",
        "Eat the rainbow. Colorful vegetables provide different vitamins and antioxidants.",
        "Mind-muscle connection. Focus on the muscle you're working to activate more fibers.",
        "Warm up properly. 5-10 minutes of light cardio and dynamic stretches prevent injury.",
        "Cool down after workouts. Static stretching helps recovery and reduces soreness.",
        "Don't compare yourself to others. Your fitness journey is unique. Progress at your own pace.",
        "Water before meals. Drinking 500ml of water 30 minutes before meals helps with weight loss.",
        "Fiber keeps you full. Aim for 25-30g daily from vegetables, fruits, and whole grains.",
        "Lift with proper form. Bad form leads to injury. Master bodyweight before adding load.",
        "Meal prep saves time and calories. Cook dal, sabzi, and roti in bulk on weekends.",
        "Stress kills gains. High cortisol promotes fat storage and muscle breakdown. Practice relaxation.",
        "Cardio after weights. If doing both in one session, lift first when you have maximum energy.",
    ]

    for tip in tips:
        lines.append(f"Coach: {tip}")
        lines.append("")

    # Motivational quotes
    quotes = [
        "Every champion was once a beginner who refused to give up.",
        "The pain you feel today is the strength you'll have tomorrow.",
        "Your body can stand almost anything. It's your mind you have to convince.",
        "The only bad workout is the one that didn't happen.",
        "Don't wish for it, work for it.",
        "Strong is not just physical, it's mental.",
        "One day or day one. You decide.",
        "The hardest step is the first one out the door.",
        "Fall in love with the process and the results will come.",
        "You are stronger than you think.",
    ]

    for q in quotes:
        lines.append(f"User: I feel like giving up.")
        lines.append(f"Coach: {q} Keep going — you've got this!")
        lines.append("")

    with open(DATA_DIR / "tips.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {DATA_DIR / 'tips.txt'} ({len(tips)} tips, {len(quotes)} quotes)")


if __name__ == "__main__":
    generate_nutrition_txt()
    generate_exercise_txt()
    generate_conversations_txt()
    generate_tips_txt()
    print(f"\nAll training data generated in {DATA_DIR}")
