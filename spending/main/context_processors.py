def current_url(request):
    return {
        'current_url': request.path,
        'current_querystring': request.META.get('QUERY_STRING'),
    }
