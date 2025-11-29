import os
import sys

# --- Configuration ---
# The name of the output file that will contain the project dump.
OUTPUT_FILENAME = "project_dump.txt"

# A set of directory names to completely ignore.
# Add any other folders you want to exclude.
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "node_modules",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "__pycache__"
}

# A set of specific file names to ignore.
EXCLUDED_FILES = {
    OUTPUT_FILENAME,  # Exclude the output file itself.
    ".gitignore",
    ".DS_Store",
    "getallcodereport.py",
}

# A set of file extensions that are considered "text" and should be included.
# Add any other extensions you use (e.g., .cfg, .ini).
INCLUDED_EXTENSIONS = {
    ".py",
    ".html",
    ".js",
    ".css",
    ".json",
    ".sh",
    ".md",
    ".yml",
    ".yaml",
    ".cfg",
    ".ini",
}

def generate_file_tree(start_path):
    """Generates a visual file tree structure as a list of strings."""
    tree_lines = []
    print("🌳 Generating file tree...")

    for root, dirs, files in os.walk(start_path, topdown=True):
        # Filter out excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        
        # Add the directory to the tree
        if level > 0: # Don't show the root folder itself, it's implied
             tree_lines.append(f"{indent[:-4]}├── {os.path.basename(root)}/")
        
        sub_indent = ' ' * 4 * (level + 1)
        
        # Filter and sort files before processing
        filtered_files = sorted([
            f for f in files if f not in EXCLUDED_FILES and
            any(f.endswith(ext) for ext in INCLUDED_EXTENSIONS)
        ])

        for i, filename in enumerate(filtered_files):
            connector = "└──" if i == len(filtered_files) - 1 and not dirs else "├──"
            tree_lines.append(f"{sub_indent}{connector} {filename}")

    return tree_lines


def dump_file_contents(start_path, output_file):
    """Dumps the contents of all relevant files into the output file."""
    print("📄 Dumping file contents...")
    
    for root, dirs, files in os.walk(start_path, topdown=True):
        # Filter directories to avoid walking into them
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        # Sort files for consistent order
        sorted_files = sorted(files)

        for filename in sorted_files:
            if filename in EXCLUDED_FILES:
                continue
            
            # Check if the file extension is in our include list
            if not any(filename.endswith(ext) for ext in INCLUDED_EXTENSIONS):
                continue

            filepath = os.path.join(root, filename)
            # Use forward slashes for cross-platform compatibility in the output
            relative_filepath = filepath.replace(os.path.sep, '/')

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as infile:
                    content = infile.read()
                
                output_file.write(f"--- File: {relative_filepath} ---\n\n")
                output_file.write(content)
                output_file.write(f"\n\n{'='*80}\n\n")
                
                print(f"  -> Included: {relative_filepath}")

            except Exception as e:
                print(f"  -> ⚠️  Could not read file {filepath}: {e}")


def main():
    """Main function to orchestrate the project dump."""
    project_root = "."
    print("🚀 Starting project dump process...")
    
    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as outfile:
            # Phase 1: Generate and write the file tree
            outfile.write("="*28 + " PROJECT STRUCTURE " + "="*29 + "\n\n")
            tree = generate_file_tree(project_root)
            outfile.write(f"{project_root}/\n")
            for line in tree:
                outfile.write(line + "\n")
            outfile.write("\n" + "="*80 + "\n\n")

            # Phase 2: Dump the contents of all files
            outfile.write("="*31 + " FILE CONTENTS " + "="*32 + "\n\n")
            dump_file_contents(project_root, outfile)

        print(f"\n🎉 Success! Project dump created at: '{os.path.abspath(OUTPUT_FILENAME)}'")
        print("You can now copy the contents of this file.")

    except IOError as e:
        print(f"\n❌ FATAL ERROR: Could not write to output file '{OUTPUT_FILENAME}'.\n   Reason: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()