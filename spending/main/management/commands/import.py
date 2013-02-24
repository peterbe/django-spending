import datetime
import csv
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from spending.main.models import Expense, Category


class Command(BaseCommand):

    args = 'file.csv'
    def handle(self, filename, **options):
        reader = csv.reader(open(filename))

        users = {}
        categories = {}

        for line in reader:
            amount, who, date, category, notes = line[:5]
            if amount == 'AMOUNT':
                continue
            amount = Decimal(amount.replace('$','').replace(',',''))
            if who not in users:
                try:
                    users[who] = User.objects.get(first_name__iexact=who)
                except User.DoesNotExist:
                    raise
            m, d, y = [int(x) for x in date.split('/')]
            date = datetime.date(y, m, d)

            if category not in categories:
                try:
                    obj = Category.objects.get(name__iexact=category)
                except Category.DoesNotExist:
                    obj = Category.objects.create(name=category)
                categories[category] = obj

            __, created = Expense.objects.get_or_create(
                amount=amount,
                user=users[who],
                date=date,
                category=categories[category],
                notes=notes,
            )
            print created
