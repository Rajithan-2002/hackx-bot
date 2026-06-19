from backend.config import DOMAIN_KEYWORDS

def is_domain_valid(question: str) -> bool:
    q_lower = question.lower()
    return any(keyword in q_lower for keyword in DOMAIN_KEYWORDS)
