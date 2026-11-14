from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
load_dotenv()

#Configuration
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
SYSTEM_PROMPT = """You are a Thai nutrition assistant.
Your task is to analyse a food item and optimise it for the user's nutrition goal.
Rules: Be concise.Use bullet points only.If the food is a dish, estimate the main ingredients. Nutritional values are estimates.Suggest a maximum of 3 substitutions.
Output exactly in this format:
Food Identification
- Name:
- Confidence:
Estimated Nutrition
- Calories:
- Protein:
- Carbs:
- Fat:
- Fibre:
- Sodium:
Suggested Substitutions
- Current → Alternative | Benefit
- Current → Alternative | Benefit
- Current → Alternative | Benefit
Estimated Nutrition Improvements
- Calories: Current → New 
- Protein: Current → New 
- Carbs: Current → New 
- Fat: Current → New 
- Fibre: Current → New 
- Sodium: Current → New 
Assumptions
- ..."""

def main():
    food = input("food: ")
    goal = input("goal: ")
    print(analysis(food, goal))

def analysis(food="", goal="", image_bytes=None, mime_type="image/jpeg"):
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Food Description: {food or 'Identify the food from the attached image.'}\n"
        f"Nutrition Goal: {goal}"
    )

    contents = [prompt]

    if image_bytes:
        contents.append(
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        )

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.4),
        )
        return response.text.strip() if response.text else "I couldn't identify the food."
    except Exception as e:
        return f"Error ({type(e).__name__}): {e}"
    

if __name__ == "__main__":
    main()



    
