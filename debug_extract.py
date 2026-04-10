"""Quick diagnostic: run one generation and dump the eval log message structure."""
import json
import sys
import tempfile
import zipfile
from pathlib import Path

# Activate the local package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shinygen.config import resolve_model, resolve_framework, FRAMEWORK_COMPOSE, FRAMEWORKS
from shinygen.generate import build_generation_task, stage_docker_context
from shinygen.skills import load_default_skills
from shinygen.prompts import build_system_prompt

def main():
    prompt = "Create a simple counter app with a button and a number display"
    model = "claude-sonnet"
    framework_key = "shiny_python"

    agent, model_id = resolve_model(model)
    fw = FRAMEWORKS[framework_key]
    
    skills = load_default_skills(framework_key)

    docker_dir = stage_docker_context(framework_key)
    
    task = build_generation_task(
        user_prompt=prompt,
        agent=agent,
        framework_key=framework_key,
        docker_context_dir=docker_dir,
        skills=skills,
    )

    from inspect_ai import eval as inspect_eval
    logs = inspect_eval(task, model=model_id, log_dir=str(docker_dir / "logs"))
    
    if not logs:
        print("No logs!")
        return
    
    log = logs[0]
    log_path = getattr(log, "location", None)
    print(f"\nLog path: {log_path}")
    
    if log_path:
        p = Path(log_path)
        with zipfile.ZipFile(p) as z:
            sample_files = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
            print(f"Sample files: {sample_files}")
            
            for sf in sample_files:
                sample = json.loads(z.read(sf))
                messages = sample.get("messages", [])
                print(f"\nTotal messages: {len(messages)}")
                
                # Dump all message roles and content types
                for i, msg in enumerate(messages):
                    role = msg.get("role", "?")
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        preview = content[:200]
                        print(f"  [{i}] {role} (str): {preview!r}")
                    elif isinstance(content, list):
                        for j, part in enumerate(content):
                            if isinstance(part, dict):
                                ptype = part.get("type", "?")
                                if ptype == "text":
                                    text = part.get("text", "")[:200]
                                    print(f"  [{i}.{j}] {role}/{ptype}: {text!r}")
                                elif ptype == "tool_use":
                                    name = part.get("name", "?")
                                    inp = part.get("input", {})
                                    # Check if this is a file write
                                    inp_keys = list(inp.keys()) if isinstance(inp, dict) else "str"
                                    inp_preview = str(inp)[:300]
                                    print(f"  [{i}.{j}] {role}/tool_use: {name}({inp_keys}) → {inp_preview}")
                                elif ptype == "tool_result":
                                    tool_id = part.get("tool_use_id", "?")
                                    result = str(part.get("content", ""))[:200]
                                    print(f"  [{i}.{j}] {role}/tool_result[{tool_id}]: {result}")
                                else:
                                    print(f"  [{i}.{j}] {role}/{ptype}: {str(part)[:200]}")
                            else:
                                print(f"  [{i}.{j}] {role}/raw: {str(part)[:200]}")
                    else:
                        print(f"  [{i}] {role} (other): {str(content)[:200]}")

                # Also try extraction
                from shinygen.extract import find_app_code_in_messages, extract_from_log
                code = find_app_code_in_messages(messages, "app.py")
                print(f"\nextract result: {'found ' + str(len(code)) + ' chars' if code else 'NONE'}")
                
                code_map = extract_from_log(p)
                print(f"extract_from_log result: {code_map.keys() if code_map else 'EMPTY'}")


if __name__ == "__main__":
    main()
