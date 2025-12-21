from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.models import RequirementsResult, ExtractionResult

logger = logging.getLogger(__name__)

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available. DOCX export will not work.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available. Logo may not display correctly.")


def clear_paragraph(paragraph):
    """Clear all runs from a paragraph by removing XML children."""
    p = paragraph._p
    for child in list(p):
        p.remove(child)


def setup_styles(doc):
    """Configure document styles for clean, professional output."""
    # Normal / Body text style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    pf = normal.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15
    
    # Heading styles
    for level in (1, 2, 3, 4):
        try:
            h = doc.styles[f"Heading {level}"]
            h.font.name = "Calibri"
            h.paragraph_format.space_before = Pt(12 if level <= 2 else 8)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True  # Avoids headings dangling at bottom
        except KeyError:
            logger.warning(f"Heading {level} style not found, skipping")
    
    try:
        list_bullet = doc.styles["List Bullet"]
        list_bullet.font.name = "Calibri"
        list_bullet.font.size = Pt(11)
        pf = list_bullet.paragraph_format
        pf.left_indent = Inches(0.25)
        pf.first_line_indent = Inches(-0.25)
    except KeyError:
        logger.warning("List Bullet style not found, will use default")


def setup_page_formatting(doc):
    """Configure page margins and add footer page numbers."""
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    
    # Add page number to footer
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    run._r.append(fld)


def add_modern_front_page(doc, title: str, project_root: Optional[Path] = None):
    """Create a modern, professional front page with logo and title."""
    # Find logo path - try multiple locations (same path as used in frontend Header.jsx)
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent
    
    logo_path = None
    # Try multiple possible logo locations (prioritize the same path as frontend)
    possible_logo_paths = [
        # Same path as frontend/src/components/Header.jsx uses
        project_root / "frontend" / "src" / "assets" / "logo-transparent.png",
        project_root / "frontend" / "src" / "assets" / "logo.png",
        # Docker/backend assets folder (copied during build)
        project_root / "assets" / "logo-transparent.png",
        project_root / "assets" / "logo.png",
        # Fallback locations
        project_root / "backend" / "assets" / "logo-transparent.png",
        project_root / "backend" / "assets" / "logo.png",
    ]
    
    for path in possible_logo_paths:
        if path.exists():
            logo_path = path
            logger.info(f"Found logo at: {logo_path}")
            break
    
    if logo_path is None:
        logger.warning(f"Logo not found. Tried paths: {[str(p) for p in possible_logo_paths]}")
    
    # Add spacing at top
    for _ in range(2):
        doc.add_paragraph()
    
    # Add logo if available
    if logo_path and logo_path.exists():
        try:
            logo_para = doc.add_paragraph()
            logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add logo with appropriate size
            run = logo_para.add_run()
            if PIL_AVAILABLE:
                # Get image dimensions to maintain aspect ratio
                try:
                    img = Image.open(logo_path)
                    width, height = img.size
                    aspect_ratio = width / height
                    # Set height to 1.5 inches, calculate width
                    logo_height = Inches(1.5)
                    logo_width = Inches(1.5 * aspect_ratio)
                    logger.info(f"Logo dimensions: {width}x{height}, display size: {logo_width} x {logo_height}")
                except Exception as e:
                    logger.warning(f"Failed to get logo dimensions: {e}")
                    logo_width = Inches(3.5)
                    logo_height = Inches(1.5)
            else:
                logo_width = Inches(3.5)
                logo_height = Inches(1.5)
            
            run.add_picture(str(logo_path), width=logo_width, height=logo_height)
            logger.info(f"Successfully added logo to front page")
            
            # Add spacing after logo
            doc.add_paragraph()
            doc.add_paragraph()
        except Exception as e:
            logger.error(f"Failed to add logo to front page: {e}", exc_info=True)
    else:
        logger.warning("Logo not found or not accessible, skipping logo on front page")
    
    # Add title with modern styling (handle long titles with word wrap)
    # Adjust font size based on title length
    title_length = len(title)
    if title_length > 80:
        font_size = Pt(24)
    elif title_length > 60:
        font_size = Pt(28)
    else:
        font_size = Pt(32)
    
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_para.paragraph_format.space_after = Pt(12)
    title_para.paragraph_format.space_before = Pt(0)
    
    # Enable word wrap and prevent truncation
    title_para.paragraph_format.widow_control = False
    title_para.paragraph_format.keep_together = False
    title_para.paragraph_format.keep_with_next = False
    
    # Set paragraph properties to allow wrapping and prevent truncation
    p_pr = title_para._element.get_or_add_pPr()
    # Remove any text overflow restrictions
    try:
        # Ensure text can wrap - set word wrap property
        wrap = OxmlElement('w:wordWrap')
        wrap.set(qn('w:val'), '0')  # 0 = wrap text
        p_pr.append(wrap)
        
        # Remove any overflow clip settings
        overflow = OxmlElement('w:overflowPunct')
        overflow.set(qn('w:val'), '0')  # Allow punctuation to overflow
        p_pr.append(overflow)
        
        # Remove any width restrictions - ensure paragraph can use full page width
        # Remove any indentation that might restrict width
        if p_pr.find(qn('w:ind')) is not None:
            p_pr.remove(p_pr.find(qn('w:ind')))
    except Exception:
        pass
    
    # Always add title as a single run to let Word handle wrapping naturally
    # This prevents truncation issues
    title_run = title_para.add_run(title)
    title_run.font.name = "Calibri"
    title_run.font.size = font_size
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(26, 84, 144)
    
    # Ensure the run doesn't have any restrictions that might cause truncation
    try:
        r_pr = title_run._element.get_or_add_rPr()
        # Remove any text effects that might truncate
        # Ensure no character limits are applied
    except Exception:
        pass
    
    logger.info(f"Added title to front page: '{title[:50]}...' (length: {title_length}, font size: {font_size})")
    
    # Add spacing
    doc.add_paragraph()
    doc.add_paragraph()
    
    # Add date with subtle styling
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(datetime.now().strftime("%B %d, %Y"))
    date_run.font.name = "Calibri"
    date_run.font.size = Pt(14)
    date_run.font.color.rgb = RGBColor(100, 100, 100)  # Gray
    
    # Add more spacing
    for _ in range(4):
        doc.add_paragraph()
    
    # Add company info section with modern styling
    company_para = doc.add_paragraph()
    company_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    company_run = company_para.add_run("fusionAIx")
    company_run.font.name = "Calibri"
    company_run.font.size = Pt(20)
    company_run.font.bold = True
    company_run.font.color.rgb = RGBColor(26, 84, 144)
    
    # Add website
    website_para = doc.add_paragraph()
    website_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    website_run = website_para.add_run("www.fusionaix.com")
    website_run.font.name = "Calibri"
    website_run.font.size = Pt(12)
    website_run.font.color.rgb = RGBColor(100, 100, 100)
    
    # Add decorative line (optional - using spacing instead for cleaner look)
    doc.add_paragraph()


