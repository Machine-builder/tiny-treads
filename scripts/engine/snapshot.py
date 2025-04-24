from typing import List, Tuple


class Snapshot:
    def __init__(self, reference_time: float, time: float, entity_states: List[Tuple]):
        self.reference_time = reference_time
        self.time = time
        self.entity_states = entity_states