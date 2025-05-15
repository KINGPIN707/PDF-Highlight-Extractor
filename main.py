import argparse
import os
import sys
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PDF Highlight Extractor - Integration Script")
    parser.add_argument("--install", action="store_true", help="Install required dependencies")
    parser.add_argument("--input", type=str, help="Input PDF file to process")
    parser.add_argument("--output", type=str, help="Output file for extracted text")
    parser.add_argument("--format", choices=["markdown", "html"], default="markdown",
                        help="Output format - markdown or html (default: markdown)")
  
    return parser.parse_args()

def install_dependencies():
    """Install required dependencies."""
    print("Installing required dependencies...")
    try:
        import pip
        pip.main(['install', 'PyMuPDF', 'pypdfium2', 'numpy', 'opencv-python', 'pillow'])
        print("Dependencies installed successfully!")
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def main():
    """Main function."""
    args = parse_arguments()
    
    # Check if installation is requested
    if args.install:
        install_dependencies()
        return
        
    # Import here after potential installation
    try:
        from pdf_extractor import PDFHighlightExtractor
    except ImportError:
        print("Error: PDF Highlight Extractor module not found or dependencies missing.")
        print("Run with --install flag to install required dependencies.")
        sys.exit(1)
    
    # Process PDF if input provided
    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)
            
        output_path = args.output
        if not output_path:
            # Use input filename with appropriate extension
            input_path = Path(args.input)
            ext = '.html' if args.format == 'html' else '.txt'
            output_path = str(input_path.with_suffix(ext))
        
        print(f"Processing {args.input}...")
        extractor = PDFHighlightExtractor(args.input)
        extractor.extract_and_format(output_path, args.format)
        
        
        print("Processing complete!")
        return
        
    # If no specific action, show help
    print("Please specify an action (--install, or --input).")
    print("Use --help for more information.")


if __name__ == "__main__":
    main()