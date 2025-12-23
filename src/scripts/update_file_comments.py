#!/usr/bin/env python3
# scripts/update_file_comments.py
"""
Script to update or add file path comments at the beginning of Python files.
The comment will be in the format: # relative/path/to/file.py
"""
import os
import re
from pathlib import Path

def should_skip_file(filepath):
    """Check if the file should be skipped."""
    # Skip files in venv and .git directories
    skip_dirs = {'venv', '.git', '__pycache__', '.pytest_cache'}
    if any(part in skip_dirs for part in filepath.parts):
        return True
    # Skip non-Python files
    if filepath.suffix != '.py':
        return True
    # Skip __init__.py files
    if filepath.name == '__init__.py':
        return True
    # Skip files in site-packages
    if 'site-packages' in filepath.parts:
        return True
    return False

def update_file_comment(filepath, project_root):
    """Update or add file path comment to the beginning of the file."""
    try:
        # Get relative path from project root
        rel_path = filepath.relative_to(project_root).as_posix()
        comment = f"# {rel_path}\n"
        
        # Read the file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines(keepends=True)
        if not lines:  # Empty file
            return
            
        # Check for shebang
        shebang = None
        if lines[0].startswith('#!'):
            shebang = lines[0]
            lines = lines[1:]
        
        # Check for encoding declaration
        encoding = None
        if lines and re.match(r'^#.*coding[:=]\s*([-\w.]+)', lines[0]):
            encoding = lines[0]
            lines = lines[1:]
        
        # Check for existing path comment
        path_comment = None
        if lines and lines[0].startswith('#'):
            first_line = lines[0].strip()
            if any(sep in first_line for sep in ('/', '\\')):
                path_comment = lines[0]
                lines = lines[1:]
        
        # Reconstruct content with updated comment
        new_content = []
        if shebang:
            new_content.append(shebang)
        if encoding:
            new_content.append(encoding)
        new_content.append(comment)
        if path_comment and path_comment.strip() != comment.strip():
            print(f"Updating comment in {rel_path}")
        elif not path_comment:
            print(f"Adding comment to {rel_path}")
        
        new_content.extend(lines)
        
        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_content)
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")
    
    # Process all Python files in the project
    for py_file in project_root.glob('**/*.py'):
        if not should_skip_file(py_file):
            update_file_comment(py_file, project_root)
    
    print("\nAll Python files have been updated with correct path comments.")

if __name__ == "__main__":
    main()
