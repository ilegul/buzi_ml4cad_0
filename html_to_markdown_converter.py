#!/usr/bin/env python3
"""
HTML to Markdown Converter
Converts HTML files (like notebook exports) to clean Markdown format
"""

import os
import re
import base64
from pathlib import Path
import datetime

def convert_html_to_markdown_pandoc(html_file, output_file=None):
    """
    Convert HTML to Markdown using pandoc (most reliable method)
    Requires: pip install pypandoc + pandoc installed on system
    """
    try:
        import pypandoc
        
        if output_file is None:
            html_path = Path(html_file)
            output_file = html_path.parent / f"{html_path.stem}.md"
        
        # Convert with pandoc
        output = pypandoc.convert_file(
            html_file, 
            'markdown',
            outputfile=str(output_file),
            extra_args=['--wrap=none', '--extract-media=images']
        )
        
        print(f"Converted to: {output_file}")
        return str(output_file)
        
    except ImportError:
        print("Pypandoc not installed. Install with: pip install pypandoc")
        return None
    except Exception as e:
        print(f"Pandoc conversion failed: {e}")
        return None

def convert_html_to_markdown_markdownify(html_file, output_file=None):
    """
    Convert HTML to Markdown using markdownify library
    Requires: pip install markdownify
    """
    try:
        from markdownify import markdownify as md
        
        if output_file is None:
            html_path = Path(html_file)
            output_file = html_path.parent / f"{html_path.stem}.md"
        
        # Read HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Convert to markdown
        markdown_content = md(
            html_content,
            heading_style="ATX",  # Use # for headings
            bullets="-",          # Use - for bullet points
            strong_mark="**",     # Use ** for bold
            em_mark="_"           # Use _ for italic
        )
        
        # Clean up the markdown
        markdown_content = clean_markdown(markdown_content)
        
        # Save markdown file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Converted to: {output_file}")
        return str(output_file)
        
    except ImportError:
        print("Markdownify not installed. Install with: pip install markdownify")
        return None
    except Exception as e:
        print(f"Markdownify conversion failed: {e}")
        return None

def convert_html_to_markdown_custom(html_file, output_file=None, extract_images=True):
    """
    Custom HTML to Markdown converter using regex and BeautifulSoup
    Requires: pip install beautifulsoup4 lxml
    """
    try:
        from bs4 import BeautifulSoup
        
        if output_file is None:
            html_path = Path(html_file)
            output_file = html_path.parent / f"{html_path.stem}.md"
        
        # Read HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text() if title else "Notebook Export"
        
        # Start markdown content
        markdown_lines = [
            f"# {title_text}",
            "",
            f"*Exported on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "---",
            ""
        ]
        
        # Process notebook cells
        cells = soup.find_all(['div'], class_=lambda x: x and ('jp-Cell' in x or 'cell' in x or 'output' in x))
        
        if not cells:
            # Fallback: process all content
            cells = [soup.body] if soup.body else [soup]
        
        image_counter = 0
        images_dir = Path(output_file).parent / "images"
        
        for cell in cells:
            cell_markdown = process_cell_to_markdown(cell, images_dir, image_counter, extract_images)
            if cell_markdown.strip():
                markdown_lines.extend(cell_markdown)
                markdown_lines.append("")
        
        # Join and clean markdown
        markdown_content = "\n".join(markdown_lines)
        markdown_content = clean_markdown(markdown_content)
        
        # Save markdown file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Converted to: {output_file}")
        if extract_images and images_dir.exists():
            print(f"Images extracted to: {images_dir}")
        
        return str(output_file)
        
    except ImportError:
        print("BeautifulSoup not installed. Install with: pip install beautifulsoup4 lxml")
        return None
    except Exception as e:
        print(f"Custom conversion failed: {e}")
        return None

def process_cell_to_markdown(cell, images_dir, image_counter, extract_images):
    """Process a single cell/element to markdown"""
    markdown_lines = []
    
    # Handle headings
    for level in range(1, 7):
        headings = cell.find_all(f'h{level}')
        for h in headings:
            markdown_lines.append(f"{'#' * level} {h.get_text().strip()}")
    
    # Handle code blocks
    code_blocks = cell.find_all(['pre', 'code'])
    for code in code_blocks:
        if code.parent and code.parent.name == 'pre':
            continue  # Skip nested code in pre
        
        code_text = code.get_text()
        if '\n' in code_text or len(code_text) > 50:
            # Multi-line code block
            markdown_lines.extend([
                "```",
                code_text.strip(),
                "```"
            ])
        else:
            # Inline code
            markdown_lines.append(f"`{code_text.strip()}`")
    
    # Handle images
    images = cell.find_all('img')
    for img in images:
        src = img.get('src', '')
        alt = img.get('alt', 'Image')
        
        if src.startswith('data:image/'):
            # Base64 image
            if extract_images:
                image_path = extract_base64_image(src, images_dir, image_counter)
                if image_path:
                    markdown_lines.append(f"![{alt}]({image_path})")
                    image_counter += 1
            else:
                markdown_lines.append(f"*[Image: {alt}]*")
        else:
            # Regular image
            markdown_lines.append(f"![{alt}]({src})")
    
    # Handle tables
    tables = cell.find_all('table')
    for table in tables:
        table_md = convert_table_to_markdown(table)
        if table_md:
            markdown_lines.extend(table_md)
    
    # Handle regular text (paragraphs, divs)
    text_elements = cell.find_all(['p', 'div'], recursive=False)
    for elem in text_elements:
        if elem.find(['table', 'img', 'pre', 'code']):
            continue  # Skip if contains special elements
        
        text = elem.get_text().strip()
        if text:
            markdown_lines.append(text)
    
    return markdown_lines

