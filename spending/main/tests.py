from django.core.urlresolvers import reverse

from django.test import TestCase
from spending.main.models import Expense, Category


class MobileTest(TestCase):

    def test_basic_submission(self):
        resp = self.client.get(reverse('mobile'))
        self.assertEqual(resp.status_code, 200)

        data = {
            'amount': '10.15',
            'other_category': 'Garden',
            'category': '_other',
            'notes': 'Stuff',
            'date': '',
        }
        resp = self.client.post(reverse('mobile'), data)
        self.assertEqual(resp.status_code, 200)
        print resp.content
