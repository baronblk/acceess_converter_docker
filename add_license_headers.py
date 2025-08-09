#!/usr/bin/env python3
"""
Script to add BSL 1.1 license headers to all source files
"""

import os
import glob
from pathlib import Path

# License header templates
PYTHON_HEADER = '''"""
Access Database Converter v2.0
Copyright © 2025 GCNG Software - Rene Süß

Lizenziert unter der Business Source License 1.1
Nicht-kommerzielle Nutzung gestattet.
Kommerzielle Nutzung nur mit schriftlicher Genehmigung.

Diese Software wird automatisch am 09. August 2030 unter MIT-Lizenz freigegeben.

Vollständige Lizenz: siehe LICENSE-Datei im Projektverzeichnis
Kontakt für kommerzielle Lizenz: baronblk@googlemail.com
"""

'''

HASH_COMMENT_HEADER = '''# Access Database Converter v2.0
# Copyright © 2025 GCNG Software - Rene Süß
#
# Lizenziert unter der Business Source License 1.1
# Nicht-kommerzielle Nutzung gestattet.
# Kommerzielle Nutzung nur mit schriftlicher Genehmigung.
#
# Diese Software wird automatisch am 09. August 2030 unter MIT-Lizenz freigegeben.
#
# Vollständige Lizenz: siehe LICENSE-Datei im Projektverzeichnis
# Kontakt für kommerzielle Lizenz: baronblk@googlemail.com

'''

def has_license_header(content):
    """Check if file already has a license header"""
    return "Copyright © 2025 GCNG Software - Rene Süß" in content

def add_header_to_python_file(file_path):
    """Add license header to Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if has_license_header(content):
        print(f"Skipping {file_path} - already has license header")
        return
    
    # Add header after any shebang line
    lines = content.splitlines(True)
    insert_pos = 0
    
    # Check for shebang
    if lines and lines[0].startswith('#!'):
        insert_pos = 1
    
    new_content = ''.join(lines[:insert_pos]) + PYTHON_HEADER + ''.join(lines[insert_pos:])
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Added license header to {file_path}")

def add_header_to_hash_comment_file(file_path):
    """Add license header to files using # comments"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if has_license_header(content):
        print(f"Skipping {file_path} - already has license header")
        return
    
    new_content = HASH_COMMENT_HEADER + content
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Added license header to {file_path}")

def main():
    """Main function to process all files"""
    project_root = Path(__file__).parent
    
    # Process Python files
    for py_file in project_root.rglob("*.py"):
        if "venv" not in str(py_file) and "__pycache__" not in str(py_file):
            add_header_to_python_file(py_file)
    
    # Process YAML files
    for yaml_file in project_root.rglob("*.yml"):
        add_header_to_hash_comment_file(yaml_file)
    
    for yaml_file in project_root.rglob("*.yaml"):
        add_header_to_hash_comment_file(yaml_file)
    
    # Process shell scripts
    for sh_file in project_root.rglob("*.sh"):
        add_header_to_hash_comment_file(sh_file)
    
    print("License headers added successfully!")

if __name__ == "__main__":
    main()
