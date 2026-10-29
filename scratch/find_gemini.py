with open("retrieval/answer_generator.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "gemini" in line.lower():
        print(f"Line {i}: {line.strip()[:100]}")
