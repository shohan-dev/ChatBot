import httpx
from typing import Optional, Dict, List

# API Configuration
ISP_API_BASE_URL = "https://isppaybd.com/api/users"
ISP_SUBSCRIPTION_URL = "https://isppaybd.com/api/subscription_index"
ISP_MOVIE_SERVERS_URL = "https://isppaybd.com/api/movieservers"
ISP_CREATE_TICKET_URL = "https://isppaybd.com/api/create_ticket"

def fetch_user_from_api(user_id: str) -> Optional[Dict]:
    """
    Fetch user data from the ISP API.
    
    Args:
        user_id: The user ID to fetch
    
    Returns:
        Dictionary containing user information or None if not found
    """
    try:
        url = f"{ISP_API_BASE_URL}/{user_id}"
        print(f"🔍 Fetching user data from API: {url}")
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User data fetched successfully for ID: {user_id}")
            return data
        else:
            print(f"❌ API returned status {response.status_code} for user ID: {user_id}")
            return None
    except Exception as e:
        print(f"❌ Error fetching user data: {e}")
        return None

def parse_user_data(api_response: Dict) -> Dict:
    """
    Parse the API response into a user-friendly format.
    
    Field explanations:
    - subscription_status: Check if subscription is active or not
    - role: User role in the system
    - status: Account active or not
    - conn_status: Internet connection active or not (actual connectivity)
    """
    if not api_response:
        return {}
    
    details = api_response.get("details", {})
    
    return {
        "user_id": details.get("id"),
        "name": details.get("name"),
        "pppoe": api_response.get("pppoe"),
        "mobile": details.get("mobile"),
        "email": details.get("email"),
        "address": details.get("address"),
        "package_id": details.get("package_id"),
        
        # Status fields (crucial for troubleshooting)
        "subscription_status": details.get("subscription_status"),  # active/inactive - subscription validity
        "account_status": details.get("status"),  # active/inactive - account status
        "conn_status": details.get("conn_status"),  # conn/disconn - actual internet connectivity
        "role": details.get("role"),  # user role
        
        # Billing information
        "last_renewed": details.get("last_renewed"),
        "will_expire": details.get("will_expire"),
        "payment_received": api_response.get("payment_received", 0),
        "payment_pending": api_response.get("payment_pending", 0),
        "fund": details.get("fund", "0.00"),
        
        # Technical details
        "router_id": details.get("router_id"),
        "area_id": details.get("area_id"),
        "auto_disconnect": details.get("auto_disconnect"),
        "total_support_ticket": api_response.get("total_support_ticket", 0),
        
        # Statistics
        "statistics": api_response.get("statistics", {}),
        
        # Full details for reference
        "full_details": details
    }

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """
    Fetch and parse user data by ID from the API.
    
    Args:
        user_id: The user ID as string
    
    Returns:
        Parsed user dictionary or None if not found
    """
    raw_data = fetch_user_from_api(user_id)
    if raw_data:
        return parse_user_data(raw_data)
    return None

def check_internet_status(user_id: str) -> Dict:
    """
    Check internet connectivity status for troubleshooting.
    
    Flow for internet issues:
    1. Check subscription_status (is subscription active?)
    2. Check conn_status (is internet actually connected?)
    3. If issues found, recommend router restart (30 seconds)
    
    Args:
        user_id: The user ID to check
    
    Returns:
        Dictionary with status info and recommendations
    """
    print(f"🔍 Checking internet status for user ID: {user_id}")
    user_data = get_user_by_id(user_id)
    
    if not user_data:
        print(f"❌ User not found for internet check: {user_id}")
        return {
            "status": "error",
            "message": "User not found"
        }
    
    subscription_status = user_data.get("subscription_status", "").lower()
    conn_status = user_data.get("conn_status", "").lower()
    account_status = user_data.get("account_status", "").lower()
    
    issues = []
    recommendations = []
    
    # Check subscription status
    if subscription_status != "active":
        issues.append(f"Subscription is {subscription_status}")
        recommendations.append("Please renew your subscription to restore internet access")
    
    # Check account status
    if account_status != "active":
        issues.append(f"Account is {account_status}")
        recommendations.append("Please contact support to activate your account")
    
    # Check connection status
    if conn_status != "conn":
        issues.append(f"Internet connection is {conn_status}")
        recommendations.append("Try restarting your router for 30 seconds")
    
    # If subscription and account are active but connection is down
    if subscription_status == "active" and account_status == "active" and conn_status != "conn":
        recommendations.append("**Router Restart Steps:**\n1. Unplug the router power cable\n2. Wait for 30 seconds\n3. Plug the router back in\n4. Wait 2-3 minutes for it to fully boot up\n5. Check if internet is working")
    
    result = {
        "status": "success",
        "user_name": user_data.get("name"),
        "subscription_status": subscription_status,
        "account_status": account_status,
        "conn_status": conn_status,
        "payment_pending": user_data.get("payment_pending", 0),
        "will_expire": user_data.get("will_expire"),
        "issues": issues if issues else ["No issues detected"],
        "recommendations": recommendations if recommendations else ["Your internet connection appears to be working normally"]
    }
    
    print(f"✅ Internet status checked - Issues: {len(issues)}, Status: {conn_status}")
    return result

