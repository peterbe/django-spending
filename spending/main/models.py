import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import utc


def today():
    return datetime.date.today()

def now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


class Category(models.Model):
    name = models.CharField(max_length=100)


class Expense(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User)
    date = models.DateField(default=today)
    category = models.ForeignKey(Category)
    notes = models.TextField(blank=True)
    added = models.DateTimeField(default=now)
