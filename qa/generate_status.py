#!/usr/bin/env python3
"""
Script to automatically update QA status after running pytest.
This script runs pytest, captures the output, and updates docs/qa/status.md.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
STATUS_FILE = ROOT_DIR / "docs" / "qa" / "status.md"
PYTEST_CMD = [sys.executable, "-m", "pytest", "-q", "--tb=short"]


def run_pytest():
    """Run pytest and capture output."""
    print(f"Running: {' '.join(PYTEST_CMD)}")
    try:
        result = subprocess.run(
            PYTEST_CMD,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Test execution timed out after 5 minutes"
    except Exception as e:
        return -1, "", f"Error running pytest: {str(e)}"


def parse_summary(stdout):
    """Extract summary line from pytest output."""
    lines = stdout.strip().split('\n')
    # Look for the summary line (usually last line with numbers)
    for line in reversed(lines):
        if 'passed' in line.lower() or 'failed' in line.lower() or 'error' in line.lower():
            return line.strip()
    return "Summary not found"


def update_status_file(returncode, stdout, stderr, summary):
    """Update docs/qa/status.md with test results."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅ PASSED" if returncode == 0 else "❌ FAILED"
    
    # Count tests
    passed = stdout.count(' PASSED') or stdout.count(' passed')
    failed = stdout.count(' FAILED') or stdout.count(' failed')
    errors = stdout.count(' ERROR') or stdout.count(' error')
    skipped = stdout.count(' SKIPPED') or stdout.count(' skipped')
    
    content = f"""# QA Status

**Última ejecución:** {timestamp}  
**Estado:** {status}  
**Comando:** `{' '.join(PYTEST_CMD)}`  
**Código de salida:** {returncode}

## Resumen

{summary}

### Conteo de tests
- ✅ Pasados: {passed}
- ❌ Fallidos: {failed}
- ⚠️  Errores: {errors}
- ⏭️  Omitidos: {skipped}

## Salida completa

<details>
<summary>Ver salida completa (click para expandir)</summary>

```
{stdout}
```

```
{stderr}
```
</details>

## Notas

Este archivo se actualiza automáticamente después de cada ejecución de `pytest` usando el script `qa/generate_status.py`.

Para ejecutar manualmente:
```bash
python qa/generate_status.py
```

O combinar ejecución y actualización:
```bash
python -m pytest -q && python qa/generate_status.py
```
"""
    
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(content, encoding='utf-8')
    print(f"✅ Status updated: {STATUS_FILE}")


def main():
    """Main entry point."""
    print("Running QA pipeline...")
    returncode, stdout, stderr = run_pytest()
    
    # Print output for immediate feedback
    if stdout:
        print("\n" + "="*80)
        print("PYTEST OUTPUT")
        print("="*80)
        print(stdout)
    if stderr:
        print("\n" + "="*80)
        print("PYTEST STDERR")
        print("="*80)
        print(stderr)
    
    summary = parse_summary(stdout)
    print(f"\n📊 Summary: {summary}")
    
    update_status_file(returncode, stdout, stderr, summary)
    
    # Exit with pytest's return code
    sys.exit(returncode)


if __name__ == "__main__":
    main()
