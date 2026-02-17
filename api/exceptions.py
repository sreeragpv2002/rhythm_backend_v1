from rest_framework.views import exception_handler
from rest_framework import status
from .response import error_response


def custom_exception_handler(exc, context):
    """Custom exception handler for DRF"""
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response_data = error_response(
            message=str(exc),
            errors=response.data if isinstance(response.data, dict) else {'detail': response.data}
        )
        response.data = custom_response_data
    
    return response
