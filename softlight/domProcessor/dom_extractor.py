# dom_extractor.py - DOM extraction engine for hybrid system
"""
DOM extraction engine that parses HTML and extracts actionable elements.
Inspired by browser-use's approach: harvest interactive elements with semantic attributes.
"""
from typing import List, Optional
from bs4 import BeautifulSoup, Tag, NavigableString
from softlight.domProcessor.element_info import ElementInfo
from softlight.core.config.logger import setup_logger

logger = setup_logger(__name__)


class DOMExtractor:
    """
    Extracts actionable elements from HTML with semantic attributes.
    
    Strategy:
    1. Parse HTML with BeautifulSoup
    2. Find all interactive elements (buttons, inputs, links, etc.)
    3. Extract semantic attributes (ARIA, text, IDs)
    4. Generate stable selectors
    5. Rank by priority (interactive > visible > text-heavy)
    """
    
    # Elements that are typically interactive
    INTERACTIVE_TAGS = {
        "button", "input", "textarea", "select", "a", 
        "label", "option", "[role=button]", "[role=link]",
        "[role=textbox]", "[contenteditable=true]"
    }
    
    # Tags to extract text from
    TEXT_TAGS = {"button", "a", "label", "span", "div", "p", "h1", "h2", "h3", "h4", "h5", "h6"}
    
    def __init__(self, max_elements: int = 100):
        """
        Initialize DOM extractor.
        
        Args:
            max_elements: Maximum number of elements to extract (default: 100)
        """
        self.max_elements = max_elements
        self._bid_counter = 0
    
    def extract_elements(self, html: str) -> List[ElementInfo]:
        """
        Extract actionable elements from HTML.
        
        Args:
            html: Full HTML content
            
        Returns:
            List of ElementInfo objects, ranked by priority
        """
        logger.debug("Starting DOM extraction")
        self._bid_counter = 0
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            elements = []
            
            # Extract interactive elements
            for tag_name in ['button', 'input', 'textarea', 'select', 'a']:
                for element in soup.find_all(tag_name):
                    elem_info = self._extract_element_info(element, tag_name)
                    if elem_info and self._is_valid_element(elem_info):
                        elements.append(elem_info)
            
            # Extract elements with ARIA roles
            for element in soup.find_all(attrs={"role": True}):
                if element.name not in ['button', 'input', 'textarea', 'select', 'a']:
                    elem_info = self._extract_element_info(element, element.name)
                    if elem_info and self._is_valid_element(elem_info):
                        elements.append(elem_info)
            
            # Extract contenteditable elements
            for element in soup.find_all(attrs={"contenteditable": "true"}):
                elem_info = self._extract_element_info(element, element.name)
                if elem_info and self._is_valid_element(elem_info):
                    elements.append(elem_info)
            
            # Rank by priority
            elements.sort(key=lambda e: e.get_priority_score(), reverse=True)
            
            # Limit to max_elements
            elements = elements[:self.max_elements]
            
            logger.info(f"Extracted {len(elements)} actionable elements")
            return elements
            
        except Exception as e:
            logger.error(f"DOM extraction failed: {e}")
            return []
    
    def extract_page_text(self, html: str) -> str:
        """
        Extract visible text content from HTML.
        
        Args:
            html: Full HTML content
            
        Returns:
            Concatenated visible text
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator="\n", strip=True)
            
            # Clean up: remove excessive whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            # Limit length
            max_chars = 3000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            return text
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    def _extract_element_info(self, element: Tag, tag_name: str) -> Optional[ElementInfo]:
        """
        Extract information from a single element.
        
        Args:
            element: BeautifulSoup Tag
            tag_name: Tag name
            
        Returns:
            ElementInfo or None if extraction fails
        """
        try:
            # Generate unique bid
            self._bid_counter += 1
            bid = str(self._bid_counter)
            
            # Extract text content
            text = self._get_element_text(element)
            
            # Extract attributes
            attrs = element.attrs
            
            # Find nearby label (for context)
            nearby_label = self._find_nearby_label(element, attrs)
            
            # Build ElementInfo
            elem_info = ElementInfo(
                bid=bid,
                tag=tag_name,
                role=attrs.get('role'),
                text=text,
                aria_label=attrs.get('aria-label'),
                aria_describedby=attrs.get('aria-describedby'),
                placeholder=attrs.get('placeholder'),
                nearby_label=nearby_label,
                name=attrs.get('name'),
                id=attrs.get('id'),
                classes=attrs.get('class', []) if isinstance(attrs.get('class'), list) else [attrs.get('class', '')],
                data_testid=attrs.get('data-testid'),
                data_bid=attrs.get('data-bid'),
                type=attrs.get('type'),
                value=attrs.get('value'),
                href=attrs.get('href'),
                disabled=attrs.get('disabled') is not None,
                readonly=attrs.get('readonly') is not None,
                contenteditable=attrs.get('contenteditable') == 'true',
                selector=self._generate_selector(element, attrs),
            )
            
            return elem_info
            
        except Exception as e:
            logger.debug(f"Failed to extract element: {e}")
            return None
    
    def _get_element_text(self, element: Tag) -> Optional[str]:
        """
        Get visible text content from element.
        
        Args:
            element: BeautifulSoup Tag
            
        Returns:
            Text content or None
        """
        try:
            # Get direct text content (not from children)
            text = element.get_text(separator=" ", strip=True)
            
            # Limit length
            if text and len(text) > 100:
                text = text[:100] + "..."
            
            return text if text else None
            
        except:
            return None
    
    def _generate_selector(self, element: Tag, attrs: dict) -> str:
        """
        Generate a stable CSS selector for the element.
        
        Priority:
        1. ID (most stable)
        2. data-testid
        3. name attribute
        4. Combination of tag + classes
        5. Tag only (fallback)
        
        Args:
            element: BeautifulSoup Tag
            attrs: Element attributes
            
        Returns:
            CSS selector string
        """
        # Priority 1: ID
        if attrs.get('id'):
            return f"#{attrs['id']}"
        
        # Priority 2: data-testid
        if attrs.get('data-testid'):
            return f"[data-testid='{attrs['data-testid']}']"
        
        # Priority 3: name
        if attrs.get('name'):
            return f"{element.name}[name='{attrs['name']}']"
        
        # Priority 4: Tag + classes
        if attrs.get('class') and isinstance(attrs['class'], list):
            classes = '.'.join(attrs['class'][:3])  # Use first 3 classes
            return f"{element.name}.{classes}"
        
        # Priority 5: Tag + type (for inputs)
        if element.name == 'input' and attrs.get('type'):
            return f"input[type='{attrs['type']}']"
        
        # Fallback: just tag
        return element.name
    
    def _is_valid_element(self, elem_info: ElementInfo) -> bool:
        """
        Check if element is valid for extraction.
        
        Filters out:
        - Hidden elements (if we can detect)
        - Elements with no meaningful content or attributes
        
        Args:
            elem_info: ElementInfo object
            
        Returns:
            True if element is valid
        """
        # Must have at least one of: text, aria-label, placeholder, id, name
        has_identity = any([
            elem_info.text,
            elem_info.aria_label,
            elem_info.placeholder,
            elem_info.id,
            elem_info.name,
            elem_info.role,
            elem_info.data_testid,
        ])
        
        return has_identity
    
    def reset_counter(self):
        """Reset bid counter (useful for testing)"""
        self._bid_counter = 0
    
    def _find_nearby_label(self, element: Tag, attrs: dict) -> Optional[str]:
        """
        Find nearby label text to provide context for the element.
        
        This helps disambiguate similar elements (e.g., multiple contenteditable divs).
        
        Strategy:
        1. Check for <label> with matching 'for' attribute
        2. Check parent <label> element
        3. Check preceding sibling text elements (h1-h6, label, span, div with text)
        4. Check aria-labelledby reference
        5. Check parent's preceding text
        
        Args:
            element: BeautifulSoup Tag
            attrs: Element attributes
            
        Returns:
            Label text or None
        """
        try:
            # Strategy 1: <label for="id">
            if attrs.get('id'):
                # Find label with for="id"
                label = element.find_previous('label', attrs={'for': attrs['id']})
                if not label:
                    # Search forward too
                    label = element.find_next('label', attrs={'for': attrs['id']})
                if label:
                    label_text = label.get_text(strip=True)
                    if label_text:
                        return label_text
            
            # Strategy 2: Parent <label>
            parent = element.parent
            if parent and parent.name == 'label':
                # Get label text excluding the element itself
                label_text = parent.get_text(strip=True)
                elem_text = self._get_element_text(element) or ""
                label_text = label_text.replace(elem_text, "").strip()
                if label_text:
                    return label_text
            
            # Strategy 3: Preceding sibling with meaningful text
            # Look for h1-h6, label, span, div immediately before this element
            prev_sibling = element.find_previous_sibling()
            attempts = 0
            while prev_sibling and attempts < 3:  # Check up to 3 siblings back
                if prev_sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'span', 'div', 'p']:
                    sibling_text = prev_sibling.get_text(strip=True)
                    # Only use if it's short enough to be a label (not a paragraph)
                    if sibling_text and len(sibling_text) < 100:
                        return sibling_text
                prev_sibling = prev_sibling.find_previous_sibling()
                attempts += 1
            
            # Strategy 4: Check aria-labelledby
            if attrs.get('aria-labelledby'):
                labelledby_id = attrs['aria-labelledby']
                label_elem = element.find_previous(attrs={'id': labelledby_id})
                if not label_elem:
                    label_elem = element.find_next(attrs={'id': labelledby_id})
                if label_elem:
                    label_text = label_elem.get_text(strip=True)
                    if label_text:
                        return label_text
            
            # Strategy 5: Check parent's preceding sibling
            if parent:
                parent_prev = parent.find_previous_sibling()
                if parent_prev and parent_prev.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'div']:
                    parent_text = parent_prev.get_text(strip=True)
                    if parent_text and len(parent_text) < 100:
                        return parent_text
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to find nearby label: {e}")
            return None


# Convenience function
def extract_dom_state(html: str, max_elements: int = 100) -> tuple[List[ElementInfo], str]:
    """
    Extract DOM elements and page text from HTML.
    
    Args:
        html: Full HTML content
        max_elements: Maximum elements to extract
        
    Returns:
        Tuple of (elements, page_text)
    """
    extractor = DOMExtractor(max_elements=max_elements)
    elements = extractor.extract_elements(html)
    page_text = extractor.extract_page_text(html)
    return elements, page_text

