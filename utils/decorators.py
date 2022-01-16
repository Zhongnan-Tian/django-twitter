from rest_framework.response import Response
from rest_framework import status
from functools import wraps


def required_params(method='GET', params=None):
    """
    When we use @required_params(params=['some_param']),
    this required_params function should return a decorator function，
    """
    if params is None:
        params = []

    # view_func is the function being decorated
    def decorator(view_func):
        """
        decorator uses wraps to parse view_func's parameters and pass them to _wrapped_view.
        The instance here is the `self` in view_function
        """
        @wraps(view_func)
        def _wrapped_view(instance, request, *args, **kwargs):
            if method.lower() == 'get':
                data = request.query_params
            else:
                data = request.data
            missing_params = [
                param
                for param in params
                if param not in data
            ]
            if missing_params:
                params_str = ','.join(missing_params)
                return Response({
                    'message': u'missing {} in request'.format(params_str),
                    'success': False,
                }, status=status.HTTP_400_BAD_REQUEST)
            # call the function being decorated, namely view_func
            return view_func(instance, request, *args, **kwargs)
        return _wrapped_view
    return decorator
