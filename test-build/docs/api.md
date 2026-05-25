# PromptForge API Reference

## api/main.py

### `lifespan(app: FastAPI)`
Initialize database on application startup.

**Parameters:**
- `app` (FastAPI): The FastAPI application instance

**Returns:** AsyncContextManager for application lifespan

**Example:**
```python
app = FastAPI(lifespan=lifespan)
```

---

### `index()`
Serve the frontend HTML page.

**Parameters:** None

**Returns:** HTMLResponse with the main application interface

**Example:**
```python
# Accessed via GET /
response = await index()
```

---

### `health()`
Health check endpoint to verify service availability.

**Parameters:** None

**Returns:** HealthResponse with status information

**Example:**
```python
# Accessed via GET /api/health
response = await health()
# {"status": "ok"}
```

---

### `optimize(req: OptimizeRequest)`
Run the full optimization pipeline on a prompt.

**Parameters:**
- `req` (OptimizeRequest): Request containing original prompt and task description

**Returns:** OptimizeResponse with optimized prompt, scorecard, and agent results

**Example:**
```python
request = OptimizeRequest(
    original_prompt="Write a summary",
    task_description="Summarize articles"
)
response = await optimize(request)
```

---

### `history(limit: int = 10)`
Get optimization history with most recent runs first.

**Parameters:**
- `limit` (int): Maximum number of history items to return (default: 10)

**Returns:** HistoryResponse containing list of recent optimizations

**Example:**
```python
# GET /api/history?limit=5
response = await history(limit=5)
```

---

### `get_one(optimization_id: int)`
Get full details for a specific optimization run.

**Parameters:**
- `optimization_id` (int): ID of the optimization to retrieve

**Returns:** Complete optimization record with all agent results

**Example:**
```python
# GET /api/optimization/42
details = await get_one(optimization_id=42)
```

---

## api/models.py

### `OptimizeRequest`
Request payload for prompt optimization.

**Fields:**
- `original_prompt` (str): The prompt to optimize
- `task_description` (str): Description of what the prompt should accomplish

**Example:**
```python
request = OptimizeRequest(
    original_prompt="Summarize this text",
    task_description="Create concise summaries"
)
```

---

### `AgentResultResponse`
Single specialist agent's analysis result.

**Fields:**
- `agent_name` (str): Name of the specialist agent
- `findings` (str): Analysis findings from the agent
- `recommendations` (str): Suggested improvements

**Example:**
```python
result = AgentResultResponse(
    agent_name="ClarityAuditor",
    findings="Vague instructions detected",
    recommendations="Add specific examples"
)
```

---

### `OptimizeResponse`
Complete response from optimization pipeline.

**Fields:**
- `optimized_prompt` (str): The improved prompt
- `scorecard` (dict): Quality metrics and scores
- `eval_score` (int): Overall evaluation score
- `agent_results` (list[AgentResultResponse]): Results from all agents
- `diff_summary` (str): Summary of changes made
- `token_usage` (int): Total tokens consumed

**Example:**
```python
response = OptimizeResponse(
    optimized_prompt="Improved version...",
    scorecard={"clarity": 9, "completeness": 8},
    eval_score=85,
    agent_results=[...],
    diff_summary="Added examples and constraints",
    token_usage=1500
)
```

---

### `HistoryItem`
Summary of a single optimization run in history list.

**Fields:**
- `id` (int): Unique optimization ID
- `original_prompt` (str): Original prompt text
- `task_description` (str): Task description
- `eval_score` (int): Evaluation score
- `created_at` (str): Timestamp of creation

**Example:**
```python
item = HistoryItem(
    id=42,
    original_prompt="Write code",
    task_description="Generate Python functions",
    eval_score=78,
    created_at="2026-05-25T21:30:00Z"
)
```

---

### `HistoryResponse`
List of recent optimization runs.

**Fields:**
- `items` (list[HistoryItem]): List of history items

**Example:**
```python
response = HistoryResponse(items=[item1, item2, item3])
```

---

### `HealthResponse`
Service health status.

**Fields:**
- `status` (str): Health status indicator

**Example:**
```python
response = HealthResponse(status="ok")
```

---

## eval/scorer.py

### `EvalScore`
Evaluation result comparing original and optimized prompts.

**Fields:**
- `score` (int): Numeric quality score (0-100)
- `reasoning` (str): Explanation of the score
- `improvements` (list[str]): List of identified improvements
- `concerns` (list[str]): List of potential issues

