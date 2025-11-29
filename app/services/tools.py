from langchain.tools import tool
from app.db.data import get_user_by_id, check_internet_status, get_subscription_packages, get_movie_servers

@tool
def search_user_by_id(user_id: str):
    """
    Fetch user details from the ISP API by their user ID.
    
    Args:
        user_id: The user ID as a string (e.g., "10854")
    
    Returns:
        User information including subscription status, connection status, billing details, etc.
    
    Use this tool when:
    - User provides their ID
    - You need to check account status
    - You need billing information
    - User asks about their account details
    """
    result = get_user_by_id(user_id)
    if result:
        return result
    return {"error": "User not found. Please verify the user ID."}

@tool
def check_internet_connectivity(user_id: str):
    """
    Check internet connectivity status and provide troubleshooting recommendations.
    
    This tool checks:
    1. subscription_status - Is the subscription active?
    2. account_status - Is the account active?
    3. conn_status - Is the internet actually connected?
    
    Args:
        user_id: The user ID as a string (e.g., "10854")
    
    Returns:
        Detailed status information and troubleshooting steps
    
    Use this tool when:
    - User reports "internet not working"
    - User says "internet is slow" or "no connection"
    - User asks to check their connection status
    - You need to diagnose connectivity issues
    
    The tool will automatically recommend router restart (30 seconds) if needed.
    """
    return check_internet_status(user_id)

@tool
def view_packages(user_id: str):
    """
    View current subscription package and all available packages for upgrade or change.
    
    This tool shows:
    - Current package (name, speed/bandwidth, monthly price)
    - All available packages with their speeds and prices
    - Subscription expiry date
    - Package comparison for upgrades
    
    Args:
        user_id: The user ID as a string (e.g., "10854")
    
    Returns:
        Current package details and list of available packages
    
    Use this tool when:
    - User asks "what is my package?"
    - User wants to know "available packages" or "internet plans"
    - User asks "how much is my plan?"
    - User wants to "upgrade" or "change package"
    - User asks about internet speeds or pricing
    """
    return get_subscription_packages(user_id)

@tool
def view_movie_servers(user_id: str):
    """
    View available movie servers, FTP servers, and OTT platforms.
    
    This tool shows:
    - Local FTP servers for movies/content
    - OTT platforms (Bongo, Bioscope, etc.)
    - Server names, URLs, and types
    
    Args:
        user_id: The user ID as a string (e.g., "10854")
    
    Returns:
        List of available movie servers with URLs and types
    
    Use this tool when:
    - User asks about "movie servers" or "FTP"
    - User wants to know "where to watch movies"
    - User asks about "OTT platforms" or streaming services
    - User asks "what servers do you have?"
    """
    return get_movie_servers(user_id)

# List of tools to be used by the agent
isp_tools = [search_user_by_id, check_internet_connectivity, view_packages, view_movie_servers]
