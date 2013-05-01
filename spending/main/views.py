import re
import os
import stat
import json
import datetime
import locale
import time
import random
import urllib
from decimal import Decimal
from collections import defaultdict
from pprint import pprint
from django import http
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from django.contrib import messages
from django.db.models import Sum
from django.template.loader import get_template
from django.template import Context
from django.contrib.auth.decorators import login_required
from django.utils.timezone import utc
from django.views.decorators.http import require_POST
from django.template.defaultfilters import slugify
from django.contrib.auth.views import login
from django.middleware.csrf import get_token

from . import forms
from .models import Expense, Category
from .utils import json_view


locale.setlocale(locale.LC_ALL, '')


def dollars(amount):
    return '$' + locale.format('%.2f', amount, True)


@csrf_exempt
@transaction.commit_on_success
def home(request, template_name='home.html', data=None, form_class=forms.ExpenseForm):
    data = data or {}
    if request.method == 'POST':
        form = form_class(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            category_value = data['category']
            if category_value == '_other':
                category_value = data['other_category']
            try:
                category = Category.objects.get(name__istartswith=category_value)
            except Category.DoesNotExist:
                category = Category.objects.create(name=category_value)
            expense = Expense.objects.create(
                category=category,
                amount=data['amount'],
                user=request.user,
                date=data['date'],
                notes=data['notes'].strip()
            )
            today = datetime.datetime.utcnow()
            data = {
                'success_message': '$%.2f for %s added' % (expense.amount, expense.category.name),
                'todays_date': today.strftime('%Y-%m-%d'),
            }
        else:
            data = {'errors': form.errors}
        return http.HttpResponse(
            json.dumps(data),
            mimetype="application/json"
        )

    else:
        initial = {}
        form = bootstrapform(forms.ExpenseForm(initial=initial))
    data['form'] = form

    data['category_names'] = _category_names()
    return render(request, template_name, data)


@csrf_exempt
@transaction.commit_on_success
def mobile(request):
    data = {
        'today': datetime.datetime.utcnow(),
    }
    return home(
        request,
        template_name='mobile.html',
        data=data,
        form_class=forms.MobileExpenseForm
    )


def _category_names(exclude=None):
    qs = Category.objects.all()
    if exclude:
        qs = qs.exclude(pk=exclude.pk)
    category_names = [x.name for x in qs.order_by('name')]
    return json.dumps(category_names)


def bootstrapform(form):
    template = get_template("bootstrapform/form.html")
    context = Context({'form': form})
    return template.render(context)


@login_required
def categories_json(request):
    qs = Category.objects.all()
    result = {
        'categories': []
    }
    for each in qs.order_by('name'):
        result['categories'].append(each.name)
    return http.HttpResponse(json.dumps(result), mimetype="application/json")


MONTH_NAMES = [
    datetime.datetime(2013, x, 1).strftime('%B')
    for x in range(1, 13)
]
FULL_MONTH_REGEX = re.compile('(%s) (\d{4})' % '|'.join(MONTH_NAMES))

@login_required
def expenses(request):
    _now = datetime.datetime.utcnow()
    historic = 'category' in request.GET
    if request.GET.get('month') and FULL_MONTH_REGEX.findall(request.GET.get('month')):
        month, year = FULL_MONTH_REGEX.findall(request.GET.get('month'))[0]
        year = int(year)
        month = MONTH_NAMES.index(month) + 1
        print request.META.get('QUERY_STRING')
        new_qs = {
            'month': month,
            'year': year,
        }
        if request.GET.get('category'):
            new_qs['category'] = request.GET.get('category')
        return redirect(reverse('expenses') + '?' + urllib.urlencode(new_qs))
    month = int(request.GET.get('month', _now.month))
    year = int(request.GET.get('year', _now.year))
    if 'month' in request.GET and 'year' in request.GET:
        historic = True

    first = datetime.datetime(year, month, 1, 0, 0, 0)

    if request.GET.get('category'):
        if request.GET.get('category').isdigit():
            category = Category.objects.get(pk=request.GET['category'])
        else:
            category = Category.objects.get(name__iexact=request.GET['category'])
    else:
        category = None

    data = {
        'first': first,
        'poll': not historic,
        'category': category,
        'month': month,
        'year': year,
    }
    return render(request, 'expenses.html', data)


@login_required
def expenses_json(request):
    qs = Expense.objects.all().select_related()
    rows = []

    date_format = '%A %d'
    _now = datetime.datetime.utcnow()
    month = int(request.GET.get('month', _now.month))
    year = int(request.GET.get('year', _now.year))

    # only do this if no category is specified or if a year and month is set
    if ('month' in request.GET and 'year' in request.GET) or not request.GET.get('category'):
        #first = datetime.datetime(year, month, 1, 0, 0, 0)
        #if month == 12:
        #    next = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
        #else:
        #    next = datetime.datetime(year, month + 1, 1, 0, 0, 0)
        #qs = qs.filter(date__gte=first, date__lt=next)
        qs = qs.filter(date__month=month, date__year=year)

    if request.GET.get('category'):
        if request.GET.get('category').isdigit():
            category = Category.objects.get(pk=request.GET['category'])
        else:
            category = Category.objects.get(name__iexact=request.GET['category'])
        qs = qs.filter(category=category)
        date_format = '%A %d %b %Y'

    if request.GET.get('latest'):
        latest = datetime.datetime.strptime(
            request.GET['latest'],
            '%Y-%m-%d %H:%M:%S'
        )
        latest = latest.replace(tzinfo=utc)
        # to avoid microseconds difference
        latest += datetime.timedelta(seconds=1)
        qs = qs.filter(added__gt=latest)
    else:
        latest = None
    if request.GET.get('sort'):
        sort = request.GET.get('sort')
        if sort == 'category':
            sort = 'category__name'

        if int(request.GET.get('reverse', 0)):
            sort = '-%s' % sort
    else:
        sort = 'date'

    for x in qs.values('added').order_by('-added')[:1]:
        latest = x['added']

    for expense in qs.order_by(sort):
        rows.append({
            'pk': expense.pk,
            'amount_string': dollars(expense.amount),
            'amount': round(float(expense.amount), 2),
            'user': expense.user.first_name or expense.user.username,
            'date': expense.date.strftime(date_format),
            'category': expense.category.name,
            'category_id': expense.category.pk,
            'notes': expense.notes
        })

    if latest:
        latest = latest.strftime('%Y-%m-%d %H:%M:%S')
    result = {
        'latest': latest,
        'rows': rows
    }
    return http.HttpResponse(json.dumps(result), mimetype="application/json")


@login_required
def edit_expense(request, pk):
    data = {}
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = forms.ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            data = form.cleaned_data
            try:
                category = Category.objects.get(name__istartswith=data['category'])
            except Category.DoesNotExist:
                category = Category.objects.create(name=data['category'])
            expense.category = category
            expense.amount = data['amount']
            expense.date = data['date']
            expense.notes = data['notes'].strip()
            expense.save()

            msg = (
                '%s for %s edited' %
                (dollars(expense.amount), expense.category.name)
            )
            data = {
                'success_message': msg,
                'amount': '%.2f' % expense.amount,
                'category': expense.category.name,
            }
        else:
            data = {
                'errors': form.errors,
            }
        data['was_edit'] = True
        return http.HttpResponse(
            json.dumps(data),
            mimetype="application/json"
        )


    else:
        initial = {'category': expense.category.name}
        form = forms.ExpenseForm(instance=expense, initial=initial)

    data['form'] = bootstrapform(form)
    data['expense'] = expense
    data['category_names'] = _category_names()

    return render(request, 'edit.html', data)


@login_required
@require_POST
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    messages.add_message(
        request,
        messages.INFO,
        '$%.2f for %s deleted' % (expense.amount, expense.category.name)
    )
    expense.delete()
    return redirect(reverse('expenses'))


@login_required
def charts(request):
    data = {}
    return render(request, 'charts.html', data)


@login_required
def charts_timeline(request):
    first, = Expense.objects.all().order_by('date')[:1]
    last, = Expense.objects.all().order_by('-date')[:1]
    first = first.date
    last = last.date

    def get_series(date, interval):

#        date = first

        points = defaultdict(list)
        cum_points = defaultdict(int)
        categories = [(x.pk, x.name) for x in
                      Category.objects.all()]
        _categories = dict(categories)

        while date < last:
            next = date
            if interval:
                next = date + interval
            else:
                # monthly increment
                while next.month == date.month:
                    next += datetime.timedelta(days=1)
            counts = defaultdict(int)
            for expense in (Expense.objects
                         .filter(date__gte=date,
                                 date__lt=next)):
                counts[expense.category_id] += float(expense.amount)

            for category_id, name in categories:
                count = counts[category_id]
                points[name].append((date, count))
            date = next

        colors = ColorPump()
        series = []

        def make_ts(d):
            return int(time.mktime(d.timetuple()))

        _totals = {}
        _colors = set()
        for name, data in points.iteritems():
            _totals[name] = sum(x[1] for x in data)
            color = _get_next_color(name, colors, _colors)
            _colors.add(color)
            series.append({
              'color': color,
              'name': name,
              'data': [{'x': int(time.mktime(a.timetuple())), 'y': b} for (a, b) in data],
            })

        series.sort(
            lambda x, y: cmp(_totals[x['name']], _totals[y['name']]),
            reverse=True
        )

        rest = series[5:]
        series = series[:5]
        # let's merge the rest into one

        first = rest[0]
        data = []
        for each in first['data']:
            T = 0
            for other in rest:
                T += sum(items['y'] for items in other['data']
                        if items['x'] == each['x'])
            data.append({'x': each['x'], 'y': T})

        series.append({
            'color': _get_next_color('All Other', colors, _colors),
            'name': 'ALL OTHER',
            'data': data
        })

        return series

    #interval = datetime.timedelta(days=7)
    interval = None
    data = {'data': get_series(first, interval)}

    return http.HttpResponse(json.dumps(data), mimetype="application/json")

def _get_next_color(name, colorpump, used_colors):
    cache_key = 'timeline-%s' % slugify(name)
    color = cache.get(cache_key)
    if color is None:
        color = colorpump.next()
        while color in used_colors:
            color = colorpump.next()
        cache.set(cache_key, color, 60 * 60)
    return color


class ColorPump(object):
    _colors = (
        '#5C8D87,#994499,#6633CC,#B08B59,#DD4477,#22AA99,'
        '#668CB3,#DD5511,#D6AE00,#668CD9,#3640AD,'
        '#ff5800,#0085cc,#c747a3,#26B4E3,#bd70c7,#cddf54,#FBD178'
        .split(',')
    )
    def __init__(self):
        self.colors = iter(self._colors)

    def next(self):
        try:
            return self.colors.next()
        except StopIteration:
            return "#%s" % "".join([hex(random.randrange(0, 255))[2:]
                                    for i in range(3)])


@login_required
def calendar(request):
    months = []
    month = None
    qs = Expense.objects.all()
    qs = qs.order_by('date')
    qs = qs.values_list('amount', 'date', 'category_id')
    rent = Category.objects.get(name__iexact='Rent')
    bucket = {}
    last_date = None
    for amount, date, category_id in qs:
        print date
        if date.strftime('%B %Y') != month:
            month = date.strftime('%B %Y')
            # new month
            if bucket:
                if months:
                    last = months[-1]
                    bucket['amount_rent_diff'] = (
                        bucket['amount_rent'] - last['amount_rent']
                    )
                    bucket['amount_diff'] = (
                        bucket['amount'] - last['amount']
                    )
                months.append(bucket)
            bucket = {
                'date': month,
                'year': date.year,
                'month': date.month,
                'amount': Decimal('0.0'),
                'amount_rent': Decimal('0.0'),
            }
        if category_id == rent.pk:
            bucket['amount_rent'] += amount
        else:
            bucket['amount'] += amount
        last_date = date

    if bucket:

        # over the last 90 days, how much do we spend per month?
        DAYS_BACK_PROJECTION = 60  # 90 instead??
        now = datetime.datetime.utcnow()
        then = now - datetime.timedelta(days=DAYS_BACK_PROJECTION)

        if Expense.objects.filter(date__lt=then).count():
            _query = (
                Expense.objects
                .filter(date__gte=then)
                .exclude(category=rent)
            )
            total_past = _query.aggregate(Sum('amount'))['amount__sum']
            per_day = total_past / DAYS_BACK_PROJECTION
            days_left = 0
            while last_date.month == bucket['month']:
                days_left += 1
                last_date += datetime.timedelta(days=1)
            days_left -= 1  # so it doesn't include the first of next month

            remaining = per_day * days_left
            bucket['amount_projected'] = bucket['amount'] + remaining
            # for the amount_total_projected, do the same but include the
            # rent (of last month) if it hasn't already been paid
            bucket['amount_total_projected'] = bucket['amount_projected']
            rents_this_month = (
                Expense.objects
                .filter(date__month=bucket['month'],
                        date__year=bucket['year'],
                        category=rent)
            )
            if not rents_this_month.count():
                last_month, last_year = bucket['month'], bucket['year']
                if last_month == 1:
                    last_month = 12
                    last_year -= 1
                else:
                    last_month -= 1

                rents_last_month = (
                    Expense.objects
                    .filter(date__month=last_month,
                            date__year=last_year,
                            category=rent)
                )
                bucket['amount_total_projected'] += (
                    rents_last_month.aggregate(Sum('amount'))['amount__sum']
                )

        months.append(bucket)

    total = total_rent = Decimal('0.0')

    for each in months:
        each['amount_str'] = dollars(each['amount'])
        total += each['amount']
        each['amount_rent_str'] = dollars(each['amount_rent'])
        total_rent += each['amount_rent']
        each['amount_total_str'] = dollars(
            each['amount_rent'] + each['amount']
        )
        if 'amount_rent_diff' in each and 'amount_diff' in each:
            each['amount_rent_diff_str'] = dollars(each['amount_rent_diff'])
            each['amount_diff_str'] = dollars(each['amount_diff'])
            each['amount_total_diff'] = (
                each['amount_diff'] + each['amount_rent_diff']
            )
            each['amount_total_diff_str'] = dollars(each['amount_total_diff'])

        if 'amount_projected' in each:
            each['amount_projected_str'] = dollars(each['amount_projected'])
        else:
            each['amount_projected_str'] = None

        if 'amount_total_projected' in each:
            each['amount_total_projected_str'] = dollars(each['amount_total_projected'])
        else:
            each['amount_total_projected_str'] = None

    data = {
        'months': months,
    }

    data.update({
        'total_str': dollars(total),
        'total_rent_str': dollars(total_rent),
        'total_total_str': dollars(total_rent + total),
    })
    #series = []
    w_rent = []
    wo_rent = []
    total = []
    for i, month in enumerate(months):
        w_rent.append({
            'x': i,
            'y': float(month['amount_rent']),
        })
        wo_rent.append({
            'x': i,
            'y': float(month['amount']),
        })
        total.append({
            'x': i,
            'y': float(month['amount'] + month['amount_rent'])
        })


    data['series'] = [
		{
			'data': w_rent,
			'color': '#4682b4',
            'name': 'Rent',
		}, {
			'data': wo_rent,
			'color': '#9cc1e0',
            'name': 'Without rent',
        }, {
            'data': total,
            'color': "#6060c0",
            'name': "Total",
	} ]
    data['series'] = json.dumps(data['series'])
    return render(request, 'calendar.html', data)


@login_required
def categories(request):
    all = []
    for category in Category.objects.all().order_by('name'):
        qs = Expense.objects.filter(category=category)
        category.total = qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        category.total_str = dollars(category.total)
        category.count = qs.count()
        all.append(category)

    reverse = int(request.GET.get('reverse', 0))
    if request.GET.get('sort') == 'count':
        all.sort(key=lambda x: x.count)
    elif request.GET.get('sort') == 'total':
        all.sort(key=lambda x: x.total)
    if reverse:
        all.reverse()
    data = {
        'categories': all,
    }
    return render(request, 'categories.html', data)


@login_required
def category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    qs = Expense.objects.filter(category=category)
    total = qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    data = {
        'category': category,
        'count': qs.count(),
        'total': total,
        'total_str': dollars(total),
        'edit_form': bootstrapform(forms.CategoryForm(instance=category)),
        'move_form': bootstrapform(forms.CategoryMoveForm()),
        'category_names': _category_names(exclude=category),
    }
    return render(request, 'category.html', data)


@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    assert not Expense.objects.filter(category=category).count()
    category.delete()
    return redirect(reverse('categories'))


@login_required
@require_POST
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = forms.CategoryForm(request.POST, instance=category)
    if form.is_valid():
        form.save()
        return redirect(reverse('category', args=(category.pk,)))
    else:
        return http.HttpResponse('<h2>Error</h2>' + str(form.errors))


@login_required
@require_POST
def move_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = forms.CategoryMoveForm(request.POST)
    if form.is_valid():
        new_category = Category.objects.get(name=form.cleaned_data['name'])
        for expense in Expense.objects.filter(category=category):
            expense.category = new_category
            expense.save()
        return redirect(reverse('category', args=(category.pk,)))
    else:
        return http.HttpResponse('<h2>Error</h2>' + str(form.errors))



@json_view
def mobile_auth(request):
    data = {}
    if request.method == 'POST':
        response = login(request)
        assert response.status_code == 302, response.status_code
    else:
        data['csrf_token'] = get_token(request)
    if request.user.is_authenticated():
        data['username'] = request.user.username
    return data


def mobile_appcache(request):
    data = {}
    views_ts = os.stat(__file__)[stat.ST_MTIME]
    tmpl_fs = os.path.join(
        os.path.dirname(__file__),
        'templates',
        'appcache.html'
    )
    tmpl_ts = os.stat(tmpl_fs)[stat.ST_MTIME]
    data['version'] = max(views_ts, tmpl_ts)

    response = render(request, 'appcache.html', data)
    response['Content-Type'] = 'text/cache-manifest'

    return response


@login_required
@json_view
def compare(request):

    _category_ids = []
    for c in request.GET.get('c', '').split(','):
        if not c:
            continue
        _category_ids.append(int(c))
    _categories = Category.objects.filter(id__in=_category_ids)

    dates = []
    for m in request.GET.get('m', '').split(','):
        if not m:
            continue
        month, year = [int(x) for x in m.split(':')]
        dates.append(datetime.date(year, month, 1))

    if (
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        or
        request.GET.get('format') == 'json'
    ):

        head = ['Category']
        for date in dates:
            head.append(date.strftime('%B %Y'))

        data = [head]

        base_qs = Expense.objects
        base_qs = base_qs.filter(category__in=_categories)

        #if without:
        #    base_qs = base_qs.exclude(category=without)

        categories = defaultdict(dict)
        category_sums = defaultdict(Decimal)

        for each in dates:
            qs = (
                base_qs
                .filter(date__month=each.month, date__year=each.year)
                .values('category_id')
                .annotate(total=Sum('amount'))
            )
            for e in qs:
                categories[e['category_id']][each] = e['total']
                category_sums[e['category_id']] += e['total']

        sums = sorted((v, k) for (k, v) in category_sums.items())
        sums.reverse()
        category_names = {}
        category_ids = [x[1] for x in sums]
        for each in Category.objects.filter(id__in=category_ids):
            category_names[each.pk] = each.name

        for category_id in category_ids:
            row = [category_names[category_id]]
            for date in dates:
                amount = categories[category_id].get(date, Decimal('0.0'))
                row.append(round(float(amount), 2))
            data.append(row)

        return {'data': data, 'title': None, 'rowcount': len(category_ids)}

    all_months = []
    first, = Expense.objects.all().values('date').order_by('date')[:1]
    date = first['date']
    today = datetime.date.today()
    while date < today:
        next = date
        while next.month == date.month:
            next += datetime.timedelta(days=1)
        count = (
            Expense.objects
            .filter(date__year=date.year, date__month=date.month)
            .count()
        )
        checked = date in dates
        all_months.append({
            'key': date.strftime('%m:%Y'),
            'label': date.strftime('%B %Y'),
            'count': count,
            'checked': checked,
        })
        date = next

    all_categories = []
    for category in Category.objects.all().order_by('name'):
        category.checked = category in _categories
        total = (
            Expense.objects
            .filter(category=category)
            .aggregate(Sum('amount'))
        )
        total = total['amount__sum']
        if total is None:
            total = 0.0
        category.total_str = dollars(total)
        all_categories.append(category)

    page_title = 'Compare months'

    data = {
        'page_title': page_title,
        'all_categories': all_categories,
        'all_months': all_months,
    }
    return render(request, 'compare.html', data)