def convert_table_to_markdown(table):
    """Convert HTML table to Markdown table"""
    rows = table.find_all('tr')
    if not rows:
        return []
    
    markdown_rows = []
    
    for i, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue
        
        # Convert cells to text
        cell_texts = [cell.get_text().strip() for cell in cells]
        markdown_row = "| " + " | ".join(cell_texts) + " |"
        markdown_rows.append(markdown_row)
        
        # Add header separator after first row if it contains th elements
        if i == 0 and row.find('th'):
            separator = "| " + " | ".join(['---'] * len(cell_texts)) + " |"
            markdown_rows.append(separator)
    
    return markdown_rows

def extract_base64_image(data_url, images_dir, counter):
    """Extract base64 image to file"""
    try:
        # Parse data URL
        header, data = data_url.split(',', 1)
        
        # Determine format
        if 'png' in header:
            ext = 'png'
        elif 'jpeg' in header or 'jpg' in header:
            ext = 'jpg'
        elif 'svg' in header:
            ext = 'svg'
        else:
            ext = 'png'  # Default
        
        # Create images directory
        images_dir.mkdir(exist_ok=True)
        
        # Generate filename
        filename = f"image_{counter:03d}.{ext}"
        filepath = images_dir / filename
        
        # Decode and save
        image_data = base64.b64decode(data)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        return f"images/{filename}"
        
    except Exception as e:
        print(f"Failed to extract image {counter}: {e}")
        return None

def clean_markdown(markdown_content):
    """Clean and format markdown content"""
    # Remove excessive newlines
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
    
    # Remove empty code blocks
    markdown_content = re.sub(r'```\s*```', '', markdown_content)
    
    # Clean up spacing around headers
    markdown_content = re.sub(r'\n+(#{1,6}\s)', r'\n\n\1', markdown_content)
    
    # Remove trailing whitespace
    lines = [line.rstrip() for line in markdown_content.split('\n')]
    markdown_content = '\n'.join(lines)
    
    return markdown_content.strip()

def auto_convert_notebook_html(html_file, method='auto'):
    """
    Automatically convert notebook HTML to Markdown using best available method
    
    Args:
        html_file (str): Path to HTML file
        method (str): 'auto', 'pandoc', 'markdownify', or 'custom'
    
    Returns:
        str: Path to generated Markdown file
    """
    html_path = Path(html_file)
    if not html_path.exists():
        print(f"HTML file not found: {html_file}")
        return None
    
    print(f"Converting {html_file} to Markdown...")
    
    if method == 'auto':
        # Try methods in order of preference
        result = convert_html_to_markdown_pandoc(html_file)
        if result:
            return result
        
        result = convert_html_to_markdown_markdownify(html_file)
        if result:
            return result
        
        result = convert_html_to_markdown_custom(html_file)
        return result
    
    elif method == 'pandoc':
        return convert_html_to_markdown_pandoc(html_file)
    elif method == 'markdownify':
        return convert_html_to_markdown_markdownify(html_file)
    elif method == 'custom':
        return convert_html_to_markdown_custom(html_file)
    else:
        print(f"Unknown method: {method}")
        return None

# Quick conversion function
def quick_html_to_md(html_file):
    """Quick conversion with automatic method selection"""
    return auto_convert_notebook_html(html_file, method='auto')

