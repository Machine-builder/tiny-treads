class Timer:
    def __init__(self, timeout: float, tick_first: bool = False):
        self.timeout = timeout if not tick_first else 0
        self.timeout_max = timeout
    
    def tick(self, dt: float) -> bool:
        self.timeout -= dt
        if self.timeout <= 0:
            self.timeout = self.timeout_max
            return True
        return False