def add_word_toc(paragraph):
    """Insert a real Word TOC field that can be auto-updated."""
    run = paragraph.add_run()
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'TOC \\o "1-3" \\h \\z \\u')
    run._r.append(fld)


def set_table_header_cell(cell):
    """Format a table header cell with bold text and styling."""
    for p in cell.paragraphs:
        for r in p.runs:
            r.bold = True
            try:
                r.font.color.rgb = RGBColor(255, 255, 255)  # White text
            except:
                pass
    try:
        tc_pr = cell._element.get_or_add_tcPr()
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), '1a5490')
        shading.set(qn('w:val'), 'clear')
        tc_pr.append(shading)
    except Exception as e:
        logger.warning("Failed to set table header color: %s", e)


def finalize_table(table):
    """Apply final polish to a table: autofit, alignment, padding."""
    try:
        table.autofit = True
    except:
        pass
    
    # Set vertical alignment and cell padding
    for row in table.rows:
        for cell in row.cells:
            try:
                # Set vertical alignment to top for body cells
                tc_pr = cell._element.get_or_add_tcPr()
                v_align = OxmlElement('w:vAlign')
                v_align.set(qn('w:val'), 'top')
                tc_pr.append(v_align)
                
                # Set cell padding (top, right, bottom, left in twips - 1/20th of a point)
                tc_mar = OxmlElement('w:tcMar')
                for margin_name, margin_val in [('top', '80'), ('right', '80'), ('bottom', '80'), ('left', '80')]:
                    margin = OxmlElement(f'w:{margin_name}')
                    margin.set(qn('w:w'), margin_val)
                    margin.set(qn('w:type'), 'dxa')
                    tc_mar.append(margin)
                tc_pr.append(tc_mar)
            except Exception as e:
                logger.debug("Failed to set table cell formatting: %s", e)


