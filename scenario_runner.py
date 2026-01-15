import os
from .envelope import FlightEnvelope, EnvelopeConfig
from .dynamics import PathGenerator
from .telemetry import TelemetryEngine
from .io import TelemetryLogger
from .renderer import FlightRenderer

class ScenarioRunner:
    """
    Orchestrates scenario generation, telemetry logging, and rendering.
    """
    def __init__(self, config: EnvelopeConfig):
        self.config = config
        self.envelope = FlightEnvelope(config)
        self.telemetry_engine = TelemetryEngine(self.envelope)

    def run_scenario(self, name, path_type="mean_revert", steps=200):
        print(f"Running scenario: {name} ({path_type})")
        gen = PathGenerator(start_spot=694.0, atr=self.config.atr, steps=steps)
        
        # Generate paths
        if path_type == "mean_revert":
            spots = gen.mean_revert_pin(target=self.config.flip)
        elif path_type == "breakout":
            spots = gen.breakout(direction=1)
        elif path_type == "false_breakout":
            spots = gen.false_breakout(target_wall=self.config.call_wall)
        else:
            spots = gen.mean_revert_pin(target=self.config.flip)

        ivs = gen.generate_vol_path(start_iv=0.15)
        hvs = [0.12] * steps  # Fixed HV for simplicity
        
        # Compute telemetry
        log_data = []
        for i in range(steps):
            step_data = self.telemetry_engine.compute_step(
                spot=spots[i],
                iv=ivs[i],
                hv=hvs[i],
                timestamp=i
            )
            log_data.append(step_data)
            
        # Save log
        output_dir = "fineagle/4dflight/output"
        os.makedirs(output_dir, exist_ok=True)
        log_path = os.path.join(output_dir, f"{name}.jsonl")
        TelemetryLogger.save_log(log_path, log_data)
        print(f"Log saved to {log_path}")
        
        return log_data

    def run_monte_carlo(self, name, path_type="mean_revert", n_runs=10, steps=200):
        """Runs multiple simulations and prints summary statistics."""
        print(f"Running Monte Carlo: {name} ({n_runs} runs)")
        results = []
        for i in range(n_runs):
            log_data = self.run_scenario(f"{name}_{i}", path_type, steps)
            # Simple outcome metric: final breach state or max load
            max_load = max(step['y'] for step in log_data)
            breached = any(len(step['flags']) > 0 for step in log_data)
            results.append({"run": i, "max_load": max_load, "breached": breached})
        
        print(f"\nMonte Carlo Results for {name}:")
        breach_count = sum(1 for r in results if r['breached'])
        print(f"Breach Rate: {breach_count/n_runs:.1%}")
        print(f"Avg Max Load: {sum(r['max_load'] for r in results)/n_runs:.2f}")
        return results

def main():
    # Example usage
    config = EnvelopeConfig(
        atr=2.8,
        flip=692.5,
        put_wall=680.0,
        call_wall=700.0
    )
    
    runner = ScenarioRunner(config)
    
    # Run a few scenarios
    scenarios = [
        ("mean_revert_test", "mean_revert"),
        ("breakout_test", "breakout"),
        ("false_breakout_test", "false_breakout")
    ]
    
    output_dir = "fineagle/4dflight/output"
    for name, p_type in scenarios:
        log_data = runner.run_scenario(name, path_type=p_type)
        
        # Render the last one or all
        renderer = FlightRenderer(log_data, config)
        html_path = os.path.join(output_dir, f"{name}.html")
        html_file = renderer.render_to_html(html_path)
        print(f"Visualization saved to {html_file}")

    # Run Monte Carlo
    runner.run_monte_carlo("mc_breakout", "breakout", n_runs=5)

if __name__ == "__main__":
    main()
