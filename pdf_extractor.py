import os
import re
import io
import sys
import argparse
import html
from typing import List, Dict, Tuple, Optional, Literal
import fitz  # PyMuPDF
import pypdfium2 as pdfium
from PIL import Image
import numpy as np
import cv2
from dataclasses import dataclass, field

@dataclass
class TextBlock:
    """Class for storing text blocks with their formatting attributes."""
    text: str
    is_header: bool = False
    is_bold: bool = False  
    is_italic: bool = False
    header_level: int = 0  # 0 means not a header, 1-6 for header levels

@dataclass
class Highlight:
    """Class for storing information about a highlight."""
    page_number: int
    rect: Tuple[float, float, float, float]  # x0, y0, x1, y1
    blocks: List[TextBlock] = field(default_factory=list)
    y_position: float = None  # Store y-position for sorting
    
    def __post_init__(self):
        # Extract y_position from rect if not explicitly provided
        if self.y_position is None:
            self.y_position = self.rect[1]  # y0 from rectangle


class PDFHighlightExtractor:
    """Class for extracting highlighted text from PDF files."""
    
    def __init__(self, pdf_path: str, highlight_color: Tuple[int, int, int] = (255, 255, 0)):
        """Initialize the PDF highlight extractor.
        
        Args:
            pdf_path: Path to the PDF file
            highlight_color: RGB tuple of the highlight color (default: yellow)
        """
        self.pdf_path = pdf_path
        self.highlight_color = highlight_color
        self.tolerance = 50  # Color detection tolerance
        self.doc = fitz.open(pdf_path) if pdf_path else None
        self.highlights = []
        
    def _is_similar_color(self, color1, color2):
        """Check if two colors are similar within tolerance."""
        return sum(abs(c1 - c2) for c1, c2 in zip(color1, color2)) < self.tolerance
        
    def detect_highlights(self):
        """Detect highlights in the PDF."""
        print(f"Scanning {self.pdf_path} for highlights...")
        
        # Use pdfium and OpenCV for highlight detection
        pdf = pdfium.PdfDocument(self.pdf_path)
        
        for page_index in range(len(pdf)):
            page = pdf.get_page(page_index)
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            
            # Convert PIL to OpenCV format
            cv_image = np.array(pil_image)
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            
            # Create mask for highlight color
            lower_bound = np.array([max(0, c - self.tolerance) for c in self.highlight_color[::-1]])
            upper_bound = np.array([min(255, c + self.tolerance) for c in self.highlight_color[::-1]])
            mask = cv2.inRange(cv_image, lower_bound, upper_bound)
            
            # Find contours in the mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Get page dimensions for normalization
            page_width, page_height = pil_image.size
            
            # Process each contour (highlight area)
            for contour in contours:
                # Filter out small noise artifacts
                if cv2.contourArea(contour) < 100:
                    continue
                    
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Normalize coordinates to PDF space
                x0 = x / 2.0  # Divide by 2.0 because we rendered with scale=2.0
                y0 = y / 2.0
                x1 = (x + w) / 2.0
                y1 = (y + h) / 2.0
                
                # Create highlight object with y_position
                highlight = Highlight(
                    page_number=page_index,
                    rect=(x0, y0, x1, y1),
                    y_position=y0  # Store y-position explicitly
                )
                self.highlights.append(highlight)
            
            print(f"  Page {page_index + 1}: Found {len(contours)} potential highlight areas")
            
        # Validate with PyMuPDF annotations
        self._validate_with_annotations()
        
        return self.highlights
        
    def _validate_with_annotations(self):
        """Validate highlights using PDF annotations if available."""
        highlight_annotations = []
        
        for page_index, page in enumerate(self.doc):
            for annot in page.annots():
                if annot.type[0] == 8:  # Highlight annotation
                    highlight = Highlight(
                        page_number=page_index,
                        rect=annot.rect,
                        y_position=annot.rect[1]  # Store the y-position (top coordinate)
                    )
                    highlight_annotations.append(highlight)
        
        # If we found annotations, prefer these over image detection
        if highlight_annotations:
            print(f"Found {len(highlight_annotations)} highlight annotations in the PDF")
            self.highlights = highlight_annotations
            
    def extract_text_from_highlights(self):
        """Extract text from highlighted areas with formatting information."""
        if not self.highlights:
            print("No highlights detected. Run detect_highlights() first.")
            return []
            
        print(f"Extracting text from {len(self.highlights)} highlighted areas...")
        
        # Sort highlights by page number and then by y-position within each page
        self.highlights.sort(key=lambda h: (h.page_number, h.y_position))
        
        for highlight in self.highlights:
            page = self.doc[highlight.page_number]
            rect = fitz.Rect(highlight.rect)
            
            # Get text blocks in the highlight area
            blocks = page.get_text("dict", clip=rect)["blocks"]
            
            # Sort blocks by their vertical position (top to bottom)
            blocks.sort(key=lambda b: b["bbox"][1])
            
            for block in blocks:
                # Sort lines within each block by vertical position
                lines = sorted(block.get("lines", []), key=lambda l: l["bbox"][1])
                
                for line in lines:
                    # Sort spans within each line by horizontal position (left to right)
                    spans = sorted(line.get("spans", []), key=lambda s: s["bbox"][0])
                    
                    for span in spans:
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                            
                        # Extract formatting information
                        font_name = span.get("font", "").lower()
                        font_size = span.get("size", 0)
                        flags = span.get("flags", 0)
                        
                        # Detect text attributes
                        is_bold = "bold" in font_name or (flags & 2) != 0
                        is_italic = "italic" in font_name or "oblique" in font_name or (flags & 1) != 0
                        
                        # Check if this might be a header based on font size
                        is_header = False
                        header_level = 0
                        
                        # Basic heuristic: headers are usually larger text
                        # This may need adjustment based on your PDFs
                        base_size = 11.0  # Typical base font size
                        if font_size > base_size * 1.8:
                            is_header = True
                            header_level = 1
                        elif font_size > base_size * 1.5:
                            is_header = True
                            header_level = 2
                        elif font_size > base_size * 1.3:
                            is_header = True
                            header_level = 3
                            
                        # Create TextBlock object
                        text_block = TextBlock(
                            text=text,
                            is_header=is_header,
                            is_bold=is_bold,
                            is_italic=is_italic,
                            header_level=header_level
                        )
                        
                        highlight.blocks.append(text_block)
        
        return self.highlights
                
    def format_output(self, output_format: str = "markdown"):
        """ Format extracted highlights, 
          preserving formatting and removing unwanted line breaks.
        
        Args:
            output_format: Format to output, either "markdown" or "html"
        
        Returns:
            Formatted text string in the specified format
        """
        if not any(h.blocks for h in self.highlights):
            print("No text extracted from highlights. Run extract_text_from_highlights() first.")
            return ""
            
        result = []
        
        # Process highlights in the correct order (by page and then by position)
        sorted_highlights = sorted(self.highlights, key=lambda h: (h.page_number, h.y_position))
        
        for highlight in sorted_highlights:
            if not highlight.blocks:
                continue
                
            current_paragraph = []
            current_format = None
            
            for block in highlight.blocks:
                # If format changes or we hit a header, start a new paragraph
                if current_format and (
                    block.is_header != current_format.is_header or
                    block.header_level != current_format.header_level
                ):
                    # Add the completed paragraph to results
                    result.append(self._format_paragraph(current_paragraph, current_format, output_format))
                    current_paragraph = []
                
                current_paragraph.append(block)
                current_format = block
                
            # Add the last paragraph
            if current_paragraph:
                result.append(self._format_paragraph(current_paragraph, current_format, output_format))
        
        if output_format == "html":
            # Wrap HTML content in basic structure
            html_result = "\n".join(result)
            return f"""<!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="UTF-8">
                            <title>Extracted Highlighted Text</title>
                            <style>
                                body {{ 
                                    font-family: Arial, sans-serif; 
                                    line-height: 1.6;
                                    margin: 2rem;
                                    max-width: 800px;
                                }}
                                h1, h2, h3, h4, h5, h6 {{ 
                                    margin-top: 1.5em;
                                    margin-bottom: 0.5em;
                                }}
                                p {{ margin-bottom: 1em; }}
                                .page-marker {{
                                    margin-top: 2em;
                                    padding: 0.5em;
                                    background-color: #f0f0f0;
                                    border-radius: 4px;
                                    font-size: 0.9em;
                                    color: #666;
                                }}
                            </style>
                        </head>
                        <body>
                        {html_result}
                        </body>
                        </html>"""
        
        else:
            # For markdown, just join with double newlines
            return "\n\n".join(result)
    
    def _format_paragraph(self, blocks, format_info, output_format="markdown"):
        """Format a paragraph based on its formatting attributes."""
        if not blocks:
            return ""
            
        # If it's a header, format accordingly
        if format_info.is_header:
            text = " ".join(block.text for block in blocks)
            
            if output_format == "html":
                h_level = min(format_info.header_level, 6)  # HTML supports h1-h6
                # Escape HTML special characters
                safe_text = html.escape(text)
                return f"<h{h_level}>{safe_text}</h{h_level}>"
            else:
                # Markdown header
                header_marker = "#" * format_info.header_level
                return f"{header_marker} {text}"
            
        # For normal paragraphs, join text and preserve formatting
        paragraph = []
        for block in blocks:
            text = block.text
            
            if output_format == "html":
                # Escape HTML special characters
                text = html.escape(text)
                
                # Apply HTML formatting
                if block.is_bold and block.is_italic:
                    text = f"<strong><em>{text}</em></strong>"
                elif block.is_bold:
                    text = f"<strong>{text}</strong>"
                elif block.is_italic:
                    text = f"<em>{text}</em>"
            else:
                # Apply markdown formatting
                if block.is_bold:
                    text = f"**{text}**"
                if block.is_italic:
                    text = f"*{text}*"
                
            paragraph.append(text)
            
        # Join with spaces to remove line breaks
        joined_text = " ".join(paragraph)
        
        if output_format == "html":
            return f"<p>{joined_text}</p>"
        else:
            return joined_text
    
    def extract_and_format(self, output_path=None, output_format="markdown"):
        """Full pipeline: detect highlights, extract text, and format.
        
        Args:
            output_path: Path to save the output file (optional)
            output_format: Format to output, either "markdown" or "html"
            
        Returns:
            Formatted text string
        """
        self.detect_highlights()
        self.extract_text_from_highlights()
        formatted_text = self.format_output(output_format)
        
        if output_path:
            # Determine file extension based on format
            if output_path.endswith(('.md', '.txt', '.html')):
                # Use the provided extension
                pass
            else:
                # Add appropriate extension based on format
                ext = '.html' if output_format == 'html' else '.md'
                output_path = f"{output_path}{ext}"
                
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            print(f"Formatted text saved to {output_path}")
            
        return formatted_text
    

def create_cli():
    """Create command-line interface."""
    parser = argparse.ArgumentParser(
        description="Extract highlighted text from PDF files while preserving formatting."
    )
    parser.add_argument(
        "pdf_path", nargs="?", 
        help="Path to the PDF file to process"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format", choices=["markdown", "html"], default="markdown",
        help="Output format - markdown or html (default: markdown)"
    )
    
    return parser


def main():
    parser = create_cli()
    args = parser.parse_args()
      
    if not args.pdf_path:
        parser.print_help()
        return
        
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        return
        
    try:
        extractor = PDFHighlightExtractor(args.pdf_path)
        formatted_text = extractor.extract_and_format(args.output, args.format)
        
        if not args.output:
            print(f"\nExtracted and formatted text ({args.format}):")
            print("-" * 40)
            print(formatted_text)
            print("-" * 40)
            
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()