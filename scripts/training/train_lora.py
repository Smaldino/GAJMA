import os
import sys
import runpy

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, repo_root)
    sys.path.insert(0, os.path.join(repo_root, 'src', 'video_gen', 'ToonCrafter'))
    runpy.run_module('src.video_gen.ToonCrafter.main.trainer', run_name='__main__')
