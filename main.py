from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard.py"

if not DASHBOARD.exists():
    raise FileNotFoundError(f"Dashboard not found: {DASHBOARD}")

print("RetailPulse - Retail Analytics and Decision Support")
print("Starting the Streamlit dashboard...")
print("Press Ctrl+C in this terminal to stop it.")

subprocess.run(
    [sys.executable, "-m", "streamlit", "run", str(DASHBOARD)],
    cwd=ROOT,
    check=False,
)
