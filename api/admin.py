from django.contrib import admin

# Register your models here.
from .models import *
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Sales)
admin.site.register(Product)
admin.site.register(UserInventory)
admin.site.register(IncomingInventory)
admin.site.register(DailyInventoryMetrics)
admin.site.register(OldIncomingInventory)
admin.site.register(OldUserInventory)


