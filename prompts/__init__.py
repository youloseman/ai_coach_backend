"""
Modular prompt system for AI Triathlon Coach.
"""

from .builder import build_coach_prompt
from .base_prompt import BASE_SYSTEM_PROMPT

__all__ = ['build_coach_prompt', 'BASE_SYSTEM_PROMPT']

