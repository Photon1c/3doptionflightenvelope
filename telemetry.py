from .envelope import FlightEnvelope, EnvelopeConfig

class TelemetryEngine:
    """
    Computes per-step telemetry and derived flags.
    """
    def __init__(self, envelope: FlightEnvelope):
        self.envelope = envelope

    def compute_step(self, spot, iv, hv, timestamp):
        state = self.envelope.evaluate_state(spot, iv, hv)
        regime = self.envelope.get_regime(state['x'], state['y'])
        
        flags = []
        if state['is_breached']: flags.append("BREACH")
        if state['is_overspeed']: flags.append("OVERSPEED")
        if state['is_stall']: flags.append("STALL")
        
        return {
            "timestamp": timestamp,
            "spot": round(spot, 2),
            "iv": round(iv, 4),
            "hv": round(hv, 4),
            "x": round(state['x'], 3),
            "y": round(state['y'], 3),
            "z": round(state['z'], 3),
            "regime": regime,
            "flags": flags
        }