def get_subscription_packages(user_id: str) -> Dict:
    """
    Fetch user's current subscription and available packages.
    
    This shows:
    - Current package details (name, bandwidth, price)
    - All available packages for upgrade/change
    - Subscription status and expiry
    
    Args:
        user_id: The user ID to check
    
    Returns:
        Dictionary with current package, available packages, and subscription info
    """
    try:
        url = f"{ISP_SUBSCRIPTION_URL}?role=user&user_id={user_id}"
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            details = data.get("details", {})
            packages = data.get("packages", [])
            
            # Find current package
            current_package_id = details.get("package_id")
            current_package = None
            available_packages = []
            
            for pkg in packages:
                if pkg["id"] == current_package_id:
                    current_package = pkg
                else:
                    available_packages.append(pkg)
            
            return {
                "status": "success",
                "user_name": details.get("name"),
                "current_package": {
                    "name": current_package.get("package_name") if current_package else "Unknown",
                    "bandwidth": current_package.get("bandwidth") if current_package else "Unknown",
                    "price": current_package.get("price") if current_package else "0",
                    "pricing_type": current_package.get("pricing_type") if current_package else "monthly"
                },
                "subscription_status": details.get("subscription_status"),
                "will_expire": details.get("will_expire"),
                "last_renewed": details.get("last_renewed"),
                "available_packages": [
                    {
                        "name": pkg["package_name"],
                        "bandwidth": pkg["bandwidth"],
                        "price": pkg["price"],
                        "pricing_type": pkg["pricing_type"]
                    }
                    for pkg in available_packages
                    if pkg.get("status") == "active" and pkg.get("visibility") == "active"
                ]
            }
        else:
            return {
                "status": "error",
                "message": "Could not fetch subscription information"
            }
    except Exception as e:
        print(f"Error fetching subscription data: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }

def get_movie_servers(user_id: str) -> Dict:
    """
    Fetch available movie/FTP servers for the user.
    
    Shows local FTP servers and OTT platforms available to ISP users.
    
    Args:
        user_id: The user ID to check
    
    Returns:
        Dictionary with compact server list (name + url only)
    """
    try:
        url = f"{ISP_MOVIE_SERVERS_URL}?user_id={user_id}"
        print(f"🎬 Fetching movie servers from API: {url}")
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("status") == "success":
                servers = data.get("data", [])
                
                # Separate FTP and OTT servers
                ftp_servers = []
                ott_servers = []
                
                for server in servers:
                    server_info = f"{server.get('name')}: {server.get('url')}"
                    if server.get("details") == "OTT":
                        ott_servers.append(server_info)
                    else:
                        ftp_servers.append(server_info)
                
                print(f"✅ Movie servers fetched: {len(ftp_servers)} FTP, {len(ott_servers)} OTT")
                return {
                    "status": "success",
                    "total": len(servers),
                    "ftp_servers": ftp_servers,
                    "ott_servers": ott_servers
                }
            else:
                print(f"❌ No servers found for user ID: {user_id}")
                return {
                    "status": "error",
                    "message": "No servers found"
                }
        else:
            print(f"❌ API returned status {response.status_code} for movie servers")
            return {
                "status": "error",
                "message": "Could not fetch servers"
            }
    except Exception as e:
        print(f"❌ Error fetching movie servers: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }

def create_support_ticket(user_id: str, subject: str, category: str, priority: str, message: str) -> Dict:
    """
    Create a support ticket via the external ISP API.
    
    Args:
        user_id: The user ID
        subject: Ticket subject
        category: Ticket category
        priority: Ticket priority
        message: Ticket message content
        
    Returns:
        API response dictionary
    """
    try:
        # The API expects parameters in the query string or body. 
        # Based on the example: {{Base_url}}/create_ticket?user_id=...
        # We will send them as query parameters in a POST request.
        
        # Enhance message to indicate it was created by AI for this specific user
        formatted_message = f"Ticket created by AI Assistant for User {user_id}.\n\nUser Issue: {message}"
        
        params = {
            "user_id": user_id,
            "subject": subject,
            "category": category,
            "priority": priority,
            "message": formatted_message
        }
        
        print(f"🎫 Creating ticket via API: {ISP_CREATE_TICKET_URL}")
        print(f"📝 Params: {params}")
        
        response = httpx.post(ISP_CREATE_TICKET_URL, params=params, timeout=15.0)
        
        if response.status_code == 200:
            print(f"✅ Ticket created successfully for user: {user_id}")
            try:
                return response.json()
            except:
                return {"status": "success", "message": "Ticket created successfully"}
        else:
            print(f"❌ Failed to create ticket. Status: {response.status_code}")
            return {
                "status": "error", 
                "message": f"Failed to create ticket (Status: {response.status_code})"
            }
            
    except Exception as e:
        print(f"❌ Error creating ticket: {e}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }

