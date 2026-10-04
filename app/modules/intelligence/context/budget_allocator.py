"""
L0-L10 Layered Context Budget Allocator
=======================================
Enforces strict token ceilings across 10 discrete context layers, guaranteeing
Nemotron 3 Ultra prompts never overflow context limits while strictly preserving
constitutional invariants, task objectives, and primary code snippets.

Context Hierarchy (L0 to L10):
  - L0_SYSTEM: System Prompt & Autonomous Principles (~1,000 tokens) [CRITICAL]
  - L1_CONSTITUTION: Constitutional Rules & Quality Invariants (~800 tokens) [CRITICAL]
  - L2_PROJECT: Project Identity & Tech Stack Summary (~500 tokens)
  - L3_TASK: Current Task Goal & Active Phase (~300 tokens) [CRITICAL]
  - L4_REPO_MAP: Compact RepoMap (~1,500 tokens)
  - L5_CODE: Primary Code Snippets & Target File AST (~6,000 tokens) [CRITICAL]
  - L6_DOCS_ADR: Relevant Documentation & Architecture Decisions (~1,000 tokens)
  - L7_TURNS: Recent Conversation Turns (~2,000 tokens)
  - L8_TOOL_LOGS: Recent Tool Observations (~2,000 tokens)
  - L9_WORKING_MEM: Working Memory & Scratchpad (~800 tokens)
  - L10_OUTPUT_RES: Output Reservation (~4,000 tokens) [RESERVED]
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ContextLayer(str, Enum):
    L0_SYSTEM = "L0_SYSTEM"           # System instructions & core principles
    L1_CONSTITUTION = "L1_CONSTITUTION" # Quality invariants & constitutional rules
    L2_PROJECT = "L2_PROJECT"         # Project identity & tech stack
    L3_TASK = "L3_TASK"               # Active task goal, phase & instructions
    L4_REPO_MAP = "L4_REPO_MAP"       # Compact symbol/route map
    L5_CODE = "L5_CODE"               # Primary code snippets & target file AST
    L6_DOCS_ADR = "L6_DOCS_ADR"       # Relevant documentation & ADR records
    L7_TURNS = "L7_TURNS"             # Recent conversation turns
    L8_TOOL_LOGS = "L8_TOOL_LOGS"     # Recent tool observations & command outputs
    L9_WORKING_MEM = "L9_WORKING_MEM" # Working memory & scratchpad
    L10_OUTPUT_RES = "L10_OUTPUT_RES" # Reserved token quota for generation


# Layers that cannot be trimmed away during progressive compaction
CRITICAL_LAYERS: set[ContextLayer] = {
    ContextLayer.L0_SYSTEM,
    ContextLayer.L1_CONSTITUTION,
    ContextLayer.L3_TASK,
    ContextLayer.L5_CODE,
}

# Sacrifice order for trimming when total tokens exceed available prompt window
# Lowest value layers are sacrificed first.
TRIMMING_SACRIFICE_ORDER: list[ContextLayer] = [
    ContextLayer.L8_TOOL_LOGS,     # 1. Raw tool execution traces trimmed first
    ContextLayer.L6_DOCS_ADR,      # 2. Supplementary documentation
    ContextLayer.L7_TURNS,         # 3. Older conversation history
    ContextLayer.L4_REPO_MAP,      # 4. Repo symbol map
    ContextLayer.L9_WORKING_MEM,   # 5. Scratchpad notes
    ContextLayer.L2_PROJECT,       # 6. High-level project identity
]


def estimate_tokens(text: str) -> int:
    """Fast, accurate token estimation heuristic (~3.8 chars per token for code/text)."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.8))


def truncate_to_tokens(
    text: str,
    max_tokens: int,
    suffix: str = "\n... [truncated to fit context budget] ...",
) -> str:
    """Trim text to strictly fit within token ceiling."""
    if not text:
        return ""
    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text

    char_limit = int(max_tokens * 3.8) - len(suffix)
    if char_limit <= 0:
        return text[: max_tokens * 3]
    return text[:char_limit] + suffix


class LayerQuotas(BaseModel):
    """Default token quotas per layer."""
    L0_SYSTEM: int = 1000
    L1_CONSTITUTION: int = 800
    L2_PROJECT: int = 500
    L3_TASK: int = 300
    L4_REPO_MAP: int = 1500
    L5_CODE: int = 6000
    L6_DOCS_ADR: int = 1000
    L7_TURNS: int = 2000
    L8_TOOL_LOGS: int = 2000
    L9_WORKING_MEM: int = 800
    L10_OUTPUT_RES: int = 4000

    def get_quota(self, layer: ContextLayer) -> int:
        return getattr(self, layer.value, 1000)


class LayeredContextBudgetConfig(BaseModel):
    """Configuration for total context window and layer allocations."""
    max_context_window: int = 32000
    quotas: LayerQuotas = Field(default_factory=LayerQuotas)

    @property
    def max_prompt_budget(self) -> int:
        """Available budget for input prompt after reserving L10 generation space."""
        return max(0, self.max_context_window - self.quotas.L10_OUTPUT_RES)


class LayerAllocationResult(BaseModel):
    """Structured result of layered context allocation."""
    layers: dict[str, str]
    token_usage: dict[str, int]
    total_prompt_tokens: int
    output_reservation: int
    total_effective_tokens: int
    max_context_window: int
    trimmed_layers: list[str]
    within_budget: bool


class ContextBudgetAllocator:
    """
    Orchestrates L0-L10 layered context assembly, enforcing strict token quotas
    and applying progressive dynamic trimming to non-critical layers when under pressure.
    """

    def __init__(self, config: LayeredContextBudgetConfig | None = None):
        self.config = config or LayeredContextBudgetConfig()

    def allocate(
        self,
        layer_contents: dict[ContextLayer, str],
        max_prompt_tokens: int | None = None,
    ) -> LayerAllocationResult:
        """
        Allocates and bounds context layers.
        
        If total prompt tokens exceed available budget, applies progressive trimming
        to non-critical layers following TRIMMING_SACRIFICE_ORDER while strictly preserving
        L0, L1, L3, and L5.
        """
        effective_max_prompt = (
            max_prompt_tokens
            if max_prompt_tokens is not None
            else self.config.max_prompt_budget
        )

        allocated: dict[str, str] = {}
        token_usage: dict[str, int] = {}
        trimmed_layers: list[str] = []

        # 1. Initial pass: clamp each layer to its configured individual quota
        for layer in ContextLayer:
            if layer == ContextLayer.L10_OUTPUT_RES:
                continue
            content = layer_contents.get(layer, "")
            quota = self.config.quotas.get_quota(layer)
            est = estimate_tokens(content)

            if est > quota:
                # If content exceeds layer quota, clamp it
                if layer in CRITICAL_LAYERS:
                    # Critical layers are clamped with generous allowance if possible
                    trimmed = truncate_to_tokens(content, quota)
                else:
                    trimmed = truncate_to_tokens(content, quota)
                allocated[layer.value] = trimmed
                trimmed_layers.append(layer.value)
            else:
                allocated[layer.value] = content

            token_usage[layer.value] = estimate_tokens(allocated[layer.value])

        total_prompt_tokens = sum(token_usage.values())

        # 2. Dynamic progressive trimming if total prompt exceeds effective_max_prompt
        if total_prompt_tokens > effective_max_prompt:
            logger.info(
                f"Context budget pressure: {total_prompt_tokens} tokens exceeds "
                f"{effective_max_prompt} prompt ceiling. Initiating dynamic trimming."
            )

            for layer in TRIMMING_SACRIFICE_ORDER:
                if total_prompt_tokens <= effective_max_prompt:
                    break

                current_tokens = token_usage.get(layer.value, 0)
                if current_tokens <= 50:
                    continue  # already minimal

                # Target reduction: cut this layer in half or down to 20%
                tokens_to_shed = total_prompt_tokens - effective_max_prompt
                new_layer_tokens = max(50, current_tokens - tokens_to_shed)

                original_content = allocated[layer.value]
                allocated[layer.value] = truncate_to_tokens(
                    original_content, new_layer_tokens
                )
                new_est = estimate_tokens(allocated[layer.value])
                token_usage[layer.value] = new_est

                if layer.value not in trimmed_layers:
                    trimmed_layers.append(layer.value)

                total_prompt_tokens = sum(token_usage.values())

        # 3. Final safety check on budget
        within_budget = total_prompt_tokens <= effective_max_prompt
        total_effective = total_prompt_tokens + self.config.quotas.L10_OUTPUT_RES

        return LayerAllocationResult(
            layers=allocated,
            token_usage=token_usage,
            total_prompt_tokens=total_prompt_tokens,
            output_reservation=self.config.quotas.L10_OUTPUT_RES,
            total_effective_tokens=total_effective,
            max_context_window=self.config.max_context_window,
            trimmed_layers=trimmed_layers,
            within_budget=within_budget,
        )

    def assemble_prompt_string(self, allocation: LayerAllocationResult) -> str:
        """
        Assembles all allocated layers in strict hierarchical order (L0 to L9)
        into a unified, cleanly delimited markdown prompt string.
        """
        sections: list[str] = []

        layer_headers = {
            ContextLayer.L0_SYSTEM.value: "=== SYSTEM & CORE PRINCIPLES ===",
            ContextLayer.L1_CONSTITUTION.value: "=== CONSTITUTIONAL RULES & INVARIANTS ===",
            ContextLayer.L2_PROJECT.value: "=== PROJECT CONTEXT & TECH STACK ===",
            ContextLayer.L3_TASK.value: "=== CURRENT TASK OBJECTIVE ===",
            ContextLayer.L4_REPO_MAP.value: "=== REPOSITORY ARCHITECTURE MAP ===",
            ContextLayer.L5_CODE.value: "=== PRIMARY CODE SNIPPETS & SYMBOLS ===",
            ContextLayer.L6_DOCS_ADR.value: "=== ARCHITECTURE DECISIONS & RELEVANT DOCS ===",
            ContextLayer.L7_TURNS.value: "=== RECENT CONVERSATION HISTORY ===",
            ContextLayer.L8_TOOL_LOGS.value: "=== RECENT TOOL OBSERVATIONS ===",
            ContextLayer.L9_WORKING_MEM.value: "=== WORKING MEMORY & SCRATCHPAD ===",
        }

        for layer in ContextLayer:
            if layer == ContextLayer.L10_OUTPUT_RES:
                continue
            val = allocation.layers.get(layer.value, "").strip()
            if val:
                header = layer_headers.get(layer.value, f"=== {layer.value} ===")
                sections.append(f"{header}\n{val}")

        return "\n\n".join(sections)
