from rest_framework.permissions import BasePermission


class IsObjectOwner(BasePermission):
    """
    This Permission checks whether obj.user == request.user

    - If detail=False，run has_permission only
    - If detail=True, run has_permission and has_object_permission
    """
    # default error message when permission checks fail
    message = "You do not have permission to access this object"

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.user
