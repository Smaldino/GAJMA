#!/usr/bin/env python3
"""
Wrapper script for LoRA training.
Routes to: scripts/training/train_lora.py
"""
import sys
import runpy
from pathlib import Path

if __name__ == "__main__":
    # Run the actual script from new location
    repo_root = Path(__file__).parent.absolute()
    sys.path.insert(0, str(repo_root))
    
    # Route to training subdirectory
    script_path = repo_root / "scripts" / "training" / "train_lora.py"
    
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}")
        sys.exit(1)
    
    runpy.run_path(str(script_path), run_name='__main__')
