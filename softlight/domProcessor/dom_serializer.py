# dom_serializer.py
from bs4 import BeautifulSoup

def serialize_dom(html_content: str) -> (str, dict):
    """
    Processes HTML to create a simplified representation for the LLM and
    a mapping for Playwright to find elements.

    Returns:
        - A string of labeled elements for the LLM (e.g., "<button bid=1>...").
        - A dictionary mapping each bid to a unique CSS selector.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    interactable_elements = soup.find_all(['a', 'button', 'input', 'textarea', 'select'])

    llm_representation = []
    element_map = {}

    for i, element in enumerate(interactable_elements):
        bid = str(i + 1)  # Use 1-based indexing for clarity
        
        # --- Create a unique selector for Playwright ---
        # A more robust selector could include classes, names, etc.
        # For this, we'll use the tag name and its order on the page.
        tag = element.name
        selector = f"{tag}:nth-of-type({interactable_elements.index(element) + 1})"
        
        # Add a `data-bid` attribute so we can find it reliably
        element['data-bid'] = bid
        
        text = element.get_text(strip=True) or element.get('aria-label', '') or element.get('placeholder', '')
        
        llm_representation.append(f"<{tag} bid={bid}>{text[:100]}</{tag}>")
        element_map[bid] = f'[data-bid="{bid}"]'

    # The key is to inject these 'data-bid' attributes back into the live browser
    # We will do that with Javascript in the browser_controller
    
    return " ".join(llm_representation), soup.prettify()