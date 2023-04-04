from dataclasses import dataclass


@dataclass
class MessageSerializer:
    id: str | int
    content: str
    tags: str
    meta: dict
    level_tag: str