def _add_formatted_text_to_paragraph(para, text: str):
    if not text:
        return
    
    if para.runs:
        clear_paragraph(para)
    
    parts = []
    last_end = 0
    
    for match in re.finditer(r'\*\*(.*?)\*\*', text):
        if match.start() > last_end:
            parts.append(('normal', text[last_end:match.start()]))
        parts.append(('bold', match.group(1)))
        last_end = match.end()
    
    if last_end < len(text):
        parts.append(('normal', text[last_end:]))
    
    if not parts:
        parts = [('normal', text)]
    
    for fmt_type, content in parts:
        if content:  # Only add non-empty content
            run = para.add_run(content)
            if fmt_type == 'bold':
                run.bold = True


def _add_bullet_paragraph(doc, content: str):
    """Add a paragraph with proper bullet point formatting using standard bullets."""
    para = doc.add_paragraph()
    
    # Set up proper indentation for bullet point
    pf = para.paragraph_format
    pf.left_indent = Inches(0.25)
    pf.first_line_indent = Inches(-0.25)
    pf.space_after = Pt(6)
    
    # Add bullet character
    bullet_run = para.add_run('• ')  # Standard bullet character
    bullet_run.font.name = "Calibri"
    bullet_run.font.size = Pt(11)
    
    # Add formatted content (handle bold formatting)
    parts = []
    last_end = 0
    
    for match in re.finditer(r'\*\*(.*?)\*\*', content):
        if match.start() > last_end:
            parts.append(('normal', content[last_end:match.start()]))
        parts.append(('bold', match.group(1)))
        last_end = match.end()
    
    if last_end < len(content):
        parts.append(('normal', content[last_end:]))
    
    if not parts:
        parts = [('normal', content)]
    
    for fmt_type, part_content in parts:
        if part_content:  # Only add non-empty content
            run = para.add_run(part_content)
            run.font.name = "Calibri"
            run.font.size = Pt(11)
            if fmt_type == 'bold':
                run.bold = True
    
    return para


def _start_table(doc, header_cells: List[str]):
    """Create a new table with header row. Returns the table object."""
    num_cols = len(header_cells)
    current_table = doc.add_table(rows=1, cols=num_cols)
    try:
        current_table.style = 'Light Grid Accent 1'
    except:
        try:
            current_table.style = 'Grid Table 1 Light'
        except:
            pass
    
    header_row_cells = current_table.rows[0].cells
    for col_idx, cell_text in enumerate(header_cells):
        cell = header_row_cells[col_idx]
        cell.text = cell_text
        set_table_header_cell(cell)
    
    return current_table


