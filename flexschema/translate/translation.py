import dataclasses
from dataclasses import field as FIELD

@dataclasses.dataclass
class Translation:
    output: str
    extension: str
    deps: set[str] = FIELD(default_factory=set)
    head: list[str] = FIELD(default_factory=list)
