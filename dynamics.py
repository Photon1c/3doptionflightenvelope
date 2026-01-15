import numpy as np
import random

class PathGenerator:
    """
    Generates synthetic price and volatility paths for scenarios.
    """
    def __init__(self, start_spot, atr, steps=200):
        self.start_spot = start_spot
        self.atr = atr
        self.steps = steps

    def mean_revert_pin(self, target, intensity=0.1, noise=0.2):
        """Pin around a target (like flip)."""
        path = [self.start_spot]
        spot = self.start_spot
        for _ in range(self.steps - 1):
            drift = (target - spot) * intensity
            spot += drift + random.normalvariate(0, self.atr * noise)
            path.append(spot)
        return path

    def breakout(self, direction=1, speed=0.5, noise=0.1):
        """Breakout with follow-through."""
        path = [self.start_spot]
        spot = self.start_spot
        for _ in range(self.steps - 1):
            spot += (direction * self.atr * speed) + random.normalvariate(0, self.atr * noise)
            path.append(spot)
        return path

    def false_breakout(self, target_wall, breach_depth=1.5, recovery=0.8):
        """Breach a wall and then snap back."""
        path = []
        spot = self.start_spot
        half = self.steps // 2
        
        # Move towards wall
        for _ in range(half):
            drift = (target_wall - spot) * 0.1
            spot += drift + random.normalvariate(0, self.atr * 0.1)
            path.append(spot)
            
        # Overshoot
        overshoot_target = target_wall + (target_wall - self.start_spot) * breach_depth
        for _ in range(self.steps - half):
            drift = (self.start_spot - spot) * recovery
            spot += drift + random.normalvariate(0, self.atr * 0.2)
            path.append(spot)
            
        return path

    def generate_vol_path(self, start_iv, target_iv=None, shock_at=None):
        """Generates an IV path, potentially with a shock."""
        path = [start_iv]
        iv = start_iv
        target = target_iv or start_iv
        for i in range(self.steps - 1):
            if shock_at and i == shock_at:
                iv *= 1.5
            drift = (target - iv) * 0.05
            iv += drift + random.normalvariate(0, start_iv * 0.05)
            path.append(max(0.01, iv))
        return path