**Example:**
```python
score = EvalScore(
    score=85,
    reasoning="Significantly clearer instructions",
    improvements=["Added examples", "Defined constraints"],
    concerns=["May be too verbose"]
)
```

---

### `EvalScorer`
Evaluates prompt quality using MiMo as an LLM judge.

**Example:**
```python
scorer = EvalScorer(client=mimo_client, model="mimo-large")
result = await scorer.evaluate(
    original_prompt="Write code",
    optimized_prompt="Write Python code with docstrings",
    task_description="Generate functions"
)
```

---

### `EvalScorer.__init__(client: AsyncOpenAI, model: str)`
Initialize the evaluator with MiMo client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier to use for evaluation

**Returns:** EvalScorer instance

**Example:**
```python
scorer = EvalScorer(client=get_mimo_client(), model="mimo-large")
```

---

### `EvalScorer.evaluate(original_prompt: str, optimized_prompt: str, task_description: str)`
Compare original vs optimized prompt using LLM judge.

**Parameters:**
- `original_prompt` (str): The original prompt text
- `optimized_prompt` (str): The optimized prompt text
- `task_description` (str): Description of the prompt's purpose

**Returns:** EvalScore with comparative analysis

**Example:**
```python
score = await scorer.evaluate(
    original_prompt="Summarize",
    optimized_prompt="Summarize in 3 bullet points",
    task_description="Create article summaries"
)
```

---

## db/database.py

### `get_db()`
Get an async database connection.

**Parameters:** None

**Returns:** aiosqlite.Connection instance

**Example:**
```python
async with await get_db() as db:
    cursor = await db.execute("SELECT * FROM optimizations")
```

---

### `init_db()`
Initialize database tables and schema.

**Parameters:** None

**Returns:** None

**Example:**
```python
await init_db()
```

---

### `save_optimization(...)`
Save a complete optimization run to the database.

**Parameters:**
- `original_prompt` (str): Original prompt text
- `task_description` (str): Task description
- `optimized_prompt` (str): Optimized prompt text
- `scorecard` (dict): Quality metrics
- `eval_score` (int): Overall evaluation score
- `agent_results` (list[dict]): Results from all agents
- `diff_summary` (str): Summary of changes
- `token_usage` (int): Total tokens used

**Returns:** int - ID of the saved optimization

**Example:**
```python
opt_id = await save_optimization(
    original_prompt="Write code",
    task_description="Generate functions",
    optimized_prompt="Write Python functions with docstrings",
    scorecard={"clarity": 9},
    eval_score=85,
    agent_results=[...],
    diff_summary="Added specificity",
    token_usage=1200
)
```

---

### `get_history(limit: int)`
Get recent optimization history.

**Parameters:**
- `limit` (int): Maximum number of records to return

**Returns:** list[dict] of optimization summaries

**Example:**
```python
recent = await get_history(limit=10)
```

---

### `get_optimization(optimization_id: int)`
Get a single optimization by ID.

**Parameters:**
- `optimization_id` (int): ID of the optimization

**Returns:** dict with full optimization details, or None if not found

**Example:**
```python
opt = await get_optimization(optimization_id=42)
```

---

## core/mimo_client.py

### `get_mimo_client()`
Return an AsyncOpenAI client pointing at MiMo-compatible endpoint.

**Parameters:** None

**Returns:** AsyncOpenAI client configured for MiMo

**Example:**
```python
client = get_mimo_client()
response = await client.chat.completions.create(...)
```

---

### `mimo_chat(client: AsyncOpenAI, model: str, messages: list[dict], temperature: float, max_tokens: int)`
Call MiMo model with SSE+reasoning_content fallback.

**Parameters:**
- `client` (AsyncOpenAI): MiMo-compatible client
- `model` (str): Model identifier
- `messages` (list[dict]): Chat messages
- `temperature` (float): Sampling temperature
- `max_tokens` (int): Maximum response tokens

**Returns:** str - The model's response text

**Example:**
```python
response = await mimo_chat(
    client=get_mimo_client(),
    model="mimo-large",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.7,
    max_tokens=500
)
```

---

## core/synthesizer.py

### `SynthesisResult`
Final output from the synthesis compiler.

**Fields:**
- `optimized_prompt` (str): The final optimized prompt
- `scorecard` (dict): Quality metrics
- `diff_summary` (str): Summary of changes made
- `token_usage` (int): Total tokens consumed

