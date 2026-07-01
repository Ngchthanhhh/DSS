"""
llm_router.py — PLACEHOLDER (skeleton only)

Ban goc chua logic goi OpenRouter API voi co che fallback giua nhieu model
(model priority list, retry, error handling...). Da luoc bo vi ly do bao mat
chat xam. Lien he chu repo neu can ban day du.
"""

import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def generate_with_fallback(prompt, temperature=0.1, max_tokens=150):
    """
    [PLACEHOLDER] Goi LLM (qua OpenRouter) voi co che fallback nhieu model.

    Ban day du: thu lan luot cac model theo priority, xu ly loi/timeout,
    tra ve text response.
    """
    raise NotImplementedError("Xem ban day du o source goc cua chu repo.")
