import threading
from typing import Callable
import time
from functools import wraps

class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.lock = threading.Lock()
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapped(*args, **kwargs):
            with self.lock:
                now = time.monotonic()
                # Remove timestamps that are outside the current rate-limiting period
                self.calls = [call for call in self.calls if call > now - self.period]
                if len(self.calls) >= self.max_calls:
                    wait_time = self.calls[0] + self.period - now
                    time.sleep(max(0, wait_time))
                self.calls.append(time.monotonic())
            return func(*args, **kwargs)
        return wrapped
