with open("tests/test_pipeline.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "ambiguous" in line.lower() or "clarification" in line.lower():
        print(f"Line {i}: {line.strip()[:100]}")