def select_files_jupyter():
    """
    Jupyter notebook file selection using ipywidgets
    """
    try:
        from ipywidgets import widgets, interact, Layout
        from IPython.display import display, clear_output
        import glob
        
        # Get all HTML files in current and subdirectories
        html_files = []
        for pattern in ["*.html", "*/*.html", "exported_notebooks/*.html"]:
            html_files.extend(glob.glob(pattern))
        
        if not html_files:
            print("No HTML files found in current directory or subdirectories")
            return
        
        print("Available HTML files:")
        selected_files = []
        
        # Create checkboxes for each file
        checkboxes = []
        for i, file_path in enumerate(html_files):
            checkbox = widgets.Checkbox(
                value=False,
                description=file_path,
                layout=Layout(width='100%')
            )
            checkboxes.append(checkbox)
        
        # Method selection
        method_dropdown = widgets.Dropdown(
            options=[
                ('Auto (best available)', 'auto'),
                ('Pandoc (highest quality)', 'pandoc'), 
                ('Markdownify (simple)', 'markdownify'),
                ('Custom (always works)', 'custom')
            ],
            value='auto',
            description='Method:'
        )
        
        # Convert button
        convert_button = widgets.Button(
            description='Convert Selected Files',
            button_style='success',
            layout=Layout(width='200px', height='40px')
        )
        
        # Output area
        output_area = widgets.Output()
        
        def on_convert_click(b):
            with output_area:
                clear_output()
                
                # Get selected files
                selected = [html_files[i] for i, cb in enumerate(checkboxes) if cb.value]
                
                if not selected:
                    print("No files selected!")
                    return
                
                method = method_dropdown.value
                print(f"Converting {len(selected)} files using {method} method...\n")
                
                success_count = 0
                for file_path in selected:
                    try:
                        print(f"Converting: {file_path}")
                        result = auto_convert_notebook_html(file_path, method=method)
                        if result:
                            success_count += 1
                            print(f"✅ Success: {result}")
                        else:
                            print(f"❌ Failed: {file_path}")
                    except Exception as e:
                        print(f"❌ Error converting {file_path}: {e}")
                    print()
                
                print(f"\n🎉 Conversion complete: {success_count}/{len(selected)} files successful")
        
        convert_button.on_click(on_convert_click)
        
        # Display UI
        print("Select files to convert:")
        for cb in checkboxes:
            display(cb)
        
        display(method_dropdown)
        display(convert_button)
        display(output_area)
        
    except ImportError:
        print("ipywidgets not available. Using file path input method.")
        select_files_manual()

def select_files_manual():
    """
    Manual file selection by listing available files
    """
    import glob
    
    # Find HTML files
    html_files = []
    for pattern in ["*.html", "*/*.html", "exported_notebooks/*.html", "**/*.html"]:
        html_files.extend(glob.glob(pattern, recursive=True))
    
    if not html_files:
        print("No HTML files found in current directory or subdirectories")
        print("Make sure your HTML files are in the current directory or subdirectories")
        return
    
    print(f"\nFound {len(html_files)} HTML files:")
    print("=" * 50)
    
    for i, file_path in enumerate(html_files, 1):
        file_size = os.path.getsize(file_path) / 1024  # Size in KB
        print(f"{i:2d}. {file_path} ({file_size:.1f} KB)")
    
    print("\nEnter file numbers to convert (comma-separated, e.g. 1,3,5):")
    print("Or enter 'all' to convert all files")
    
    selection = input("Selection: ").strip()
    
    if selection.lower() == 'all':
        selected_files = html_files
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_files = [html_files[i] for i in indices if 0 <= i < len(html_files)]
        except (ValueError, IndexError):
            print("Invalid selection. Please enter valid file numbers.")
            return
    
    if not selected_files:
        print("No valid files selected.")
        return
    
    print(f"\nSelected {len(selected_files)} files:")
    for f in selected_files:
        print(f"  - {f}")
    
    # Method selection
    print("\nConversion methods:")
    methods = [
        ("auto", "Auto (best available)"),
        ("pandoc", "Pandoc (highest quality)"),
        ("markdownify", "Markdownify (simple)"),
        ("custom", "Custom (always works)")
    ]
    
    for i, (value, description) in enumerate(methods, 1):
        print(f"{i}. {description}")
    
    while True:
        try:
            choice = int(input("\nSelect method (1-4): "))
            if 1 <= choice <= 4:
                method = methods[choice-1][0]
                break
            else:
                print("Please enter 1, 2, 3, or 4")
        except ValueError:
            print("Please enter a number")
    
    # Convert files
    print(f"\nConverting {len(selected_files)} files using {method} method...")
    print("=" * 60)
    
    success_count = 0
    for file_path in selected_files:
        try:
            print(f"\nConverting: {file_path}")
            result = auto_convert_notebook_html(file_path, method=method)
            if result:
                success_count += 1
                print(f"✅ Success: {result}")
            else:
                print(f"❌ Failed: {file_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎉 Conversion complete: {success_count}/{len(selected_files)} files successful")

def quick_select_and_convert():
    """
    Quick file selection and conversion - tries best method available
    """
    # Try Jupyter widgets first, then fallback to manual
    try:
        from ipywidgets import widgets
        select_files_jupyter()
    except ImportError:
        select_files_manual()

# Update the main selection function
def select_and_convert_files():
    """
    Interactive file selection and conversion - uses best available method
    """
    try:
        # Try Jupyter widgets first (works in VS Code notebooks)
        from ipywidgets import widgets
        select_files_jupyter()
    except ImportError:
        try:
            # Try tkinter GUI (works in standalone Python)
            import tkinter as tk
            from tkinter import filedialog, messagebox, ttk
            
            # [Previous tkinter GUI code would go here if needed]
            print("GUI not available in notebook environment.")
            select_files_manual()
            
        except ImportError:
            # Fallback to manual selection
            select_files_manual()

def quick_convert_gui():
    """Quick GUI launcher"""
    select_and_convert_files()

if __name__ == "__main__":
    print("HTML to Markdown Converter")
    print("Usage options:")
    print("1. GUI: select_and_convert_files()")
    print("2. Quick GUI: quick_convert_gui()")
    print("3. Direct: auto_convert_notebook_html('file.html')")
    print("4. CLI: select_files_cli()")
    
    # Auto-launch GUI if run directly
    select_and_convert_files()