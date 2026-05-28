"""Prompt registry — maps logical prompt names to versioned module paths.

To add a new prompt:
    1. Create the module in the appropriate subdirectory
    2. Register it here with a logical name key

To switch a prompt to a new version (e.g. for A/B testing):
    Update the module path here. The old version stays as a file for audit.

Logical names are used by PromptEngine to load the correct template.
"""

PROMPT_REGISTRY: dict[str, str] = {
    "oracle_system":      "prompts.system.oracle_system_v1",
    "oracle_quick":       "prompts.system.oracle_quick_v1",
    "chart_analysis":     "prompts.analysis.chart_analysis_v1",
    "ohlcv_context":      "prompts.analysis.ohlcv_context_v1",
    "reflection":         "prompts.trade.reflection_v1",
    "morning_briefing":   "prompts.briefing.morning_briefing_v1",
    "confidence_scoring": "prompts.scoring.confidence_scoring_v1",
}
