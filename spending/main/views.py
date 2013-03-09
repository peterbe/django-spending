import json
import datetime
import locale
import time
import random
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
from django.template.loader import get_template
from django.template import Context
from django.contrib.auth.decorators import login_required
from django.utils.timezone import utc
from django.views.decorators.http import require_POST
from django.template.defaultfilters import slugify

from .forms import ExpenseForm, CategoryForm, CategoryMoveForm
from .models import Expense, Category


locale.setlocale(locale.LC_ALL, '')


def dollars(amount):
    return '$' + locale.format('%.2f', amount, True)


@csrf_exempt
@transaction.commit_on_success
def home(request):
    data = {}
    if request.method == 'POST':
        form = ExpenseForm(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                category = Category.objects.get(name__istartswith=data['category'])
            except Category.DoesNotExist:
                category = Category.objects.create(name=data['category'])
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
            raise NotImplementedError
        return http.HttpResponse(
            json.dumps(data),
            mimetype="application/json"
        )

    else:
        initial = {}
        form = bootstrapform(ExpenseForm(initial=initial))
    data['form'] = form

    data['category_names'] = _category_names()
    return render(request, 'home.html', data)


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
def expenses(request):
    _now = datetime.datetime.utcnow()
    month = int(request.GET.get('month', _now.month))
    year = int(request.GET.get('year', _now.year))
    first = datetime.datetime(year, month, 1, 0, 0, 0)
    historic = 'month' in request.GET and 'year' in request.GET
    data = {
        'first': first,
        'poll': not historic,
    }
    return render(request, 'expenses.html', data)


@login_required
def expenses_json(request):
    _now = datetime.datetime.utcnow()
    month = int(request.GET.get('month', _now.month))
    year = int(request.GET.get('year', _now.year))
    first = datetime.datetime(year, month, 1, 0, 0, 0)
    rows = []
    qs = Expense.objects.all().select_related()
    if month == 12:
        next = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        next = datetime.datetime(year, month + 1, 1, 0, 0, 0)

    qs = qs.filter(date__gte=first, date__lt=next)

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
    if request.GET.get('category'):
        category = Category.objects.get(name__iexact=request.GET['category'])
        qs = qs.filter(category=category)
    if request.GET.get('sort'):
        sort = request.GET.get('sort')
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
            'date': expense.date.strftime('%A %d'),
            'category': expense.category.name,
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
        form = ExpenseForm(request.POST, instance=expense)
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
        form = ExpenseForm(instance=expense, initial=initial)

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

    def get_series():
        interval = datetime.timedelta(days=7)
        first, = Expense.objects.all().order_by('date')[:1]
        last, = Expense.objects.all().order_by('-date')[:1]
        first = first.date
        last = last.date

        #first = datetime.datetime(first.year, first.month, first.day)
        #first = first.replace(tzinfo=utc)
        #last = datetime.datetime(last.year, last.month, last.day)
        #last = last.replace(tzinfo=utc)

        date = first

        points = defaultdict(list)
        cum_points = defaultdict(int)
        categories = [(x.pk, x.name) for x in
                      Category.objects.all()]
        _categories = dict(categories)
        while date < last:
            next = date + interval
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

        _totals = {}
        for name, data in points.iteritems():
            _totals[name] = sum(x[1] for x in data)
            series.append({
              'color': _get_next_color(name, colors),
              'name': name,
              'data': [{'x': int(time.mktime(a.timetuple())), 'y': b} for (a, b) in data],
            })

        series.sort(
            lambda x, y: cmp(_totals[x['name']], _totals[y['name']]),
            reverse=True
        )
        return series

    data = {'data': get_series()}

    return http.HttpResponse(json.dumps(data), mimetype="application/json")

def _get_next_color(name, colorpump):
    cache_key = 'timeline-%s' % slugify(name)
    color = cache.get(cache_key)
    if color is None:
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
    for amount, date, category_id in qs:
        if date.strftime('%B %Y') != month:
            month = date.strftime('%B %Y')
            # new month
            if bucket:
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

    if bucket:
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

    data = {
        'months': months,
    }

    data.update({
        'total_str': dollars(total),
        'total_rent_str': dollars(total_rent),
        'total_total_str': dollars(total_rent + total),
    })

    return render(request, 'calendar.html', data)

from django.db.models import Sum

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
        'edit_form': bootstrapform(CategoryForm(instance=category)),
        'move_form': bootstrapform(CategoryMoveForm()),
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
    form = CategoryForm(request.POST, instance=category)
    if form.is_valid():
        form.save()
        return redirect(reverse('category', args=(category.pk,)))
    else:
        return http.HttpResponse('<h2>Error</h2>' + str(form.errors))


@login_required
@require_POST
def move_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryMoveForm(request.POST)
    if form.is_valid():
        new_category = Category.objects.get(name=form.cleaned_data['name'])
        for expense in Expense.objects.filter(category=category):
            expense.category = new_category
            expense.save()
        return redirect(reverse('category', args=(category.pk,)))
    else:
        return http.HttpResponse('<h2>Error</h2>' + str(form.errors))
