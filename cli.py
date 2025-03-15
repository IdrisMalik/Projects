import argparse
import sys
from backend import FileHandler, validate_inputs

def cli_main():
    """Handle command-line interface execution."""
    parser = argparse.ArgumentParser(
        description="CLI Notepad Launcher - Create multiple text files and open them",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--folder', required=True, help="Target directory for files")
    parser.add_argument('--base-name', required=True, help="Base filename (without extension)")
    parser.add_argument('--start', type=int, default=1, help="Starting number for files")
    parser.add_argument('--count', type=int, default=1, help="Number of files to create")
    parser.add_argument('--content', default='', help="Initial content for files")
    
    args = parser.parse_args()
    
    valid, message = validate_inputs(args.folder, args.base_name, args.count)
    if not valid:
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(1)
    
    try:
        created_files = FileHandler.create_files(
            args.folder,
            args.base_name,
            args.start,
            args.count,
            args.content
        )
        print(f"Successfully created {len(created_files)} files in {args.folder}")
        FileHandler.open_files(created_files)
        print(f"Opened {len(created_files)} files in default applications")
    except Exception as e:
        print(f"Critical error: {str(e)}", file=sys.stderr)
        sys.exit(1)