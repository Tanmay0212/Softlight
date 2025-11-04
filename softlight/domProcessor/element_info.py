# element_info.py - Element representation for hybrid DOM + Vision system
"""
ElementInfo dataclass represents an extracted DOM element with all semantic attributes.
This is the core data structure for the hybrid perception system.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ElementInfo:
    """
    Represents an actionable DOM element with semantic attributes.
    
    This structure is inspired by browser-use's element extraction approach,
    combining structural info (tag, selector) with semantic attributes (ARIA, text)
    for robust element identification.
    """
    
    # Core identification
    bid: str                           # Unique ID for this element (generated)
    tag: str                          # HTML tag name (button, input, a, etc.)
    
    # Semantic attributes (for LLM reasoning)
    role: Optional[str] = None        # ARIA role (button, textbox, link, etc.)
    text: Optional[str] = None        # Visible text content
    aria_label: Optional[str] = None  # ARIA label
    aria_describedby: Optional[str] = None  # ARIA description
    placeholder: Optional[str] = None # Placeholder text (for inputs)
    
    # Standard HTML attributes
    name: Optional[str] = None        # Name attribute (forms)
    id: Optional[str] = None          # ID attribute
    classes: List[str] = field(default_factory=list)  # CSS classes
    data_testid: Optional[str] = None # Test automation ID
    data_bid: Optional[str] = None    # Existing Softlight bid system
    
    # Element properties
    type: Optional[str] = None        # Input type (text, button, checkbox, etc.)
    value: Optional[str] = None       # Current value
    href: Optional[str] = None        # Link href
    disabled: bool = False            # Is element disabled
    readonly: bool = False            # Is element readonly
    contenteditable: bool = False     # Is contenteditable
    
    # Interaction metadata
    is_interactive: bool = True       # Is element clickable/focusable
    is_visible: bool = True           # Is element visible
    
    # Selectors (for execution)
    selector: str = ""                # Generated stable selector
    xpath: Optional[str] = None       # XPath selector (optional)
    
    # Visual metadata (optional)
    bbox: Optional[Dict[str, float]] = None  # Bounding box {x, y, width, height}
    
    def to_compact_string(self) -> str:
        """
        Generate compact string representation for LLM prompt.
        Format: [bid] tag "text" (key_attributes)
        
        Example:
        [5] button "Search" (aria-label="Search button")
        [7] input[type=text] placeholder="Enter query" (name="q")
        """
        parts = [f"[{self.bid}]", self.tag]
        
        # Add type for inputs
        if self.type:
            parts[-1] = f"{self.tag}[type={self.type}]"
        
        # Add text content
        if self.text:
            text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
            parts.append(f'"{text_preview}"')
        
        # Collect key attributes
        attrs = []
        if self.aria_label:
            attrs.append(f'aria-label="{self.aria_label}"')
        if self.placeholder:
            attrs.append(f'placeholder="{self.placeholder}"')
        if self.name:
            attrs.append(f'name="{self.name}"')
        if self.id:
            attrs.append(f'id="{self.id}"')
        if self.href:
            attrs.append(f'href="{self.href[:30]}"')
        if self.data_testid:
            attrs.append(f'data-testid="{self.data_testid}"')
        if self.disabled:
            attrs.append("disabled")
        if self.readonly:
            attrs.append("readonly")
        
        if attrs:
            parts.append(f"({', '.join(attrs)})")
        
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "bid": self.bid,
            "tag": self.tag,
            "role": self.role,
            "text": self.text,
            "aria_label": self.aria_label,
            "placeholder": self.placeholder,
            "name": self.name,
            "id": self.id,
            "classes": self.classes,
            "selector": self.selector,
            "is_interactive": self.is_interactive,
            "type": self.type,
            "href": self.href,
        }
    
    def get_priority_score(self) -> int:
        """
        Calculate priority score for element ranking.
        Higher score = more likely to be relevant for automation.
        
        Priority factors:
        - Interactive elements (buttons, inputs, links) = higher
        - Elements with text/labels = higher
        - Disabled/hidden elements = lower
        """
        score = 0
        
        # Base score by tag type
        interactive_tags = {"button", "input", "textarea", "select", "a"}
        if self.tag in interactive_tags:
            score += 50
        
        # Boost for ARIA role
        if self.role:
            score += 20
        
        # Boost for text content
        if self.text:
            score += 15
        
        # Boost for labels
        if self.aria_label:
            score += 15
        if self.placeholder:
            score += 10
        
        # Boost for IDs (easier to target)
        if self.id:
            score += 10
        if self.name:
            score += 10
        if self.data_testid:
            score += 10
        
        # Penalty for disabled/hidden
        if self.disabled:
            score -= 30
        if not self.is_visible:
            score -= 50
        
        return score

