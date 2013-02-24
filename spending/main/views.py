import json
import datetime
import locale
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
    if (
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        and
        'application/json' in request.META.get('HTTP_ACCEPT')
    ):
        rows = []
        qs = Expense.objects.all().select_related()
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
                'amount_string': '$' + locale.format('%.2f', expense.amount, True),
                'amount': round(float(expense.amount), 2),
                'user': expense.user.first_name or expense.user.username,
                'date': expense.date.strftime('%A %d %B %Y'),
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
        data = {}
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
