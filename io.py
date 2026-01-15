import json

class TelemetryLogger:
    """
    Handles JSONL save/load for telemetry data.
    """
    @staticmethod
    def save_log(filepath, data):
        with open(filepath, 'w') as f:
            for entry in data:
                f.write(json.dumps(entry) + '\n')

    @staticmethod
    def load_log(filepath):
        data = []
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data
