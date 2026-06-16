import os
import sys
import runpy

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, repo_root)
    runpy.run_module('src.manga.cli', run_name='__main__')
