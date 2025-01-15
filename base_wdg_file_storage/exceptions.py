from rest_framework.views import exception_handler
from rest_framework import status
from base.utils.util import get_relationship_field


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if 'request' in context and hasattr(context.get('view'), 'model'):
                        fields = get_relationship_field(context.get('view').model)
                        for field in fields:
                            if field.name == key:
                                if value[0] and value[0].code == 'invalid':
                                    response.data[key] = value
                                else:
                                    response.data[key] = 'This field is required.'
        error = {}
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error['form_errors'] = response.data
        else:
            error['errors'] = response.data
        response.data = {"error": error}

    return response
