from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """Permission check for customer role"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_customer
        )


class IsBroadcaster(permissions.BasePermission):
    """Permission check for broadcaster role"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_broadcaster
        )


class IsAdmin(permissions.BasePermission):
    """Permission check for admin role"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_admin
        )


class IsBroadcasterOrAdmin(permissions.BasePermission):
    """Permission check for broadcaster or admin role"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_broadcaster or request.user.is_admin)
        )


class IsVerifiedBroadcaster(permissions.BasePermission):
    """Permission check for verified broadcaster"""
    
    message = "You must be a verified broadcaster to perform this action."
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        if request.user.is_admin:
            return True
        
        if request.user.is_broadcaster:
            return (
                hasattr(request.user, 'broadcaster_profile') and
                request.user.broadcaster_profile.is_verified
            )
        
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission check for object owner or admin"""
    
    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.is_admin:
            return True
        
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if the object is the user itself
        return obj == request.user
