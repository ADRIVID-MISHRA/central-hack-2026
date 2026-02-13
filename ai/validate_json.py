
import json

try:
    with open('model.features.json', 'r') as f:
        data = json.load(f)
    print("JSON is valid.")
except json.JSONDecodeError as e:
    print(f"JSON Error: {e}")
    print(f"Error at line {e.lineno}, column {e.colno}, char {e.pos}")
    # Read raw content to see context
    with open('model.features.json', 'r') as f:
        content = f.read()
    start = max(0, e.pos - 50)
    end = min(len(content), e.pos + 50)
    print(f"Context: ...{content[start:end]}...")
