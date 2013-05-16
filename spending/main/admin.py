from django.contrib import admin
from spending.main.models import Household, Expense, Category


class HouseholdAdmin(admin.ModelAdmin):
    list_display = ('name', 'no_users')

    def no_users(self, obj):
        return obj.users.all().count()
    no_users.short_description = '# users'


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'date', 'user', 'category')

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


admin.site.register(Household, HouseholdAdmin)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Category, CategoryAdmin)
