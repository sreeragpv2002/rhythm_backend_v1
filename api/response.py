"""
Standardized API response format
"""


def success_response(message="Success", data=None):
    """
    Create a standardized success response
    
    Args:
        message (str): Success message
        data: Response data (dict, list, or None)
    
    Returns:
        dict: Standardized response format
    """
    response = {
        "success": True,
        "message": message,
    }
    
    if data is not None:
        response["data"] = data
    
    return response


def error_response(message="Error", errors=None):
    """
    Create a standardized error response
    
    Args:
        message (str): Error message
        errors: Error details (dict, list, or None)
    
    Returns:
        dict: Standardized response format
    """
    response = {
        "success": False,
        "message": message,
    }
    
    if errors is not None:
        response["errors"] = errors
    
    return response
