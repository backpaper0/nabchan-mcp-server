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
        
        parser = self._parse_html_file(summary_file)
        
        # Extract classes from links
        classes = []
        for link in parser.links:
            href = link['href']
            text = link['text']
            
            # Filter for class links (ending with .html but not package-*.html)
            if (href.endswith('.html') and 
                not href.startswith('package-') and 
                not href.startswith('../') and
                text and not text.startswith('All ')):
                
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
            'summary': '',
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
                if html_file.read_text(encoding='utf-8').find(class_name) != -1:
                    class_file = html_file
                    break
            else:
                raise ValueError(f"Class not found: {class_name}")
        
        parser = self._parse_html_file(class_file)
        
        # Extract methods from the content
        methods = []
        content = class_file.read_text(encoding='utf-8')
        
        # Look for method signatures using regex
        # Pattern for method names in Javadoc (simplified)
        method_pattern = re.compile(r'<a[^>]+>([a-zA-Z_]\w*)</a>\s*\([^)]*\)')
        
        for match in method_pattern.finditer(content):
            method_name = match.group(1)
            # Filter out common non-method names
            if method_name not in ['Class', 'Interface', 'Enum', 'All', 'Package']:
                methods.append({
                    'name': method_name,
                    'signature': method_name + '(...)',
                    'modifiers': '',
                    'summary': '',
                    'type': 'method'
                })
        
        # Remove duplicates
        seen = set()
        unique_methods = []
        for method in methods:
            if method['name'] not in seen:
                seen.add(method['name'])
                unique_methods.append(method)
        
        return {
            'name': class_name,
            'type': 'class',
            'summary': '',
            'methods': unique_methods
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