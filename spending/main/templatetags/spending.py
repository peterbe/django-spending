import urllib
import cgi
from django import template
from fancy_tag import fancy_tag
register = template.Library()


@fancy_tag(register, takes_context=True)
def sort_header_url(context, name, **kwargs):
    # thank you main.context_processors.current_url()
    qs = context['current_querystring']
    parsed = cgi.parse_qs(qs)
    _previous_sort = parsed.get('sort')
    parsed['sort'] = [name]
    reverse = int(parsed.get('reverse', ['0'])[0])

    if _previous_sort and _previous_sort[0] == name:
        reverse = int(not reverse)
    parsed['reverse'] = reverse
    back = urllib.urlencode(parsed, True)
    return '?%s' % back


@register.filter
def delta(value):
    if value > 0:
        return "increased "
    return "decreased "
