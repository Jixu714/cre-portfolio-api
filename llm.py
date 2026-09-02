import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client_ai = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
cache = {}

def clear_cache():
    cache.clear()

def ask_about_portfolio(question, data):
    key = question.lower().strip()

    if key in cache:
        return cache[key]
    
    lines = []
    for row in data:
        lines.append(f"{row['name']}: {row['square_ft']} sqft total, {row['leased_sqft']} leased, {row['occupancy_pct']}% occupied\n")
    context = "".join(lines)

    prompt = f"""You are a commercial real estate analyst. Answer in 2-3 sentences, plain text, no markdown formatting or headers.

    Portfolio data: 
    {context}
    
    Question: {question}"""

    message = client_ai.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]

    )
    
    for block in message.content:
        if block.type == "text":
            cache[key] = block.text
            return block.text
