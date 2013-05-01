import datetime
from django import forms
from spending.main.models import Expense


class MobileExpenseForm(forms.ModelForm):

    category = forms.CharField(required=False)
    other_category = forms.CharField(required=False)

    class Meta:
        model = Expense
        exclude = ('added', 'user', 'category')

    def __init__(self, *args, **kwargs):
        super(MobileExpenseForm, self).__init__(*args, **kwargs)
        # because we can use `other_category`
        self.fields['category'].required = False
        self.fields['date'].required = False

    def clean_date(self):
        value = self.cleaned_data['date']
        if not value:
            value = datetime.datetime.utcnow().date()
        return value
