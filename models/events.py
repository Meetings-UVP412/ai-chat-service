from typing import Dict, Any


class ChunkProcessedEvent:
    def __init__(self, uuid: str, ord_num: int, is_last: bool, duration: int, success: bool):
        self.uuid = uuid
        self.ord = ord_num
        self.isLast = is_last
        self.duration = duration
        self.success = success

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            uuid=str(data.get('uuid') or data.get('UUID') or ''),
            ord_num=int(data.get('ord', data.get('Ord', 0))),
            is_last=bool(data.get('isLast', data.get('islast', False))),
            duration=int(data.get('duration', data.get('Duration', 0))),
            success=bool(data.get('success', False))
        )
