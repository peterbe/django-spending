import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.views import login
from django.middleware.csrf import get_token
from spending.main.models import Expense, Category
from spending.main.utils import json_view
from . import forms


def home(request):
    data = {}
    return render(request, 'mobile/home.html', data)


@login_required
@require_POST
@json_view
def submit(request):
    form = forms.MobileExpenseForm(data=request.POST)
    if form.is_valid():
        data = form.cleaned_data
        category_value = data['category']
        if category_value == '_other':
            category_value = data['other_category']
        try:
            category = Category.objects.get(name__istartswith=category_value)
        except Category.DoesNotExist:
            category = Category.objects.create(name=category_value)

        expense = None
        try:
            last_expense, = Expense.objects.filter(user=request.user).order_by('-added')[:1]
            if (
                last_expense.amount == data['amount']
                and
                last_expense.category == category
                and
                last_expense.date == data['date']
                and
                last_expense.notes == data['notes'].strip()
            ):
                print "Not creating another identical one"
                expense = last_expense
        except IndexError:
            pass
        if expense is None:
            expense = Expense.objects.create(
                category=category,
                amount=data['amount'],
                user=request.user,
                date=data['date'],
                notes=data['notes'].strip()
            )
        #today = datetime.datetime.utcnow()
        data = {
            'success_message': '$%.2f for %s added' % (expense.amount, expense.category.name),
            #'todays_date': today.strftime('%Y-%m-%d'),
        }
    else:
        data = {'errors': form.errors}
    return data

@json_view
def auth(request):
    data = {}
    if request.method == 'POST':
        response = login(request)
        assert response.status_code == 302, response.status_code
    else:
        data['csrf_token'] = get_token(request)
    if request.user.is_authenticated():
        data['username'] = request.user.username
    return data


@login_required
@json_view
def categories(request):
    qs = Category.objects.all()
    result = {
        'categories': []
    }
    for each in qs.order_by('name'):
        result['categories'].append([each.name, each.pk])
    return result
