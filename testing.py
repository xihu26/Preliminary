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
- Calories:
- Protein:
- Carbs:
- Fat:
- Fibre:
- Sodium:
Assumptions
- ..."""

def main():
    food = input("food: ")
    goal = input("goal: ")
    print(analysis(food, goal))

def analysis(food, goal):
    print("Calling Gemini...")
    try:
        response = client.models.generate_content(
                model="gemini-3.1-flash-lite", contents=f"{SYSTEM_PROMPT}\n\nFood Description: {food}\nNutrition Goal: {goal}",
                config=types.GenerateContentConfig(temperature=0.4))
        
        return response.text.strip()

    except TimeoutError:
        print("Request timed out. Please try again.")
        return None
    except Exception as e:
        return f"Error ({type(e).__name__}): {e}"
    

if __name__ == "__main__":
    main()



    
