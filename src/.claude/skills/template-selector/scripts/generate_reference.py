import os
import json
import re

# Adjust this to point to the actual examples directory
EXAMPLES_DIR = os.path.abspath('../examples')
OUTPUT_FILE = os.path.abspath('../reference.md')

def get_description(template_dir):
    description = ""
    
    # Try package.json
    pkg_path = os.path.join(template_dir, 'package.json')
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                description = data.get('description', '')
        except:
            pass
            
    if description:
        return description
        
    # Try README.md
    readme_path = os.path.join(template_dir, 'README.md')
    if not os.path.exists(readme_path):
        readme_path = os.path.join(template_dir, 'README_zh-CN.md') # Fallback
        
    if os.path.exists(readme_path):
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find first non-header paragraph
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        description = line
                        break
        except:
            pass
            
    return description

def main():
    if not os.path.exists(EXAMPLES_DIR):
        print(f"Error: Examples directory not found at {EXAMPLES_DIR}")
        return

    templates = []
    
    for name in sorted(os.listdir(EXAMPLES_DIR)):
        path = os.path.join(EXAMPLES_DIR, name)
        if os.path.isdir(path):
            desc = get_description(path)
            templates.append({'name': name, 'description': desc or "No description available."})
            
    # Generate Markdown
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Available Templates Reference\n\n")
        f.write("This document lists all available templates in the `examples` directory and their descriptions.\n\n")
        f.write("| Template Name | Description |\n")
        f.write("| --- | --- |\n")
        for t in templates:
            # Clean description for table
            clean_desc = t['description'].replace('\n', ' ').replace('|', '\|')[:200]
            if len(t['description']) > 200:
                clean_desc += "..."
            f.write(f"| {t['name']} | {clean_desc} |\n")
            
    print(f"Generated reference at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
