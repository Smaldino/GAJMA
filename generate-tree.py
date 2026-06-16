import os
import sys

# 🔒 DEFAULTS: Automatically ignored to keep the tree clean & GitHub-friendly
IGNORED_EXTENSIONS = {
    # Video
    'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v',
    # Images
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'ico', 'webp', 'tiff',
    # Audio
    'mp3', 'wav', 'ogg', 'flac', 'aac', 'mpa',
    # Archives & Data
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
    # Documents & Spreadsheets
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'json', 'xml', 'yaml', 'yml',
    # Logs, Temp & Python Cache
    'log', 'tmp', 'bak', 'swp', 'pyc', 'pyo', 'pyd', 'egg', 'whl', 'dist-info'
}

IGNORED_FOLDERS = {
    'node_modules', '__pycache__', '.git', 'venv', '.venv', 'env',
    '.ipynb_checkpoints', 'dist', 'build', '.DS_Store', 'Thumbs.db',
    '.pytest_cache', '.mypy_cache', '.cache', '.ruff_cache', 'output', 'videos', 'images'
}

def generate_tree(root_dir, output_file="project_structure.txt"):
    def build_tree(dir_path, prefix=""):
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            return f"{prefix}└── (Access Denied)\n"

        # Filter directories & files
        dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e)) and e.lower() not in IGNORED_FOLDERS]
        files = []
        for e in entries:
            if not os.path.isfile(os.path.join(dir_path, e)):
                continue
            _, ext = os.path.splitext(e.lower())
            if ext.lstrip('.') not in IGNORED_EXTENSIONS:
                files.append(e)

        all_items = dirs + files
        total = len(all_items)
        tree_str = ""

        for i, item in enumerate(all_items):
            item_path = os.path.join(dir_path, item)
            is_last = (i == total - 1)
            connector = "└── " if is_last else "├── "
            tree_str += f"{prefix}{connector}{item}\n"

            if os.path.isdir(item_path):
                extension = "    " if is_last else "│   "
                tree_str += build_tree(item_path, prefix + extension)

        return tree_str

    root_name = os.path.basename(os.path.abspath(root_dir)) or root_dir
    full_tree = f"{root_name}/\n" + build_tree(root_dir)

    # Save to file & print to console
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_tree)
    print(f"✅ Directory tree saved to: {os.path.abspath(output_file)}")
    print("\n" + full_tree)

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output_path = sys.argv[2] if len(sys.argv) > 2 else "project_structure.txt"
    generate_tree(target_dir, output_path)