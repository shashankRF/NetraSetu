from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ResponseProfile:

    domain: str

    sections: List[str]

    description: str