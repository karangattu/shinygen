import json
import sys
import zipfile
from pathlib import Path

p = Path("/var/folders/76/t198ltzn1_77wm4c18b5vwh40000gp/T/shinygen_q4h4nub9/logs/2026-03-18T04-48-23-00-00_task_P5vRB9wsRx8xLySXFFdBYb.eval")

with zipfile.ZipFile(p) as z:
    print("Files in zip:")
    for n in z.namelist():
        print(f"  {n}")

    sample = json.loads(z.read("samples/shinygen/generate_epoch_1.json"))
    messages = sample.get("messages", [])
    print(f"\nTotal messages: {len(messages)}")

    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, str):
            print(f"MSG[{i}] {role} str: {content[:300]!r}")
        elif isinstance(content, list):
            for j, part in enumerate(content):
                if isinstance(part, dict):
                    ptype = part.get("type", "?")
                    if ptype == "tool_use":
                        name = part.get("name", "?")
                        inp = part.get("input", {})
                        inp_str = json.dumps(inp)[:500]
                        print(f"MSG[{i}.{j}] {role} tool_use: name={name} input={inp_str}")
                    elif ptype in ("reasoning", "thinking"):
                        print(f"MSG[{i}.{j}] {role} {ptype}: [redacted]")
                    else:
                        content_str = json.dumps(part)[:500]
                        print(f"MSG[{i}.{j}] {role} {ptype}: {content_str}")
                else:
                    print(f"MSG[{i}.{j}] {role} raw: {str(part)[:300]}")

    scores = sample.get("scores", {})
    print(f"\nScores: {json.dumps(scores, indent=2)[:500]}")

    output_val = sample.get("output", {})
    print(f"Output: {json.dumps(output_val, indent=2)[:500]}")
