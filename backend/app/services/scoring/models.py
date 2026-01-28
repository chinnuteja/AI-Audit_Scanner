from dataclasses import dataclass

@dataclass
class Check:
    """Individual audit check result."""
    id: str
    category: str
    name: str
    status: str  # pass, fail, partial, skip, info
    points_awarded: float
    points_possible: float
    evidence: str = ""
    how_to_fix: str = ""
    importance: str = "high"
    severity: str = "P2"
