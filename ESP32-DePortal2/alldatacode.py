import os
import sys

# This script requires the 'tqdm' library for a progress bar.
# You can install it by running: pip install tqdm
try:
    from tqdm import tqdm
except ImportError:
    print("Error: The 'tqdm' library is not installed.", file=sys.stderr)
    print("Please install it first using the following command:", file=sys.stderr)
    print("pip install tqdm", file=sys.stderr)
    sys.exit(1)


# --- (1) Configuration Area - Adjust settings here ---

# The name of the final output file.
OUTPUT_FILENAME = "project_dump.txt"

# A set of directory names to completely ignore.
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
    ".pio",  # Added as per your request
    # Add any other folders you want to exclude here, e.g., "logs", "temp"
}

# A set of specific file names to ignore.
EXCLUDED_FILES = {
    OUTPUT_FILENAME,      # Exclude the output file itself.
    ".gitignore",
    ".DS_Store",
    "alldatacode.py",
    # This script's filename will be added automatically.
}

# A set of file extensions and full filenames that should be included.
# Any file not matching these will be ignored.
INCLUDED_EXTENSIONS = {
    ".py", ".h", ".cpp",  # .h and .cpp added as per your request
    ".html", ".js", ".css",
    ".json", ".sh", ".txt", ".md",
    ".yml", ".yaml", ".cfg", ".ini",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    ".ini",
}

# --- (2) Core Logic - No need to edit below this line ---

class ProjectDumper:
    """
    Dumps the structure and content of the current project (all files and subdirectories)
    into a single, organized text file.
    """
    def __init__(self, root_path):
        self.root_path = root_path
        self.output_filename = os.path.join(root_path, OUTPUT_FILENAME)
        
        # Automatically add this script's name to the excluded files list.
        self.excluded_files = EXCLUDED_FILES.union({os.path.basename(__file__)})
        self.excluded_dirs = EXCLUDED_DIRS
        self.included_extensions = INCLUDED_EXTENSIONS
        
        self.processed_files_count = 0

    def _is_relevant(self, path, is_dir=False):
        """Checks if a file or directory should be included in the dump."""
        basename = os.path.basename(path)
        if is_dir:
            return basename not in self.excluded_dirs
        
        if basename in self.excluded_files:
            return False
            
        return any(basename.endswith(ext) for ext in self.included_extensions)

    def generate_file_tree(self, outfile):
        """Generates and writes the visual file tree for the entire project."""
        print("🌳 Generating file tree...")
        outfile.write(f"{os.path.basename(self.root_path) or '.'}/\n")
        
        tree_paths = []
        for root, dirs, files in os.walk(self.root_path, topdown=True):
            # Filter out excluded directories in-place
            dirs[:] = [d for d in dirs if self._is_relevant(os.path.join(root, d), is_dir=True)]
            
            # Filter and sort relevant files
            relevant_files = sorted([f for f in files if self._is_relevant(os.path.join(root, f))])
            
            path_parts = os.path.relpath(root, self.root_path).split(os.sep)
            level = 0 if path_parts[0] == '.' else len(path_parts)

            # Add subdirectories to the tree structure
            if root != self.root_path:
                indent = ' ' * 4 * (level - 1)
                tree_paths.append(f"{indent}├── {os.path.basename(root)}/")

            # Add files to the tree structure
            indent = ' ' * 4 * level
            for i, filename in enumerate(relevant_files):
                connector = "└──" if i == len(relevant_files) - 1 else "├──"
                tree_paths.append(f"{indent}{connector} {filename}")

        # Write the final sorted tree for a clean, alphabetical structure
        for line in sorted(tree_paths):
             outfile.write(line + "\n")
        
        outfile.write("\n" + "="*80 + "\n\n")


    def dump_file_contents(self, outfile):
        """Dumps the contents of all relevant files in the project."""
        files_to_dump = []
        for root, dirs, files in os.walk(self.root_path, topdown=True):
            dirs[:] = [d for d in dirs if self._is_relevant(os.path.join(root, d), is_dir=True)]
            
            for filename in files:
                filepath = os.path.join(root, filename)
                if self._is_relevant(filepath):
                    files_to_dump.append(filepath)

        print(f"📄 Dumping file contents...")
        
        # Use tqdm for a progress bar
        for filepath in tqdm(sorted(files_to_dump), desc="  -> Processing files"):
            relative_filepath = os.path.relpath(filepath, self.root_path).replace(os.path.sep, '/')
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as infile:
                    content = infile.read()
                
                # This is the header that appears above each file's content.
                outfile.write(f"--- File: {relative_filepath} ---\n\n")
                outfile.write(content)
                outfile.write(f"\n\n{'='*80}\n\n")
                self.processed_files_count += 1
            except Exception as e:
                tqdm.write(f"  -> ⚠️  Could not read file {filepath}: {e}")

    def run(self):
        """The main method to orchestrate the entire dumping process."""
        print("🚀 Starting project dump process...")
        
        try:
            with open(self.output_filename, "w", encoding="utf-8") as outfile:
                # Phase 1: Generate the file tree structure.
                outfile.write("="*28 + " PROJECT STRUCTURE " + "="*29 + "\n\n")
                self.generate_file_tree(outfile)

                # Phase 2: Dump the file contents.
                outfile.write("="*31 + " FILE CONTENTS " + "="*32 + "\n\n")
                self.dump_file_contents(outfile)
            
            print("\n" + "*"*50)
            print("🎉 Success! Project dump completed.")
            print(f"    -> Summary: Processed {self.processed_files_count} files.")
            print(f"    -> Output file created at: '{os.path.abspath(self.output_filename)}'")
            print("*"*50)

        except IOError as e:
            print(f"\n❌ FATAL ERROR: Could not write to output file '{self.output_filename}'.\n   Reason: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    # The script will operate on the directory where it is located.
    script_path = os.path.dirname(os.path.abspath(__file__))
    
    dumper = ProjectDumper(root_path=script_path)
    dumper.run()