from django.contrib import admin
from spending.main.models import Expense, Category


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'date', 'user', 'category')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Category, CategoryAdmin)
