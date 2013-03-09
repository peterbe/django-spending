from django import forms
from .models import Expense, Category


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


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = ('name',)

    def clean_name(self):
        value = self.cleaned_data['name'].strip()
        if Category.objects.exclude(pk=self.instance.pk).filter(name__iexact=value):
            raise forms.ValidationError('Named used by a different category')
        return value


class CategoryMoveForm(forms.Form):

    name = TypeaheadField()