**Example:**
```python
result = SynthesisResult(
    optimized_prompt="Improved prompt...",
    scorecard={"clarity": 9, "completeness": 8},
    diff_summary="Added examples and constraints",
    token_usage=1500
)
```

---

### `Synthesizer`
Merges agent outputs into final optimized prompt.

**Example:**
```python
synth = Synthesizer(client=get_mimo_client(), model="mimo-large")
result = await synth.synthesize(
    original_prompt="Write code",
    task_description="Generate functions",
    agent_results=[agent1_result, agent2_result]
)
```

---

### `Synthesizer.__init__(client: AsyncOpenAI, model: str)`
Initialize synthesizer with MiMo client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** Synthesizer instance

**Example:**
```python
synth = Synthesizer(client=get_mimo_client(), model="mimo-large")
```

---

### `Synthesizer.synthesize(original_prompt: str, task_description: str, agent_results: list[AgentResult])`
Produce final optimized prompt from all agent analyses.

**Parameters:**
- `original_prompt` (str): Original prompt text
- `task_description` (str): Task description
- `agent_results` (list[AgentResult]): Results from all specialist agents

**Returns:** SynthesisResult with optimized prompt and metrics

**Example:**
```python
result = await synth.synthesize(
    original_prompt="Summarize text",
    task_description="Create summaries",
    agent_results=[clarity_result, tone_result]
)
```

---

## core/agent.py

### `AgentResult`
Output from a single specialist agent.

**Fields:**
- `agent_name` (str): Name of the agent
- `findings` (str): Analysis findings
- `recommendations` (str): Suggested improvements
- `token_usage` (int): Tokens consumed by this agent

**Example:**
```python
result = AgentResult(
    agent_name="ClarityAuditor",
    findings="Vague instructions",
    recommendations="Add specific examples",
    token_usage=250
)
```

---

### `AgentConfig`
Configuration for an agent.

**Fields:**
- `name` (str): Agent name
- `system_prompt` (str): System instructions for the agent

**Example:**
```python
config = AgentConfig(
    name="ClarityAuditor",
    system_prompt="You analyze prompt clarity..."
)
```

---

### `BaseAgent`
Base class for all specialist agents.

**Example:**
```python
class MyAgent(BaseAgent):
    def __init__(self, client, model):
        super().__init__(
            config=AgentConfig(name="MyAgent", system_prompt="..."),
            client=client,
            model=model
        )
```

---

### `BaseAgent.__init__(config: AgentConfig, client: AsyncOpenAI, model: str)`
Initialize agent with configuration, client, and model.

**Parameters:**
- `config` (AgentConfig): Agent configuration
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** BaseAgent instance

**Example:**
```python
agent = BaseAgent(
    config=AgentConfig(name="Test", system_prompt="..."),
    client=get_mimo_client(),
    model="mimo-large"
)
```

---

### `BaseAgent.build_user_prompt(prompt: str, task_description: str)`
Build the user-facing prompt for this agent.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** str - Formatted user prompt

**Example:**
```python
user_prompt = agent.build_user_prompt(
    prompt="Write code",
    task_description="Generate functions"
)
```

---

### `BaseAgent.run(prompt: str, task_description: str)`
Execute the agent and return structured results.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** AgentResult with findings and recommendations

**Example:**
```python
result = await agent.run(
    prompt="Summarize text",
    task_description="Create summaries"
)
```

---

## core/orchestrator.py

### `AgentOrchestrator`
Runs all specialist agents concurrently and collects results.

**Example:**
```python
orchestrator = AgentOrchestrator(
    client=get_mimo_client(),
    model="mimo-large"
)
results = await orchestrator.run_all(
    prompt="Write code",
    task_description="Generate functions"
)
```

---

### `AgentOrchestrator.__init__(client: AsyncOpenAI, model: str)`
Initialize orchestrator with MiMo client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** AgentOrchestrator instance

**Example:**
```python
orchestrator = AgentOrchestrator(
    client=get_mimo_client(),
    model="mimo-large"
)
```

---

### `AgentOrchestrator.run_all(prompt: str, task_description: str)`
Run all agents in parallel and return results.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** list[AgentResult] from all specialist agents

**Example:**
```python
results = await orchestrator.run_all(
    prompt="Summarize articles",
    task_description="Create concise summaries"
)
```

---

## agents/regression_writer.py

### `RegressionWriter`
Identifies regression risks and generates safety checks.