def _parse_markdown_to_docx(doc, text: str):
    if not text:
        return
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^---+$', stripped):
            continue
        cleaned_lines.append(line)
    
    lines = cleaned_lines
    i = 0
    in_table = False
    current_table = None
    in_code_block = False
    code_block_lines = []
    last_was_blank = False
    list_item_buffer = []
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Handle code blocks
        if stripped.startswith('```'):
            if in_code_block:
                # End code block
                if code_block_lines:
                    para = doc.add_paragraph(style='Normal')
                    para.style.font.name = 'Consolas'
                    para.style.font.size = Pt(10)
                    para.text = '\n'.join(code_block_lines)
                code_block_lines = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # Handle blank lines - only add one paragraph break max
        if not stripped:
            if in_table and current_table:
                # Finalize table when we hit a blank line
                finalize_table(current_table)
                in_table = False
                current_table = None
            elif not last_was_blank:
                # Only add paragraph if last wasn't blank (avoid gappy docs)
                doc.add_paragraph()
                last_was_blank = True
            i += 1
            continue
        
        last_was_blank = False
        
        # Handle tables
        if '|' in stripped and not stripped.startswith('#'):
            # Check if this is a table header (next line is separator)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^[\|\s:\-]+$', next_line):
                    # Start new table
                    cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
                    if cells:
                        current_table = _start_table(doc, cells)
                        in_table = True
                        i += 2
                        continue
            
            # Check if we're in an existing table
            if in_table and current_table:
                cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
                if cells:
                    row = current_table.add_row()
                    for col_idx, cell_text in enumerate(cells):
                        if col_idx < len(row.cells):
                            cell = row.cells[col_idx]
                            cell.text = ""  # Clear first
                            para = cell.paragraphs[0]
                            _add_formatted_text_to_paragraph(para, cell_text)
                i += 1
                continue
        
        # If we were in a table, finalize it before moving on
        if in_table and current_table:
            finalize_table(current_table)
            in_table = False
            current_table = None
        
        # Handle list items (including multi-line)
        if stripped.startswith('- ') or stripped.startswith('* ') or re.match(r'^\d+\.\s', stripped):
            # Start or continue list item
            if stripped.startswith('- ') or stripped.startswith('* '):
                content = stripped[2:].strip()
                is_bullet = True
            else:
                content = re.sub(r'^\d+\.\s', '', stripped).strip()
                is_bullet = False
            
            # Check if next line continues this list item (not a new list item and not blank)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                # If next line is not a list marker and not blank, it's a continuation
                if (next_stripped and 
                    not next_stripped.startswith('- ') and 
                    not next_stripped.startswith('* ') and 
                    not re.match(r'^\d+\.\s', next_stripped)):
                    list_item_buffer.append(content)
                    list_item_buffer.append(next_stripped)
                    i += 2
                    # Continue collecting until we hit a new list item or blank line
                    while i < len(lines):
                        cont_line = lines[i]
                        cont_stripped = cont_line.strip()
                        if (not cont_stripped or 
                            cont_stripped.startswith('- ') or 
                            cont_stripped.startswith('* ') or 
                            re.match(r'^\d+\.\s', cont_stripped)):
                            break
                        list_item_buffer.append(cont_stripped)
                        i += 1
                    # Now add the complete list item
                    full_content = ' '.join(list_item_buffer)
                    list_item_buffer = []
                    full_content = _capitalize_sentence(full_content)
                    if is_bullet:
                        _add_bullet_paragraph(doc, full_content)
                    else:
                        para = doc.add_paragraph(style='List Number')
                        _add_formatted_text_to_paragraph(para, full_content)
                    continue
            
            # Single-line list item
            content = _capitalize_sentence(content)
            if is_bullet:
                _add_bullet_paragraph(doc, content)
            else:
                para = doc.add_paragraph(style='List Number')
                _add_formatted_text_to_paragraph(para, content)
            i += 1
            continue
        
        # Regular text/headings
        _add_text_line(doc, stripped)
        i += 1
    
    # Finalize any remaining table
    if in_table and current_table:
        finalize_table(current_table)
    
    # Handle any remaining code block
    if in_code_block and code_block_lines:
        para = doc.add_paragraph(style='Normal')
        para.style.font.name = 'Consolas'
        para.style.font.size = Pt(10)
        para.text = '\n'.join(code_block_lines)


def _clean_markdown_text(text: str) -> str:
    if not text:
        return text

    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*\*([^*]*)\*\*', r'\1', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    return text


def _capitalize_sentence(text: str) -> str:
    if not text:
        return text
    text = text.strip()
    if text and text[0].islower():
        return text[0].upper() + text[1:]
    return text


def _add_text_line(doc, line: str):
    """Add a single line of text to the document, handling headings and regular text."""
    stripped = line.strip()
    if not stripped:
        return
    
    if re.match(r'^---+$', stripped):
        return
    
    if stripped.startswith('#### '):
        header_text = _clean_markdown_text(stripped[5:])
        if header_text:
            doc.add_heading(header_text, 4)
    elif stripped.startswith('### '):
        header_text = _clean_markdown_text(stripped[4:])
        if header_text:
            doc.add_heading(header_text, 3)
    elif stripped.startswith('## '):
        header_text = _clean_markdown_text(stripped[3:])
        if header_text:
            doc.add_heading(header_text, 2)
    elif stripped.startswith('# '):
        header_text = _clean_markdown_text(stripped[2:])
        if header_text:
            doc.add_heading(header_text, 1)
    else:
        content = _clean_markdown_text(stripped)
        if content:
            if content and len(content) > 0 and content[0].islower() and content[0].isalpha():
                content = _capitalize_sentence(content)
            para = doc.add_paragraph()
            _add_formatted_text_to_paragraph(para, content)


