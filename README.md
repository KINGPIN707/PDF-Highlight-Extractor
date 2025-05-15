# PDF Highlight Extractor

A powerful Python tool for extracting highlighted text from PDF documents while preserving formatting information such as headers, bold text, and italics.

## Features

- Extracts text from highlighted areas in PDF documents
- Preserves text formatting (headers, bold, italic)
- Outputs formatted text in Markdown or HTML
- Detects and preserves hierarchical structure of documents
- Command-line interface for easy integration into workflows
- Intelligent paragraph and formatting detection

## Use Cases

- Content research and collection
- Academic paper review and note-taking
- Legal document analysis and extraction
- Knowledge management systems
- Content migration to CMSs


## Requirements

- Python 3.7+
- Dependencies:
    - PyMuPDF (fitz) - For PDF text extraction and annotation handling
    - pypdfium2 - For PDF rendering
    - OpenCV (cv2) - For image processing and highlight detection
    - NumPy - For array operations
    - Pillow (PIL) - For image handling

## Installation

```bash
# Clone the repository
git clone https://github.com/No0Bitah/PDF-Highlight-Extractor.git
cd PDF-Highlight-Extractor

# Install dependencies
python main.py --install
```

Alternatively, you can install dependencies manually:

```bash
pip install PyMuPDF pypdfium2 numpy opencv-python pillow
```

## Usage

### Basic Usage

```bash
python main.py --input sample.pdf --format markdown
```

This will process `sample.pdf` and save the extracted highlighted text to `sample.txt` in Markdown format.

### Command Line Arguments

```bash
# Install dependencies
python main.py --install

# Process a PDF file with default settings (markdown output)
python main.py --input document.pdf

# Process a PDF file and specify output file
python main.py --input document.pdf --output extracted_highlights.md

# Generate HTML output
python main.py --input document.pdf --format html --output extracted_highlights.html
```

### Using as a Library

You can also use the `PDFHighlightExtractor` class directly in your Python code:

```python
from pdf_extractor import PDFHighlightExtractor

# Initialize the extractor
extractor = PDFHighlightExtractor("document.pdf")

# Run the full pipeline
formatted_text = extractor.extract_and_format(output_path="output.md", output_format="markdown")

# Or run individual steps
extractor.detect_highlights()
extractor.extract_text_from_highlights()
formatted_text = extractor.format_output(output_format="markdown")
```

## Limitations

- Currently, the tool only detects **yellow highlights** (RGB: 255, 255, 0). Other highlight colors are not supported yet.
- The highlight detection works best on clean, well-scanned PDFs. Poor quality scans may affect detection accuracy.
- Header detection is based on font size heuristics and may not be perfect for all PDF documents.

## Future Improvements

1. Support for multiple highlight colors with color-coding in output
2. Improved header and structure detection
3. Option to extract annotations and comments
4. Support for PDF forms and fillable fields
5. Better handling of complex layouts (multi-column, mixed orientations)
6. CMS integration capabilities for direct publishing to content management systems
7. Web interface/API for remote processing
8. OCR integration for scanned documents
9. Batch processing for multiple PDFs

## How It Works

The tool uses a combination of image processing techniques (with OpenCV) and PDF parsing (with PyMuPDF) to:

1. Detect highlighted areas by color analysis
2. Extract text from those areas using PDF parsing libraries
3. Preserve formatting information from the original document
4. Reconstruct the logical structure of the highlighted content
5. Output in the desired format (Markdown or HTML)

## Troubleshooting

- **No highlights detected**: Try adjusting the `tolerance` parameter for color detection
- **Missing formatting**: Some PDFs don't store formatting as expected; manual adjustments may be needed
- **Performance issues with large PDFs**: Process page ranges instead of the entire document


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributors

- 🔗 [No0Bitah](https://github.com/No0Bitah)
- 📧 [Contact me](jomari.daison@gmail.com)