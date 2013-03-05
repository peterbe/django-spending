import json
import datetime
import locale
import time
import random
from decimal import Decimal
from collections import defaultdict
from django import http
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib import messages
from django.template.loader import get_template
from django.template import Context
from django.contrib.auth.decorators import login_required
from django.utils.timezone import utc
from django.views.decorators.http import require_POST

from .forms import ExpenseForm
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
                category = Category.objects.get(name__iexact=data['category'])
            except Category.DoesNotExist:
                category = Category.objects.create(name=data['category'])
            expense = Expense.objects.create(
                category=category,
                amount=data['amount'],
                user=request.user,
                date=data['date'],
                notes=data['notes'].strip()
            )
            messages.add_message(
                request,
                messages.INFO,
                '$%.2f for %s added' % (expense.amount, expense.category.name)
            )

            return redirect(reverse('home'))
    else:
        initial = {}
        form = bootstrapform(ExpenseForm(initial=initial))
    data['form'] = form

    data['category_names'] = _category_names()
    return render(request, 'home.html', data)


def _category_names():
    category_names = [x.name for x in Category.objects.all().order_by('name')]
    return json.dumps(category_names)


def bootstrapform(form):
    template = get_template("bootstrapform/form.html")
    context = Context({'form': form})
    return template.render(context)


@login_required
def expenses(request):
    first = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0)
    while first.strftime('%d') != '01':
        first -= datetime.timedelta(days=1)
    if (
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        and
        'application/json' in request.META.get('HTTP_ACCEPT')
    ):
        rows = []
        qs = Expense.objects.all().select_related()
        qs = qs.filter(date__gte=first)

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
        for expense in qs.order_by('added'):
            rows.append({
                'pk': expense.pk,
                'amount_string': dollars(expense.amount),
                'amount': round(float(expense.amount), 2),
                'user': expense.user.first_name or expense.user.username,
                'date': expense.date.strftime('%A %d'),
                'category': expense.category.name,
                'notes': expense.notes
            })
            latest = expense.added

        if latest:
            latest = latest.strftime('%Y-%m-%d %H:%M:%S')
        result = {
            'latest': latest,
            'rows': rows
        }
        return http.HttpResponse(json.dumps(result), mimetype="application/json")
    else:
        data = {'first': first}
        return render(request, 'expenses.html', data)


@login_required
def edit_expense(request, pk):
    data = {}
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            data = form.cleaned_data
            try:
                category = Category.objects.get(name__iexact=data['category'])
            except Category.DoesNotExist:
                category = Category.objects.create(name=data['category'])
            expense.category = category
            expense.amount = data['amount']
            expense.date = data['date']
            expense.notes = data['notes'].strip()
            expense.save()

            messages.add_message(
                request,
                messages.INFO,
                '$%.2f for %s edited' % (expense.amount, expense.category.name)
            )
            return redirect(reverse('expenses'))

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
        last = last.date
        date = first.date

        points = defaultdict(list)
        cum_points = defaultdict(int)
        categories = [(x.pk, x.name) for x in
                      Category.objects.all()]
        _categories = dict(categories)
        while date < last:
            next = date + interval
            counts = defaultdict(int)
            for expense in (Expense.objects
                         .filter(added__gte=date,
                                 added__lt=next)):
                counts[expense.category_id] += float(expense.amount)

            for category_id, name in categories:
                count = counts[category_id]
                points[name].append((date, count + cum_points.get(category_id, 0)))

            date = next

        colors = ColorPump()
        series = []

        for name, data in points.iteritems():
            series.append({
              'color': colors.next(),
              'name': name,
              'data': [{'x': int(time.mktime(a.timetuple())), 'y': b} for (a, b) in data]
            })

        return series

    data = {'data': get_series()}
    from pprint import pprint
    pprint(data)

    return http.HttpResponse(json.dumps(data), mimetype="application/json")


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
                'amount': Decimal('0.0')
            }
        bucket['amount'] += amount

    if bucket:
        months.append(bucket)

    total = Decimal('0.0')
    for each in months:
        each['amount_str'] = dollars(each['amount'])
        total += each['amount']
    months.append({
        'date': 'TOTAL',
        'amount': total,
        'amount_str': dollars(total),
    })

    data = {
        'months': months,
    }
    print months
    return render(request, 'calendar.html', data)
