"""Agent orchestrator — runs all 5 specialist agents in parallel."""

import asyncio
import time
from openai import AsyncOpenAI

from core.agent import BaseAgent, AgentOutput
from core.mimo_client import ClientStats, MIMO_MODEL
from core.scanner import ScanResult
from agents.architecture_agent import ArchitectureAgent
from agents.api_agent import APIAgent
from agents.examples_agent import ExamplesAgent
from agents.changelog_agent import ChangelogAgent
from agents.config_agent import ConfigAgent


class Orchestrator:
    """Runs all specialist agents concurrently and collects results."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = MIMO_MODEL,
        stats: ClientStats | None = None,
    ):
        self.client = client
        self.model = model
        self.stats = stats or ClientStats()
        self.agents: list[BaseAgent] = [
            ArchitectureAgent(client, model, self.stats),
            APIAgent(client, model, self.stats),
            ExamplesAgent(client, model, self.stats),
            ChangelogAgent(client, model, self.stats),
            ConfigAgent(client, model, self.stats),
        ]

    async def run_all(self, scan_result: ScanResult) -> dict[str, AgentOutput]:
        """Run all agents in parallel. Returns {agent_name: AgentOutput}."""
        t0 = time.time()

        tasks = [agent.run(scan_result) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: dict[str, AgentOutput] = {}
        for i, result in enumerate(results):
            agent_name = self.agents[i].config.name
            if isinstance(result, Exception):
                outputs[agent_name] = AgentOutput(
                    agent_name=agent_name,
                    sections={"Error": f"Agent failed: {result}"},
                    findings=[f"Error: {result}"],
                    confidence=0.0,
                    raw_response=str(result),
                )
            else:
                outputs[agent_name] = result

        elapsed = time.time() - t0
        print(f"Orchestrator: all {len(self.agents)} agents completed in {elapsed:.1f}s")
        return outputs
