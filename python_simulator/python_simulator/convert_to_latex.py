#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Markdown protocol documents to LaTeX format with table of contents
"""

import os
import re
import subprocess
import shutil


def markdown_to_latex(md_file, tex_file):
    """Convert Markdown to LaTeX format"""
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # LaTeX document structure with table of contents
    latex_content = r"""\documentclass{ctexart}
\ctexset{fontset=ubuntu}
\usepackage{hyperref}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{geometry}
\usepackage{xcolor}

\geometry{
    left=2.5cm,
    right=2.5cm,
    top=2.5cm,
    bottom=2.5cm
}

\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=cyan,
}

\title{通信协议文档}
\author{司南测控系统}
\date{\today}

\begin{document}

\maketitle

\tableofcontents
\newpage

"""
    
    # Convert Markdown headers to LaTeX sections
    # Level 1 headers (##) -> \section
    content = re.sub(r'^##\s+(.+)$', r'\\section{\1}', content, flags=re.MULTILINE)
    
    # Level 2 headers (###) -> \subsection
    content = re.sub(r'^###\s+(.+)$', r'\\subsection{\1}', content, flags=re.MULTILINE)
    
    # Level 3 headers (####) -> \subsubsection
    content = re.sub(r'^####\s+(.+)$', r'\\subsubsection{\1}', content, flags=re.MULTILINE)
    
    # Convert bold text **text** to \textbf{text}
    content = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', content)
    
    # Convert italic text *text* to \textit{text}
    content = re.sub(r'\*(.+?)\*', r'\\textit{\1}', content)
    
    # Convert code blocks ```...``` to verbatim
    content = re.sub(r'```(\w+)?\n(.*?)\n```', r'\\begin{verbatim}\2\\end{verbatim}', content, flags=re.DOTALL)
    
    # Convert inline code `text` to \texttt{text}
    content = re.sub(r'`([^`]+)`', r'\\texttt{\1}', content)
    
    # Convert tables
    content = convert_tables(content)
    
    # Convert bullet points - convert to itemize
    content = convert_lists(content)
    
    # Convert > quotes to blockquote
    content = re.sub(r'^>\s+(.+)$', r'\\begin{quote}\n\1\n\\end{quote}', content, flags=re.MULTILINE)
    
    # Remove empty lines before sections
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Add the main content (ctexart handles Chinese automatically)
    latex_content += content
    
    latex_content += r"""