def generate_rfp_docx(
    individual_responses: List[Dict[str, Any]],
    requirements_result: RequirementsResult,
    extraction_result: ExtractionResult,
    rfp_title: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> bytes:
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx is not installed. Install it with: pip install python-docx")
    
    logger.info("Generating DOCX document: %d requirement responses", len(individual_responses))
    
    doc = Document()
    
    # Setup styles first (cleanest output)
    setup_styles(doc)
    
    # Setup page formatting (margins and footer)
    setup_page_formatting(doc)
    
    # Determine project root for logo path (always calculate from file location)
    project_root = Path(__file__).parent.parent.parent
    
    # Create modern front page
    final_title = rfp_title or extraction_result.language.upper()
    add_modern_front_page(doc, final_title, project_root)
    
    doc.add_page_break()
    
    doc.add_heading("Table of Contents", 1)
    
    # Use real Word TOC field instead of manual list
    toc_para = doc.add_paragraph()
    add_word_toc(toc_para)
    
    doc.add_page_break()
    
    doc.add_heading("Company Overview", 1)
    overview_text = """At fusionAIx, we believe that the future of digital transformation lies in the seamless blend of low-code platforms and artificial intelligence. Our core team brings together decades of implementation experience, domain expertise, and a passion for innovation. We partner with enterprises to reimagine processes, accelerate application delivery, and unlock new levels of efficiency. We help businesses scale smarter, faster, and with greater impact.

With a collaborative spirit and a commitment to excellence, our team transforms complex challenges into intelligent, practical solutions. fusionAIx is not just about technology—it's about empowering people, industries, and enterprises to thrive in a digital-first world.

We are proud to be officially recognized as a Great Place To Work® Certified Company for 2025–26, reflecting our commitment to a culture built on trust, innovation, and people-first values.

fusionAIx delivers tailored solutions that blend AI and automation to drive measurable results across industries. We are a niche Pega partner with 20+ successful Pega Constellation implementations across the globe. As Constellation migration experts, we focus on pattern-based development with Constellation, enabling faster project go-lives than traditional implementation approaches.

Our proven capabilities span three core technology platforms: Pega Constellation, Microsoft Power Platform, and ServiceNow. Through these platforms, we provide comprehensive services including Low Code/No Code development, Digital Process Transformation, and AI & Data solutions.

To accelerate time-to-value, fusionAIx offers proprietary accelerators and solution components including fxAgentSDK, fxAIStudio, fxMockUpToView, and fxSmartDCO. These tools enable rapid development, intelligent automation, and streamlined project delivery.

We support clients across diverse industries including Insurance, Banking & Finance, Government & Public Sector, Automotive & Fleet Management, and Travel & Tourism, combining platform expertise with structured knowledge transfer to help customers build sustainable, future-ready capabilities."""
    
    for para_text in overview_text.split('\n\n'):
        if para_text.strip():
            doc.add_paragraph(para_text.strip())
    
    doc.add_page_break()
    
    is_structured = len(individual_responses) == 1 and individual_responses[0].get('requirement_id') == 'STRUCTURED'
    
    if is_structured:
        response_text = individual_responses[0].get('response', '')
        _parse_markdown_to_docx(doc, response_text)
    else:
        doc.add_heading("Solution Requirement Responses", 1)
        for idx, resp_data in enumerate(individual_responses, 1):
            req_heading = doc.add_heading(f"Requirement {idx}: {resp_data.get('requirement_id', 'N/A')}", 2)
            
            req_para = doc.add_paragraph()
            req_para.add_run("Requirement: ").bold = True
            req_text = resp_data.get('requirement_text', '')
            if req_text:
                req_para.add_run(_capitalize_sentence(req_text))
            
            resp_heading = doc.add_heading("Response", 3)
            _parse_markdown_to_docx(doc, resp_data.get('response', ''))
            
            if resp_data.get('quality'):
                quality = resp_data['quality']
                quality_para = doc.add_paragraph()
                quality_para.add_run(f"Quality Score: {quality.get('score', 0):.0f}/100 | ").bold = True
                quality_para.add_run(f"Completeness: {quality.get('completeness', 'unknown')} | ")
                quality_para.add_run(f"Relevance: {quality.get('relevance', 'unknown')}")
            
            doc.add_paragraph()
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        logger.info("DOCX saved to: %s", output_path.absolute())
        return output_path.read_bytes()
    else:
        # Use BytesIO instead of temp file round-trip
        buf = BytesIO()
        doc.save(buf)
        bytes_data = buf.getvalue()
        logger.info("DOCX generated: %d bytes (in memory)", len(bytes_data))
        return bytes_data

