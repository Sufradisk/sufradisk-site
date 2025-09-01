from django.contrib import admin
from .models import Game, Review

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('game', 'user_email', 'rating', 'created_at')
    list_filter = ('game', 'rating', 'created_at')
    search_fields = ('user__email', 'comment')

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"
    user_email.short_description = 'Email'
