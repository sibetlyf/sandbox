import os
import sys
import shutil
import argparse
import difflib

# Adjust this to point to the actual examples directory
# Assuming script is in <root>/skills/template-selector/scripts/
# And examples are in <root>/examples/
EXAMPLES_DIR = os.path.abspath('../examples')

def find_template(keyword):
    if not os.path.exists(EXAMPLES_DIR):
        print(f"Error: Examples directory not found at {EXAMPLES_DIR}")
        return None

    candidates = [d for d in os.listdir(EXAMPLES_DIR) if os.path.isdir(os.path.join(EXAMPLES_DIR, d))]
    
    # Exact match first
    if keyword in candidates:
        return keyword
    
    # Substring match
    matches = [c for c in candidates if keyword.lower() in c.lower()]
    if matches:
        # Return shortest match as it's likely the specific one (e.g. "react" -> "react-template" over "react-native-...")
        # sticking to simple logic for now.
        return matches[0]
        
    # Fuzzy match
    close_matches = difflib.get_close_matches(keyword, candidates, n=1, cutoff=0.6)
    if close_matches:
        return close_matches[0]
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Select and copy a template.")
    parser.add_argument("keyword", help="Keyword to search for a template")
    parser.add_argument("destination", help="Target destination path")
    
    args = parser.parse_args()
    
    template_name = find_template(args.keyword)
    
    if not template_name:
        print(f"No suitable template found for keyword: {args.keyword}")
        sys.exit(1)
        
    src_path = os.path.join(EXAMPLES_DIR, template_name)
    dest_path = os.path.abspath(args.destination)
    
    print(f"Found template: {template_name}")
    print(f"Source: {src_path}")
    print(f"Destination: {dest_path}")
    
    if os.path.exists(dest_path):
        print(f"Error: Destination '{dest_path}' already exists.")
        sys.exit(1)
        
    try:
        shutil.copytree(src_path, dest_path)
        print(f"Successfully copied template '{template_name}' to '{dest_path}'")
    except Exception as e:
        print(f"Error copying template: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
