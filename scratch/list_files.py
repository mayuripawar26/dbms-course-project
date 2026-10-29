import os

for root, dirs, files in os.walk("."):
    if ".git" in root or "__pycache__" in root:
        continue
    rel_root = os.path.relpath(root, ".")
    print(f"Directory: {rel_root}")
    for f in files:
        if not f.endswith(".pyc"):
            print(f"  {f}")
