import datetime
import urllib
import cgi
from django.core.urlresolvers import reverse
from django import template
from fancy_tag import fancy_tag

from spending.main.models import Category

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


@fancy_tag(register)
def compare_url(year, month, without_rent=False):
    date = datetime.date(year, month, 1)
    previous = date
    while previous.month == date.month:
        previous -= datetime.timedelta(days=1)

    categories_qs = Category.objects.all()
    if without_rent:
        categories_qs = categories_qs.exclude(name__iexact='Rent')
    categories = categories_qs.values('id')

    data = {
        'm': ','.join([previous.strftime('%m:%Y'), date.strftime('%m:%Y')]),
        'c': ','.join(str(x['id']) for x in categories),
    }
    qs = '&'.join('%s=%s' % (k, v) for (k, v) in data.items())

    return reverse('compare') + '?%s' % qs
