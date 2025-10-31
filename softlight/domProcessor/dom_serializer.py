# dom_serializer.py
from bs4 import BeautifulSoup

def serialize_dom(html_content: str) -> (str, str):
    """
    Processes HTML to create a simplified representation for the LLM and
    inject data-bid attributes for element identification.

    Returns:
        - A string of labeled elements for the LLM (e.g., "<button bid=1>...").
        - Updated HTML with data-bid attributes injected.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all interactive elements - expanded list for better coverage
    interactable_elements = soup.find_all([
        'a', 'button', 'input', 'textarea', 'select',
        'label',  # Form labels (often clickable)
    ])
    
    # Also find elements with interactive attributes
    elements_with_onclick = soup.find_all(attrs={"onclick": True})
    elements_with_role_button = soup.find_all(attrs={"role": "button"})
    elements_with_role_link = soup.find_all(attrs={"role": "link"})
    elements_with_role_tab = soup.find_all(attrs={"role": "tab"})
    elements_with_role_menuitem = soup.find_all(attrs={"role": "menuitem"})
    elements_with_role_textbox = soup.find_all(attrs={"role": "textbox"})  # For contenteditable divs
    elements_contenteditable = soup.find_all(attrs={"contenteditable": "true"})  # Direct contenteditable
    
    # Combine all interactive elements and remove duplicates
    all_interactable = list(set(
        interactable_elements + 
        elements_with_onclick + 
        elements_with_role_button + 
        elements_with_role_link +
        elements_with_role_tab +
        elements_with_role_menuitem +
        elements_with_role_textbox +
        elements_contenteditable
    ))

    llm_representation = []

    for i, element in enumerate(all_interactable):
        bid = str(i + 1)  # Use 1-based indexing for clarity
        
        # Add a `data-bid` attribute so we can find it reliably
        element['data-bid'] = bid
        
        tag = element.name
        
        # Get element text and attributes for better context
        text = element.get_text(strip=True)[:100]  # Limit to 100 chars
        element_type = element.get('type', '')
        placeholder = element.get('placeholder', '')
        aria_label = element.get('aria-label', '')
        name = element.get('name', '')
        value = element.get('value', '')
        role = element.get('role', '')
        contenteditable = element.get('contenteditable', '')
        
        # Build a more descriptive representation
        attrs = []
        if element_type:
            attrs.append(f'type="{element_type}"')
        if placeholder:
            attrs.append(f'placeholder="{placeholder}"')
        if aria_label:
            attrs.append(f'aria-label="{aria_label}"')
        if name:
            attrs.append(f'name="{name}"')
        if value and element_type != 'password':  # Don't include password values
            attrs.append(f'value="{value[:50]}"')
        if role:
            attrs.append(f'role="{role}"')
        if contenteditable == 'true':
            attrs.append(f'contenteditable="true"')
        
        attrs_str = ' ' + ' '.join(attrs) if attrs else ''
        llm_representation.append(f"<{tag} bid={bid}{attrs_str}>{text}</{tag}>")

    # Return the LLM representation and the updated HTML with data-bid attributes
    return "\n".join(llm_representation), soup.prettify()