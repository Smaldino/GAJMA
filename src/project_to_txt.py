import os

def consolidate_project(root_dir, output_file):
    # Updated extensions to include
    valid_extensions = (
        '.jsonl', '.md', '.ps1', '.pt', 
        '.py', '.sh', '.txt', '.xml', '.yaml'
    )
    
    # Folders to ignore
    ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(root_dir):
            # Modify dirs in-place to skip ignored folders
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if file.endswith(valid_extensions):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Note: Some files like .gif, .jpg, or .pt (PyTorch models) 
                        # are binary. Reading them as text will cause errors.
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            
                            outfile.write("="*80 + "\n")
                            outfile.write(f"FILE: {file_path}\n")
                            outfile.write("="*80 + "\n\n")
                            outfile.write(content)
                            outfile.write("\n\n")
                    except Exception as e:
                        print(f"Could not read {file_path}: {e}")

if __name__ == "__main__":
    # '.' means the current directory
    consolidate_project('.', 'project_dump.txt')
    print("Project consolidated into project_dump.txt")