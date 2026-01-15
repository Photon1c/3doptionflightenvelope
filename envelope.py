import numpy as np
from dataclasses import dataclass

@dataclass
class EnvelopeConfig:
    atr: float
    flip: float
    put_wall: float
    call_wall: float
    risk_proxy_base: float = 1.0  # e.g., default IV/HV ratio

class FlightEnvelope:
    """
    Geometry and boundary evaluation for the option flight envelope.
    Coordinates:
    X = Structural Airspeed = |spot - flip| / ATR
    Y = Load Factor = risk proxy (e.g., IV/HV)
    """
    def __init__(self, config: EnvelopeConfig):
        self.config = config

    def evaluate_state(self, spot: float, iv: float, hv: float):
        """
        Calculates coordinates and regime based on spot price and volatility.
        """
        atr = self.config.atr
        flip = self.config.flip
        
        # X: Structural Airspeed
        airspeed = abs(spot - flip) / (atr if atr > 0 else 1e-9)
        
        # Y: Load Factor (defaulting to IV/HV)
        load_factor = iv / (hv if hv > 0 else 1e-9)
        
        # Z: Normalized Wall Proximity (0 at wall, 1 at flip)
        # We'll use this for the 3rd dimension as requested
        if spot >= flip:
            wall_dist = abs(self.config.call_wall - spot)
            max_dist = abs(self.config.call_wall - flip)
        else:
            wall_dist = abs(self.config.put_wall - spot)
            max_dist = abs(self.config.put_wall - flip)
            
        wall_proximity = wall_dist / (max_dist if max_dist > 0 else 1e-9)
        
        return {
            "x": airspeed,
            "y": load_factor,
            "z": wall_proximity,
            "is_breached": spot > self.config.call_wall or spot < self.config.put_wall,
            "is_overspeed": airspeed > 3.0,  # Example threshold
            "is_stall": airspeed < 0.2,      # Example threshold
        }

    def get_regime(self, x: float, y: float):
        """
        Classifies the flight regime based on X (airspeed) and Y (load).
        """
        if y > 2.5 or x > 4.5:
            return "RUPTURE"
        if x < 0.3:
            return "TAXI"
        if y > 1.5 or x > 2.5:
            return "MANEUVER"
        return "CRUISE"
