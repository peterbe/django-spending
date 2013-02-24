from django import forms
from .models import Expense


class TypeaheadField(forms.CharField):

    def widget_attrs(self, widget):
        attrs = super(TypeaheadField, self).widget_attrs(widget)
        attrs['autocomplete'] = 'off'
        attrs['class'] = 'typeahead'
        attrs['data-provide'] = 'typeahead'
        return attrs


class ExpenseForm(forms.ModelForm):

    category = TypeaheadField()

    class Meta:
        model = Expense
        exclude = ('added', 'user', 'category')
