"""Javadoc HTML parser and data extractor."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup


class JavadocParser:
    """Parser for extracting information from Javadoc HTML files."""
    
    def __init__(self, base_path: str, version: str = "LATEST"):
        """Initialize the parser with a base path and version.
        
        Args:
            base_path: Base path to the javadoc directory
            version: Version string (e.g., "LATEST", "6u3", "5u25")
        """
        self.base_path = Path(base_path)
        self.version = version
        self.javadoc_path = self.base_path / "docs" / version / "javadoc"
        
        if not self.javadoc_path.exists():
            raise ValueError(f"Javadoc path does not exist: {self.javadoc_path}")
        
        # Detect Javadoc version (old frame-based vs new)
        self.is_modern = (self.javadoc_path / "allpackages-index.html").exists()
    
    def get_all_packages(self) -> List[Dict[str, str]]:
        """Get a list of all packages with their names and summaries.
        
        Returns:
            List of dicts containing 'name' and 'summary' for each package
        """
        packages = []
        
        if self.is_modern:
            # Modern Javadoc structure
            packages_file = self.javadoc_path / "allpackages-index.html"
            if packages_file.exists():
                soup = BeautifulSoup(packages_file.read_text(encoding='utf-8'), 'html.parser')
                
                # Find all package entries
                for row in soup.select('div.summary-table div.col-first'):
                    link = row.find('a')
                    if link:
                        package_name = link.text.strip()
                        # Get summary from next sibling
                        summary_div = row.find_next_sibling('div', class_='col-last')
                        summary = summary_div.text.strip() if summary_div else ""
                        
                        packages.append({
                            'name': package_name,
                            'summary': summary
                        })
        else:
            # Old frame-based Javadoc
            overview_file = self.javadoc_path / "overview-frame.html"
            if overview_file.exists():
                soup = BeautifulSoup(overview_file.read_text(encoding='utf-8'), 'html.parser')
                
                # Find all package links
                for link in soup.select('a[target="packageFrame"]'):
                    package_name = link.text.strip()
                    # For old version, we need to parse package-summary.html for summaries
                    summary = self._get_package_summary_old(package_name)
                    
                    packages.append({
                        'name': package_name,
                        'summary': summary
                    })
        
        return sorted(packages, key=lambda x: x['name'])
    
    def _get_package_summary_old(self, package_name: str) -> str:
        """Get package summary for old Javadoc format."""
        package_path = package_name.replace('.', '/')
        summary_file = self.javadoc_path / package_path / "package-summary.html"
        
        if summary_file.exists():
            soup = BeautifulSoup(summary_file.read_text(encoding='utf-8'), 'html.parser')
            # Look for package description
            desc = soup.find('div', class_='block')
            if desc:
                return desc.text.strip()
        
        return ""
    
    def get_package_info(self, package_name: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get detailed information about a package including its classes.
        
        Args:
            package_name: Full package name (e.g., "nablarch.core.db")
            
        Returns:
            Dict containing 'name', 'summary', and 'classes' list
        """
        package_path = package_name.replace('.', '/')
        summary_file = self.javadoc_path / package_path / "package-summary.html"
        
        if not summary_file.exists():
            raise ValueError(f"Package not found: {package_name}")
        
        soup = BeautifulSoup(summary_file.read_text(encoding='utf-8'), 'html.parser')
        
        # Get package summary
        summary = ""
        if self.is_modern:
            desc_div = soup.find('section', class_='package-description')
            if desc_div:
                block = desc_div.find('div', class_='block')
                if block:
                    summary = block.text.strip()
        else:
            desc_div = soup.find('div', class_='block')
            if desc_div:
                summary = desc_div.text.strip()
        
        # Get classes
        classes = []
        
        # Find interfaces
        interfaces = self._extract_type_info(soup, 'Interface')
        classes.extend(interfaces)
        
        # Find classes
        class_info = self._extract_type_info(soup, 'Class')
        classes.extend(class_info)
        
        # Find enums
        enums = self._extract_type_info(soup, 'Enum')
        classes.extend(enums)
        
        # Find exceptions
        exceptions = self._extract_type_info(soup, 'Exception')
        classes.extend(exceptions)
        
        # Find errors
        errors = self._extract_type_info(soup, 'Error')
        classes.extend(errors)
        
        # Find annotations
        annotations = self._extract_type_info(soup, 'Annotation Type')
        classes.extend(annotations)
        
        return {
            'name': package_name,
            'summary': summary,
            'classes': sorted(classes, key=lambda x: x['name'])
        }
    
    def _extract_type_info(self, soup: BeautifulSoup, type_name: str) -> List[Dict[str, str]]:
        """Extract information about specific types (classes, interfaces, etc.)."""
        items = []
        
        if self.is_modern:
            # Look for section with the type name
            for section in soup.find_all('section'):
                h2 = section.find('h2')
                if h2 and type_name in h2.text:
                    table = section.find('div', class_='summary-table')
                    if table:
                        for row in table.select('div.col-first'):
                            link = row.find('a')
                            if link:
                                name = link.text.strip()
                                summary_div = row.find_next_sibling('div', class_='col-last')
                                summary = summary_div.text.strip() if summary_div else ""
                                
                                items.append({
                                    'name': name,
                                    'type': type_name.lower(),
                                    'summary': summary
                                })
        else:
            # Old format uses tables
            for table in soup.find_all('table'):
                caption = table.find('caption')
                if caption and type_name in caption.text:
                    for row in table.select('tr.rowColor, tr.altColor'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            link = cells[0].find('a')
                            if link:
                                name = link.text.strip()
                                summary = cells[1].text.strip()
                                
                                items.append({
                                    'name': name,
                                    'type': type_name.lower(),
                                    'summary': summary
                                })
        
        return items
    
    def get_class_info(self, class_name: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get detailed information about a class including its methods.
        
        Args:
            class_name: Full class name (e.g., "nablarch.core.db.DbAccessException")
            
        Returns:
            Dict containing 'name', 'summary', 'type', and 'methods' list
        """
        # Find the class HTML file
        class_file = None
        for html_file in self.javadoc_path.rglob("*.html"):
            if html_file.name == f"{class_name.split('.')[-1]}.html":
                # Verify it's the correct class by checking the content
                content = html_file.read_text(encoding='utf-8')
                if class_name in content:
                    class_file = html_file
                    break
        
        if not class_file:
            raise ValueError(f"Class not found: {class_name}")
        
        soup = BeautifulSoup(class_file.read_text(encoding='utf-8'), 'html.parser')
        
        # Determine type (class, interface, enum, etc.)
        type_info = "class"
        title = soup.find('h2', class_='title') or soup.find('h1', class_='title')
        if title:
            title_text = title.text.lower()
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
        
        # Get class summary
        summary = ""
        if self.is_modern:
            desc_section = soup.find('section', class_='class-description')
            if desc_section:
                block = desc_section.find('div', class_='block')
                if block:
                    summary = block.text.strip()
        else:
            desc_div = soup.find('div', class_='block')
            if desc_div and desc_div.parent.get('class') == ['description']:
                summary = desc_div.text.strip()
        
        # Get methods
        methods = []
        
        # Extract constructors
        constructors = self._extract_member_info(soup, 'Constructor')
        for c in constructors:
            c['type'] = 'constructor'
        methods.extend(constructors)
        
        # Extract methods
        method_info = self._extract_member_info(soup, 'Method')
        for m in method_info:
            m['type'] = 'method'
        methods.extend(method_info)
        
        return {
            'name': class_name,
            'type': type_info,
            'summary': summary,
            'methods': methods
        }
    
    def _extract_member_info(self, soup: BeautifulSoup, member_type: str) -> List[Dict[str, str]]:
        """Extract information about class members (methods, constructors)."""
        members = []
        
        if self.is_modern:
            # Look for method summary section
            for section in soup.find_all('section'):
                h2 = section.find('h2')
                if h2 and f"{member_type} Summary" in h2.text:
                    table = section.find('div', class_='summary-table')
                    if table:
                        for row_set in table.find_all('div', class_='summary-table-row'):
                            # Modern format groups method info in sets of 3 divs
                            divs = row_set.find_all('div', recursive=False)
                            if len(divs) >= 3:
                                # First div: modifiers and return type
                                modifiers = divs[0].text.strip()
                                
                                # Second div: method name and parameters
                                method_div = divs[1]
                                link = method_div.find('a')
                                if link:
                                    name = link.text.strip()
                                    # Get full signature
                                    signature = method_div.text.strip()
                                    
                                    # Third div: description
                                    desc = divs[2].text.strip()
                                    
                                    members.append({
                                        'name': name,
                                        'signature': signature,
                                        'modifiers': modifiers,
                                        'summary': desc
                                    })
        else:
            # Old format
            for table in soup.find_all('table'):
                summary = table.find('th', class_='colFirst')
                if summary and f"{member_type} Summary" in summary.text:
                    for row in table.select('tr.rowColor, tr.altColor'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            # First cell: modifiers and return type
                            modifiers = cells[0].text.strip()
                            
                            # Second cell: method signature and description
                            method_cell = cells[1]
                            code = method_cell.find('code')
                            if code:
                                # Extract method name
                                link = code.find('a')
                                if link:
                                    name = link.text.strip()
                                    signature = code.text.strip()
                                    
                                    # Get description (text after code)
                                    desc = ""
                                    next_node = code.next_sibling
                                    while next_node:
                                        if hasattr(next_node, 'text'):
                                            desc += next_node.text
                                        else:
                                            desc += str(next_node)
                                        next_node = next_node.next_sibling
                                    
                                    members.append({
                                        'name': name,
                                        'signature': signature,
                                        'modifiers': modifiers,
                                        'summary': desc.strip()
                                    })
        
        return members
    
    def search_by_keyword(self, keyword: str) -> Dict[str, List[Dict[str, str]]]:
        """Search for classes and methods by keyword.
        
        Args:
            keyword: Search keyword
            
        Returns:
            Dict with 'classes' and 'methods' lists containing matching items
        """
        keyword_lower = keyword.lower()
        results = {'classes': [], 'methods': []}
        
        if self.is_modern:
            # Use search indices for modern Javadoc
            
            # Search in type index
            type_index_file = self.javadoc_path / "type-search-index.js"
            if type_index_file.exists():
                content = type_index_file.read_text(encoding='utf-8')
                # Extract JSON data from JavaScript
                match = re.search(r'typeSearchIndex\s*=\s*(\[.*?\]);', content, re.DOTALL)
                if match:
                    try:
                        type_data = json.loads(match.group(1))
                        for item in type_data:
                            if keyword_lower in item.get('l', '').lower():
                                results['classes'].append({
                                    'name': item.get('l', ''),
                                    'package': item.get('p', ''),
                                    'type': item.get('c', 'class').lower()
                                })
                    except json.JSONDecodeError:
                        pass
            
            # Search in member index
            member_index_file = self.javadoc_path / "member-search-index.js"
            if member_index_file.exists():
                content = member_index_file.read_text(encoding='utf-8')
                match = re.search(r'memberSearchIndex\s*=\s*(\[.*?\]);', content, re.DOTALL)
                if match:
                    try:
                        member_data = json.loads(match.group(1))
                        for item in member_data:
                            if keyword_lower in item.get('l', '').lower():
                                results['methods'].append({
                                    'name': item.get('l', ''),
                                    'class': item.get('p', ''),
                                    'type': 'method'
                                })
                    except json.JSONDecodeError:
                        pass
        else:
            # For old Javadoc, use index-all.html
            index_file = self.javadoc_path / "index-all.html"
            if index_file.exists():
                soup = BeautifulSoup(index_file.read_text(encoding='utf-8'), 'html.parser')
                
                for dt in soup.find_all('dt'):
                    link = dt.find('a')
                    if link and keyword_lower in link.text.lower():
                        text = dt.text.strip()
                        
                        # Determine if it's a class or method
                        if ' - Class in ' in text or ' - Interface in ' in text or ' - Enum in ' in text:
                            # It's a type
                            type_match = re.search(r' - (\w+) in (.+)$', text)
                            if type_match:
                                results['classes'].append({
                                    'name': link.text.strip(),
                                    'type': type_match.group(1).lower(),
                                    'package': type_match.group(2).strip()
                                })
                        elif ' - Method in ' in text or ' - Constructor ' in text:
                            # It's a method
                            class_match = re.search(r' - \w+ in (?:class|interface|enum) (.+)$', text)
                            if class_match:
                                results['methods'].append({
                                    'name': link.text.strip().split('(')[0],
                                    'class': class_match.group(1).strip(),
                                    'type': 'constructor' if 'Constructor' in text else 'method'
                                })
        
        # Remove duplicates
        results['classes'] = list({(c['name'], c.get('package', '')): c for c in results['classes']}.values())
        results['methods'] = list({(m['name'], m.get('class', '')): m for m in results['methods']}.values())
        
        return results