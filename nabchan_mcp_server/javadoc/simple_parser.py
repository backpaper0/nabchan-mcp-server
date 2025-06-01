"""Simple Javadoc HTML parser using only standard library."""

import json
import re
import html.parser
from pathlib import Path
from typing import Dict, List, Optional, Union


class SimpleHTMLParser(html.parser.HTMLParser):
    """Simple HTML parser to extract data from Javadoc."""
    
    def __init__(self):
        super().__init__()
        self.in_target = False
        self.current_tag = None
        self.current_attrs = {}
        self.data = []
        self.links = []
        self.text_content = []
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        
        if tag == 'a' and 'href' in self.current_attrs:
            self.links.append({
                'href': self.current_attrs['href'],
                'text': ''
            })
    
    def handle_data(self, data):
        if self.current_tag:
            self.text_content.append(data.strip())
            
            # Store link text
            if self.current_tag == 'a' and self.links:
                self.links[-1]['text'] += data.strip()
    
    def handle_endtag(self, tag):
        self.current_tag = None


class JavadocParser:
    """Parser for extracting information from Javadoc HTML files using standard library."""
    
    def __init__(self, base_path: str, version: str = "LATEST"):
        """Initialize the parser with a base path and version."""
        self.base_path = Path(base_path)
        self.version = version
        self.javadoc_path = self.base_path / "docs" / version / "javadoc"
        
        if not self.javadoc_path.exists():
            raise ValueError(f"Javadoc path does not exist: {self.javadoc_path}")
        
        # Detect Javadoc version (old frame-based vs new)
        self.is_modern = (self.javadoc_path / "allpackages-index.html").exists()
    
    def _parse_html_file(self, file_path: Path) -> SimpleHTMLParser:
        """Parse an HTML file and return the parser object."""
        parser = SimpleHTMLParser()
        try:
            content = file_path.read_text(encoding='utf-8')
            parser.feed(content)
        except Exception:
            pass
        return parser
    
    def _extract_summary_from_content(self, content: str, summary_type: str) -> str:
        """Extract summary from HTML content using pattern matching."""
        try:
            # Look for different patterns based on summary type
            if summary_type == "package":
                # Package description pattern: <section class="package-description">...<div class="block">...</div>
                match = re.search(r'<section[^>]*class="[^"]*package-description[^"]*"[^>]*>.*?<div[^>]*class="[^"]*block[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
            elif summary_type == "class":
                # Class description pattern: <section class="class-description">...<div class="block">...</div>
                match = re.search(r'<section[^>]*class="[^"]*class-description[^"]*"[^>]*>.*?<div[^>]*class="[^"]*block[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
            elif summary_type == "class_summary":
                # Class summary in package file: <div class="col-last...class-summary..."><div class="block">...</div>
                match = re.search(r'<div[^>]*class="[^"]*col-last[^"]*class-summary[^"]*"[^>]*>.*?<div[^>]*class="[^"]*block[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
            else:
                return ""
            
            if match:
                # Clean up HTML tags and normalize whitespace
                summary = match.group(1)
                summary = re.sub(r'<[^>]+>', ' ', summary)  # Remove HTML tags
                summary = re.sub(r'\s+', ' ', summary)  # Normalize whitespace
                return summary.strip()
        except Exception:
            pass
        return ""
    
    def get_all_packages(self) -> List[Dict[str, str]]:
        """Get a list of all packages with their names."""
        packages = []
        
        if self.is_modern:
            # Modern Javadoc - use element-list
            element_list = self.javadoc_path / "element-list"
            if element_list.exists():
                content = element_list.read_text(encoding='utf-8')
                for line in content.splitlines():
                    if line.strip() and not line.startswith('module:'):
                        packages.append({
                            'name': line.strip(),
                            'summary': ''
                        })
        else:
            # Old Javadoc - use package-list
            package_list = self.javadoc_path / "package-list"
            if package_list.exists():
                content = package_list.read_text(encoding='utf-8')
                for line in content.splitlines():
                    if line.strip():
                        packages.append({
                            'name': line.strip(),
                            'summary': ''
                        })
        
        return sorted(packages, key=lambda x: x['name'])
    
    def get_package_info(self, package_name: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get basic information about a package."""
        package_path = package_name.replace('.', '/')
        summary_file = self.javadoc_path / package_path / "package-summary.html"
        
        if not summary_file.exists():
            raise ValueError(f"Package not found: {package_name}")
        
        content = summary_file.read_text(encoding='utf-8')
        parser = self._parse_html_file(summary_file)
        
        # Extract package summary
        package_summary = self._extract_summary_from_content(content, "package")
        
        # Extract classes with summaries
        classes = []
        
        # Use regex to find class entries in the summary table
        # Pattern matches two-column layout with class name and description
        class_pattern = r'<div[^>]*class="[^"]*col-first[^"]*class-summary[^"]*"[^>]*>.*?<a[^>]*href="([^"]+\.html)"[^>]*title="[^"]*">([^<]+)</a></div>\s*<div[^>]*class="[^"]*col-last[^"]*class-summary[^"]*"[^>]*>(.*?)</div>'
        
        for match in re.finditer(class_pattern, content, re.DOTALL | re.IGNORECASE):
            href = match.group(1)
            class_name = match.group(2).strip()
            summary_section = match.group(3)
            
            # Extract summary from the block div (block div is already at the top level)
            block_match = re.search(r'<div[^>]*class="[^"]*block[^"]*"[^>]*>(.*?)</div>', summary_section, re.DOTALL | re.IGNORECASE)
            class_summary = ""
            if block_match:
                class_summary = block_match.group(1)
                class_summary = re.sub(r'<[^>]+>', ' ', class_summary)  # Remove HTML tags
                class_summary = re.sub(r'\s+', ' ', class_summary)  # Normalize whitespace
                class_summary = class_summary.strip()
            else:
                # The summary_section itself might be the content we want, try direct text extraction
                text_only = re.sub(r'<[^>]+>', ' ', summary_section)
                text_only = re.sub(r'\s+', ' ', text_only).strip()
                if text_only and len(text_only) > 5:  # Avoid capturing just whitespace
                    class_summary = text_only
            
            # Determine type based on content or default to class
            if 'interface' in summary_section.lower():
                class_type = 'interface'
            elif 'enum' in summary_section.lower():
                class_type = 'enum'
            elif 'annotation' in summary_section.lower():
                class_type = 'annotation'
            elif 'exception' in class_name.lower():
                class_type = 'exception'
            else:
                class_type = 'class'
            
            classes.append({
                'name': class_name,
                'type': class_type,
                'summary': class_summary
            })
        
        # If regex didn't find anything, fall back to link parsing
        if not classes:
            for link in parser.links:
                href = link['href']
                text = link['text']
                
                # Filter for class links (ending with .html but not package-*.html)
                if (href.endswith('.html') and 
                    not href.startswith('package-') and 
                    not href.startswith('../') and
                    not href.startswith('#') and
                    '/' not in href and  # Exclude links to other packages
                    text and 
                    not text.startswith('All ') and
                    text not in ['Prev', 'Next', 'Frames', 'No Frames']):
                    
                    # Only include if it looks like a valid class name
                    if text and text[0].isupper() and '.' not in text:
                        classes.append({
                            'name': text,
                            'type': 'class',
                            'summary': ''
                        })
        
        # Remove duplicates
        seen = set()
        unique_classes = []
        for cls in classes:
            if cls['name'] not in seen:
                seen.add(cls['name'])
                unique_classes.append(cls)
        
        return {
            'name': package_name,
            'summary': package_summary,
            'classes': sorted(unique_classes, key=lambda x: x['name'])
        }
    
    def get_class_info(self, class_name: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get basic information about a class."""
        # Find the class HTML file
        class_simple_name = class_name.split('.')[-1]
        package_path = '.'.join(class_name.split('.')[:-1]).replace('.', '/')
        
        class_file = self.javadoc_path / package_path / f"{class_simple_name}.html"
        
        if not class_file.exists():
            # Try to find it by searching
            for html_file in self.javadoc_path.rglob(f"{class_simple_name}.html"):
                content = html_file.read_text(encoding='utf-8')
                if content.find(class_name) != -1:
                    class_file = html_file
                    break
            else:
                raise ValueError(f"Class not found: {class_name}")
        
        content = class_file.read_text(encoding='utf-8')
        
        # Determine type from title or content
        type_info = "class"
        title_match = re.search(r'<h\d[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h\d>', content, re.IGNORECASE)
        if title_match:
            title_text = title_match.group(1).lower()
            if 'interface' in title_text:
                type_info = "interface"
            elif 'enum' in title_text:
                type_info = "enum"
            elif 'annotation' in title_text:
                type_info = "annotation"
            elif 'exception' in title_text:
                type_info = "exception"
            elif 'error' in title_text:
                type_info = "error"
        
        # Extract class summary
        class_summary = self._extract_summary_from_content(content, "class")
        
        # Extract methods with summaries
        methods = []
        
        # Pattern for method summary table entries in three-column format  
        # Each row has col-first, col-second, col-last with same row-color class
        row_pattern = r'<div[^>]*class="[^"]*col-first[^"]*(?:even|odd)-row-color[^"]*method-summary-table[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*col-second[^"]*(?:even|odd)-row-color[^"]*method-summary-table[^"]*"[^>]*>(.*?)</div>\s*<div[^>]*class="[^"]*col-last[^"]*(?:even|odd)-row-color[^"]*method-summary-table[^"]*"[^>]*>(.*?)</div>'
        
        for row_match in re.finditer(row_pattern, content, re.DOTALL | re.IGNORECASE):
            col2 = row_match.group(2)  # Method column
            col3 = row_match.group(3)  # Description column
            
            # Extract method name from col2
            method_match = re.search(r'<a[^>]*class="[^"]*member-name-link[^"]*"[^>]*>([^<]+)</a>', col2)
            if method_match:
                method_name = method_match.group(1).strip()
                
                # Extract summary from col3
                # Handle potential whitespace around block div
                block_match = re.search(r'<div[^>]*class="[^"]*block[^"]*"[^>]*>\s*(.*?)\s*</div>', col3, re.DOTALL)
                method_summary = ""
                if block_match:
                    method_summary = block_match.group(1)
                    method_summary = re.sub(r'<[^>]+>', ' ', method_summary)  # Remove HTML tags
                    method_summary = re.sub(r'\s+', ' ', method_summary)  # Normalize whitespace
                    method_summary = method_summary.strip()
                else:
                    # Try direct text extraction from col3 if no block div
                    text_only = re.sub(r'<[^>]+>', ' ', col3)
                    text_only = re.sub(r'\s+', ' ', text_only).strip()
                    if text_only and len(text_only) > 5:
                        method_summary = text_only
                
                # Try to extract signature from col2
                signature_match = re.search(r'<code[^>]*>(.*?)</code>', col2, re.DOTALL | re.IGNORECASE)
                signature = method_name + "(...)"
                if signature_match:
                    sig_text = signature_match.group(1)
                    sig_text = re.sub(r'<[^>]+>', '', sig_text)  # Remove HTML tags
                    sig_text = re.sub(r'\s+', ' ', sig_text)  # Normalize whitespace
                    signature = sig_text.strip()
                
                methods.append({
                    'name': method_name,
                    'signature': signature,
                    'modifiers': '',
                    'summary': method_summary,
                    'type': 'method'
                })
        
        # Also look for constructor pattern  
        constructor_pattern = r'<div[^>]*class="[^"]*col-first[^"]*constructor-summary[^"]*"[^>]*>.*?</div>\s*<div[^>]*class="[^"]*col-second[^"]*constructor-summary[^"]*"[^>]*>.*?<a[^>]*class="[^"]*member-name-link[^"]*"[^>]*>(' + re.escape(class_simple_name) + r')</a>.*?</div>\s*<div[^>]*class="[^"]*col-last[^"]*constructor-summary[^"]*"[^>]*>(.*?)</div>'
        
        for match in re.finditer(constructor_pattern, content, re.DOTALL | re.IGNORECASE):
            constructor_name = match.group(1).strip()
            summary_section = match.group(2)
            
            # Extract summary from the block div
            block_match = re.search(r'<div[^>]*class="[^"]*block[^"]*"[^>]*>(.*?)</div>', summary_section, re.DOTALL | re.IGNORECASE)
            constructor_summary = ""
            if block_match:
                constructor_summary = block_match.group(1)
                constructor_summary = re.sub(r'<[^>]+>', ' ', constructor_summary)  # Remove HTML tags
                constructor_summary = re.sub(r'\s+', ' ', constructor_summary)  # Normalize whitespace
                constructor_summary = constructor_summary.strip()
            
            # Try to extract signature
            signature_match = re.search(r'<code[^>]*>(.*?)</code>', match.group(0), re.DOTALL | re.IGNORECASE)
            signature = constructor_name + "(...)"
            if signature_match:
                sig_text = signature_match.group(1)
                sig_text = re.sub(r'<[^>]+>', '', sig_text)  # Remove HTML tags
                sig_text = re.sub(r'\s+', ' ', sig_text)  # Normalize whitespace
                signature = sig_text.strip()
            
            methods.append({
                'name': constructor_name,
                'signature': signature,
                'modifiers': '',
                'summary': constructor_summary,
                'type': 'constructor'
            })
        
        return {
            'name': class_name,
            'type': type_info,
            'summary': class_summary,
            'methods': methods
        }
    
    def search_by_keyword(self, keyword: str) -> Dict[str, List[Dict[str, str]]]:
        """Search for classes by keyword in index."""
        keyword_lower = keyword.lower()
        results = {'classes': [], 'methods': []}
        
        if self.is_modern:
            # Try to parse type-search-index.js
            type_index_file = self.javadoc_path / "type-search-index.js"
            if type_index_file.exists():
                content = type_index_file.read_text(encoding='utf-8')
                # Extract JSON data
                match = re.search(r'typeSearchIndex\s*=\s*(\[.*?\]);', content, re.DOTALL)
                if match:
                    try:
                        type_data = json.loads(match.group(1))
                        for item in type_data:
                            if keyword_lower in item.get('l', '').lower():
                                results['classes'].append({
                                    'name': item.get('l', ''),
                                    'package': item.get('p', ''),
                                    'type': 'class'
                                })
                    except json.JSONDecodeError:
                        pass
        else:
            # For old Javadoc, search in allclasses files
            allclasses_file = self.javadoc_path / "allclasses-noframe.html"
            if not allclasses_file.exists():
                allclasses_file = self.javadoc_path / "allclasses-frame.html"
            
            if allclasses_file.exists():
                parser = self._parse_html_file(allclasses_file)
                for link in parser.links:
                    if keyword_lower in link['text'].lower():
                        results['classes'].append({
                            'name': link['text'],
                            'package': '',
                            'type': 'class'
                        })
        
        return results