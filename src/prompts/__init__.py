"""Centralised prompt library for the Oracle AI assistant.

All prompts live here. No prompt strings exist in infrastructure or use cases.
Each prompt module exports:
    PROMPT_NAME:        str  — logical identifier
    PROMPT_VERSION:     str  — semantic version
    PROMPT_DESCRIPTION: str  — human-readable description
    TEMPLATE:           str  — the prompt template (use {variable} for injection)

The PROMPT_REGISTRY in versions.py maps logical names to module paths.
PromptEngine (infrastructure/ai/) imports from here to render prompts.
"""
