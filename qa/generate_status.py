"""Generate QA status markdown from pytest results."""
import subprocess
from datetime import datetime
from pathlib import Path


def run_pytest() -> str:
    try:
        result = subprocess.run(["python", "-m", "pytest", "-q"], capture_output=True, text=True, check=False)
        return result.stdout + "\n" + result.stderr
    except Exception as e:
        return f"Error running pytest: {e}"


def summarize(output: str) -> str:
    lines = output.strip().splitlines()
    summary_line = next((l for l in lines if l.strip().startswith("===") and "in" in l and ("passed" in l or "failed" in l or "errors" in l)), None)
    return summary_line or "No summary detected."


def write_status(summary: str, full_output: str):
    status_path = Path("docs/qa/status.md")
    status_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec='seconds')
    content = f"# QA Status\n\n- Timestamp: {now}\n- Summary: {summary}\n\n<details><summary>Full Output</summary>\n\n```text\n{full_output}\n```\n\n</details>\n"
    status_path.write_text(content, encoding="utf-8")


def main():
    output = run_pytest()
    summary = summarize(output)
    write_status(summary, output)


if __name__ == "__main__":
    main()