**Example:**
```python
agent = RegressionWriter(
    client=get_mimo_client(),
    model="mimo-large"
)
result = await agent.run(
    prompt="Deploy to production",
    task_description="Deployment automation"
)
```

---

### `RegressionWriter.__init__(client: AsyncOpenAI, model: str)`
Initialize regression writer agent with client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** RegressionWriter instance

**Example:**
```python
agent = RegressionWriter(get_mimo_client(), "mimo-large")
```

---

### `RegressionWriter.build_user_prompt(prompt: str, task_description: str)`
Build the user prompt for regression analysis.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** str - Formatted user prompt

**Example:**
```python
user_prompt = agent.build_user_prompt(
    prompt="Deploy code",
    task_description="Automated deployment"
)
```

---

## agents/clarity_auditor.py

### `ClarityAuditor`
Finds ambiguous language, vague instructions, and missing context.

**Example:**
```python
agent = ClarityAuditor(
    client=get_mimo_client(),
    model="mimo-large"
)
result = await agent.run(
    prompt="Do the thing",
    task_description="Task automation"
)
```

---

### `ClarityAuditor.__init__(client: AsyncOpenAI, model: str)`
Initialize clarity auditor agent with client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** ClarityAuditor instance

**Example:**
```python
agent = ClarityAuditor(get_mimo_client(), "mimo-large")
```

---

### `ClarityAuditor.build_user_prompt(prompt: str, task_description: str)`
Build the user prompt for clarity analysis.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** str - Formatted user prompt

**Example:**
```python
user_prompt = agent.build_user_prompt(
    prompt="Write something",
    task_description="Content generation"
)
```

---

## agents/edge_case_probe.py

### `EdgeCaseProbe`
Finds edge cases, boundary conditions, and potential failure modes.

**Example:**
```python
agent = EdgeCaseProbe(
    client=get_mimo_client(),
    model="mimo-large"
)
result = await agent.run(
    prompt="Process user input",
    task_description="Input validation"
)
```

---

### `EdgeCaseProbe.__init__(client: AsyncOpenAI, model: str)`
Initialize edge case probe agent with client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** EdgeCaseProbe instance

**Example:**
```python
agent = EdgeCaseProbe(get_mimo_client(), "mimo-large")
```

---

### `EdgeCaseProbe.build_user_prompt(prompt: str, task_description: str)`
Build the user prompt for edge case analysis.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** str - Formatted user prompt

**Example:**
```python
user_prompt = agent.build_user_prompt(
    prompt="Parse JSON",
    task_description="Data parsing"
)
```

---

## agents/output_contract.py

### `OutputContract`
Analyzes output format requirements and schema enforcement.

**Example:**
```python
agent = OutputContract(
    client=get_mimo_client(),
    model="mimo-large"
)
result = await agent.run(
    prompt="Return JSON",
    task_description="API response formatting"
)
```

---

### `OutputContract.__init__(client: AsyncOpenAI, model: str)`
Initialize output contract agent with client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** OutputContract instance

**Example:**
```python
agent = OutputContract(get_mimo_client(), "mimo-large")
```

---

### `OutputContract.build_user_prompt(prompt: str, task_description: str)`
Build the user prompt for output format analysis.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** str - Formatted user prompt

**Example:**
```python
user_prompt = agent.build_user_prompt(
    prompt="Generate report",
    task_description="Report generation"
)
```

---

## agents/tone_matcher.py

### `ToneMatcher`
Analyzes tone, voice, and audience alignment.

**Example:**
```python
agent = ToneMatcher(
    client=get_mimo_client(),
    model="mimo-large"
)
result = await agent.run(
    prompt="Write email",
    task_description="Customer communication"
)
```

---

### `ToneMatcher.__init__(client: AsyncOpenAI, model: str)`
Initialize tone matcher agent with client and model.

**Parameters:**
- `client` (AsyncOpenAI): OpenAI-compatible async client
- `model` (str): Model identifier

**Returns:** ToneMatcher instance

**Example:**
```python
agent = ToneMatcher(get_mimo_client(), "mimo-large")
```

---

### `ToneMatcher.build_user_prompt(prompt: str, task_description: str)`
Build the user prompt for tone analysis.

**Parameters:**
- `prompt` (str): The prompt to analyze
- `task_description` (str): Description of the task

**Returns:** str - Formatted user prompt

**Example:**
```python
user_prompt = agent.build_user_prompt(
    prompt="Draft message",
    task_description="Internal communication"
)