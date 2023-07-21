from django.contrib import admin
from planner_updates.models import Update, Token, Asset, Signature

admin.site.register(Update)
admin.site.register(Token)
admin.site.register(Asset)
admin.site.register(Signature)
