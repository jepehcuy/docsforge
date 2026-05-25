# Getting Started

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/promptforge.git
cd promptforge

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENAI_API_KEY="your-api-key-here"

# Initialize the database
python -m db.database

# Start the API server
uvicorn api.main:app --reload
```

## Basic Prompt Optimization

Submit a prompt for optimization and receive an improved version with evaluation metrics.

```python
import httpx
import asyncio

async def optimize_prompt():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/optimize",
            json={
                "original_prompt": "Write a story about a cat",
                "task_description": "Generate creative fiction"
            }
        )
        result = response.json()
        print(f"Optimized prompt: {result['optimized_prompt']}")
        print(f"Evaluation score: {result['eval_score']}/100")

asyncio.run(optimize_prompt())
```

## Reviewing Optimization History

Retrieve past optimizations to compare approaches and track improvements over time.

```python
import httpx
import asyncio

async def view_history():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/history?limit=10")
        history = response.json()
        
        for item in history["items"]:
            print(f"\nID: {item['id']}")
            print(f"Original: {item['original_prompt'][:50]}...")
            print(f"Score: {item['eval_score']}/100")
            print(f"Created: {item['created_at']}")

asyncio.run(view_history())
```

## Detailed Optimization Analysis

Fetch a specific optimization to examine agent results, diff summaries, and token usage.

```python
import httpx
import asyncio

async def analyze_optimization(optimization_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/optimization/{optimization_id}")
        opt = response.json()
        
        print(f"Task: {opt['task_description']}")
        print(f"\nOriginal:\n{opt['original_prompt']}")
        print(f"\nOptimized:\n{opt['optimized_prompt']}")
        print(f"\nDiff Summary:\n{opt['diff_summary']}")
        print(f"\nToken Usage: {opt['token_usage']}")
        
        print("\nAgent Results:")
        for agent in opt["agent_results"]:
            print(f"  - {agent['agent_name']}: {agent['suggestion'][:80]}...")

asyncio.run(analyze_optimization(1))
```

## Custom Evaluation with EvalScorer

Programmatically evaluate prompt quality using the built-in scoring system.

```python
import asyncio
from openai import AsyncOpenAI
from eval.scorer import EvalScorer

async def evaluate_prompts():
    client = AsyncOpenAI(api_key="your-api-key")
    scorer = EvalScorer(client=client, model="gpt-4")
    
    original = "Tell me about dogs"
    optimized = "Provide a comprehensive overview of domestic dogs (Canis familiaris), including their evolutionary history, behavioral characteristics, common breeds, and their role in human society."
    task = "Educational content generation"
    
    score = await scorer.evaluate(
        original_prompt=original,
        optimized_prompt=optimized,
        task_description=task
    )
    
    print(f"Overall Score: {score.overall_score}/100")
    print(f"Clarity: {score.clarity_score}/100")
    print(f"Specificity: {score.specificity_score}/100")
    print(f"Effectiveness: {score.effectiveness_score}/100")
    print(f"\nReasoning: {score.reasoning}")

asyncio.run(evaluate_prompts())