# QA Execution Guide

## Environment
- Ensure Python 3.10+.
- From the repository root, tests import `backend`, `backtest`, etc. The following settings make this work:
  - `conftest.py` adds the repo root to `sys.path` automatically.
  - `pytest.ini` sets `pythonpath=.` and test discovery paths.

## Commands

- Run tests:
```bash
python -m pytest -q
```

- Generate QA status (writes to `docs/qa/status.md` with timestamp and full output):
```bash
python qa/generate_status.py
```

- Combined:
```bash
python -m pytest -q && python qa/generate_status.py
```

## Notes
- If you need to customize environment variables (e.g., `ACCOUNT_CAPITAL`, `TIMEFRAMES`), export them before running tests.
- The status file includes the exact summary line from pytest and the full output collapsed.
