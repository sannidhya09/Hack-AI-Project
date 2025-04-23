# -----------------------------
# FILE: pdf_utils.py
# -----------------------------
import fitz  # PyMuPDF
import os
import tempfile
from PIL import Image
import pytesseract
import io
import re

def clean_text(text):
    """Clean extracted text to remove unnecessary whitespace and formatting."""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove unnecessary line breaks
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Remove multiple consecutive line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_text_and_tables_from_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    full_text = ""
    tables = []
    extracted_image_text = []
    
    # Get total pages for progress reporting
    total_pages = len(doc)
    
    # Process only the first 30 pages if document is very large
    max_pages = min(30, total_pages)
    
    for page_num in range(max_pages):
        page = doc[page_num]
        
        # Extract text
        page_text = page.get_text()
        full_text += page_text
        
        # Extract tables using advanced table detection
        # First, try to detect tables using layout analysis
        dict_text = page.get_text("dict")
        blocks = dict_text["blocks"]
        
        # Process each block to identify tables
        for block in blocks:
            if "lines" in block:
                lines = block["lines"]
                
                # Skip blocks with very few lines
                if len(lines) < 2:
                    continue
                    
                # Store the entire block text for analysis
                block_text = ""
                for line in lines:
                    if "spans" in line:
                        line_text = " ".join([span["text"] for span in line["spans"]])
                        block_text += line_text + "\n"
                
                # Check if this looks like a table using multiple heuristics
                is_table = False
                
                # 1. Check for common table markers
                table_markers = ["S.No.", "Sl.No.", "S. No.", "No.", "Total", "Particulars", "%"]
                if any(marker in block_text for marker in table_markers) and len(lines) > 2:
                    is_table = True
                
                # 2. Check for numeric content pattern typical of tables
                if not is_table:
                    # Count lines with multiple numbers
                    numeric_line_count = 0
                    for line in lines:
                        if "spans" in line:
                            line_text = " ".join([span["text"] for span in line["spans"]])
                            # Count digits and percentage signs
                            digit_count = sum(c.isdigit() for c in line_text)
                            if digit_count > 5 or "%" in line_text:
                                numeric_line_count += 1
                    
                    # If many lines contain numbers, likely a table
                    if numeric_line_count > 2 and numeric_line_count / len(lines) > 0.3:
                        is_table = True
                
                # 3. Check for consistent spatial alignment
                if not is_table and len(lines) > 2:
                    # Get x-positions of spans
                    line_x_positions = []
                    for line in lines:
                        if "spans" in line:
                            positions = [span["bbox"][0] for span in line["spans"]]
                            if positions:
                                line_x_positions.append(positions)
                    
                    # Check for alignment across multiple lines
                    if line_x_positions:
                        # Find positions that occur frequently
                        all_positions = [pos for line_pos in line_x_positions for pos in line_pos]
                        
                        # Group nearby positions (within 5 points)
                        clusters = []
                        if all_positions:
                            sorted_pos = sorted(all_positions)
                            current_cluster = [sorted_pos[0]]
                            
                            for pos in sorted_pos[1:]:
                                if pos - current_cluster[-1] < 5:
                                    current_cluster.append(pos)
                                else:
                                    if len(current_cluster) > 2:  # Only keep significant clusters
                                        clusters.append(sum(current_cluster) / len(current_cluster))
                                    current_cluster = [pos]
                            
                            if len(current_cluster) > 2:
                                clusters.append(sum(current_cluster) / len(current_cluster))
                        
                        # If we have multiple column positions, it's likely a table
                        if len(clusters) >= 3:
                            is_table = True
                
                if is_table:
                    # Enhanced table extraction with better formatting preservation
                    table_text = ""
                    
                    # Extract table heading if present (usually the line before the table)
                    table_heading = ""
                    try:
                        # Look at blocks above this one to find potential headings
                        for prev_block in blocks:
                            if "lines" in prev_block and prev_block != block:
                                last_line = prev_block["lines"][-1]
                                last_line_text = " ".join([s["text"] for s in last_line["spans"]])
                                if any(word in last_line_text.lower() for word in ["employees", "gender", "directors", "table", "distribution"]):
                                    table_heading = last_line_text
                                    break
                    except:
                        pass
                    
                    if table_heading:
                        table_text += f"TABLE HEADING: {table_heading}\n"
                    
                    # Process each line, preserving column structure
                    for line in lines:
                        if "spans" in line:
                            spans = line["spans"]
                            
                            # First sort spans by x-position
                            spans.sort(key=lambda span: span["bbox"][0])
                            
                            # Initialize an empty line with proper spacing
                            formatted_line = ""
                            last_x_end = 0
                            
                            for span in spans:
                                span_text = span["text"].strip()
                                if not span_text:
                                    continue
                                    
                                x_start = span["bbox"][0]
                                
                                # Add proper spacing to maintain column alignment
                                if last_x_end > 0:
                                    # Calculate spaces needed
                                    space_width = 4  # Approximate width of a space
                                    spaces_needed = max(1, int((x_start - last_x_end) / space_width))
                                    
                                    # For large gaps, use tabs instead of spaces
                                    if spaces_needed > 6:
                                        formatted_line += "\t"
                                    else:
                                        formatted_line += " " * spaces_needed
                                
                                # Add the actual text
                                formatted_line += span_text
                                last_x_end = span["bbox"][2]  # Update last end position
                            
                            # Add the formatted line to the table
                            table_text += formatted_line + "\n"
                    
                    # Only include tables with substantial content
                    if len(table_text.strip().split("\n")) > 2 and 20 < len(table_text) < 5000:
                        # Add page number and cleaned table text
                        formatted_table = f"--- TABLE FROM PAGE {page_num+1} ---\n{table_text.strip()}"
                        tables.append(formatted_table)
                        
                        # Also add tables directly to full text to ensure they're included
                        full_text += "\n\n" + formatted_table + "\n\n"
        
        # Extract images for OCR (limit to first 10 pages)
        if page_num < 10:
            image_list = page.get_images(full=True)
            
            # Process up to 3 images per page
            for img_index, img in enumerate(image_list[:3]):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Process image with PIL
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Skip small images
                    if image.width < 100 or image.height < 100:
                        continue
                    
                    # Extract text using OCR
                    img_text = pytesseract.image_to_string(image)
                    
                    # Check if the OCR text appears to contain a table
                    if img_text and (len(img_text) > 20) and any(marker in img_text for marker in ["Total", "%", "Male", "Female"]):
                        # Try to format as a table
                        formatted_ocr_text = f"--- TABLE FROM IMAGE (PAGE {page_num+1}) ---\n{img_text}"
                        tables.append(formatted_ocr_text)
                        extracted_image_text.append(formatted_ocr_text)
                    elif img_text and len(img_text) > 20:
                        extracted_image_text.append(f"Image text (page {page_num+1}): {img_text}")
                except Exception as e:
                    print(f"OCR error on page {page_num+1}, image {img_index+1}: {e}")
    
    doc.close()
    
    # Clean the extracted text
    full_text = clean_text(full_text)
    
    # Add image text if available
    if extracted_image_text:
        full_text += "\n\n" + "\n".join(extracted_image_text)
    
    # Limit total text length
    if len(full_text) > 150000:  # Increased limit
        full_text = full_text[:150000] + "\n\n[Document truncated due to size limitations]"
    
    # Return extracted content
    return full_text, tables
    
    