\end{document}
"""
    
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    
    print(f"Converted {md_file} to {tex_file}")


def convert_tables(content):
    """Convert Markdown tables to LaTeX longtable format"""
    
    # Find table blocks
    table_pattern = r'\|(.+)\|\n\|[-\s:|]+\|\n((?:\|.+\|\n)+)'
    
    def replace_table(match):
        header = match.group(1)
        rows = match.group(2).strip().split('\n')
        
        # Parse header
        headers = [h.strip() for h in header.split('|')]
        headers = [h for h in headers if h]  # Remove empty strings
        
        # Parse rows
        table_rows = []
        for row in rows:
            cells = [c.strip() for c in row.split('|')]
            cells = [c for c in cells if c]
            if cells:
                table_rows.append(cells)
        
        # Build LaTeX table
        num_cols = len(headers)
        col_spec = '|l|' + 'l|' * (num_cols - 1)
        
        latex_table = f'\\begin{{longtable}}{{{col_spec}}}\n'
        latex_table += '\\hline\n'
        
        # Header row
        latex_table += ' & '.join([f'\\textbf{{{h}}}' for h in headers])
        latex_table += ' \\\\\n'
        latex_table += '\\hline\n'
        
        # Data rows
        for row in table_rows:
            latex_table += ' & '.join(row)
            latex_table += ' \\\\\n'
        
        latex_table += '\\hline\n'
        latex_table += '\\end{longtable}\n'
        
        return latex_table
    
    content = re.sub(table_pattern, replace_table, content, flags=re.MULTILINE)
    
    return content


def convert_lists(content):
    """Convert bullet points to itemize"""
    
    lines = content.split('\n')
    result = []
    in_list = False
    list_level = 0
    
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result.append('\\begin{itemize}')
                in_list = True
            item_content = line.strip()[2:]
            result.append(f'\\item {item_content}')
        elif line.strip().startswith('  - '):
            if list_level == 0:
                result.append('\\begin{itemize}')
                list_level = 1
            item_content = line.strip()[4:]
            result.append(f'\\item {item_content}')
        else:
            if in_list:
                while list_level > 0:
                    result.append('\\end{itemize}')
                    list_level -= 1
                in_list = False
            result.append(line)
    
    # Close any open lists
    if in_list:
        while list_level > 0:
            result.append('\\end{itemize}')
            list_level -= 1
    
    return '\n'.join(result)


def compile_latex(tex_file, pdf_file):
    """Compile LaTeX file to PDF"""
    
    try:
        # Run pdflatex - use cwd to ensure it runs in the correct directory
        tex_dir = os.path.dirname(tex_file)
        tex_name = os.path.basename(tex_file)
        
        # First, run pdflatex with CJK package
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', tex_name],
            cwd=tex_dir,
            capture_output=True,
            timeout=30,
            text=False  # Don't decode as text to avoid UTF-8 issues
        )
        
        if result.returncode == 0:
            print(f"Successfully compiled {tex_file} to {pdf_file}")
            return True
        else:
            print(f"Error compiling {tex_file} (return code: {result.returncode})")
            # Try to decode output with error handling
            try:
                stdout = result.stdout.decode('utf-8', errors='replace')
                stderr = result.stderr.decode('utf-8', errors='replace')
                if stdout:
                    print("STDOUT:", stdout[:500])  # Print first 500 chars
                if stderr:
                    print("STDERR:", stderr[:500])
            except:
                pass
            return False
    except subprocess.TimeoutExpired:
        print(f"Timeout compiling {tex_file}")
        return False
    except Exception as e:
        print(f"Exception compiling {tex_file}: {e}")
        return False


def main():
    """Main function to convert all protocol documents"""
    
    # Define the documents to convert
    documents = [
        ('超导通信协议文档.md', '超导通信协议文档'),
        ('光量子通信协议文档.md', '光量子通信协议文档'),
        ('离子阱通信协议文档.md', '离子阱通信协议文档'),
        ('中性原子通信协议文档.md', '中性原子通信协议文档')
    ]
    
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    success_count = 0
    total_count = len(documents)
    
    for md_filename, title in documents:
        md_path = os.path.join(script_dir, md_filename)
        tex_filename = md_filename.replace('.md', '.tex')
        tex_path = os.path.join(script_dir, tex_filename)
        pdf_filename = md_filename.replace('.md', '.pdf')
        pdf_path = os.path.join(script_dir, pdf_filename)
        
        print(f"\n{'='*60}")
        print(f"Processing: {title}")
        print(f"{'='*60}")
        
        # Check if source file exists
        if not os.path.exists(md_path):
            print(f"Warning: {md_path} does not exist, skipping...")
            continue
        
        try:
            # Convert to LaTeX
            markdown_to_latex(md_path, tex_path)
            
            # Compile to PDF
            if compile_latex(tex_path, pdf_path):
                success_count += 1
                print(f"✓ Successfully created {pdf_filename}")
            else:
                print(f"✗ Failed to compile {pdf_filename}")
            
        except Exception as e:
            print(f"✗ Error processing {md_filename}: {e}")
            import traceback
            traceback.print_exc()
        
        # Clean up auxiliary files
        aux_files = [
            tex_path.replace('.tex', '.aux'),
            tex_path.replace('.tex', '.log'),
            tex_path.replace('.tex', '.out'),
        ]
        for aux_file in aux_files:
            if os.path.exists(aux_file):
                try:
                    os.remove(aux_file)
                except:
                    pass
    
    print(f"\n{'='*60}")
    print(f"Summary: {success_count}/{total_count} documents converted successfully")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
