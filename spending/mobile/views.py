from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from spending.main.models import Expense, Category


def home(request):
    data = {}
    return render(request, 'mobile/home.html', data)
