from django.contrib import admin
from .models import Game, PlaySession, Advertisement
from .models import ShopOffer, Profile, InventoryItem

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'is_approved')
    list_filter = ('is_approved',)
    search_fields = ('name', 'author__username')

    # 👇 this makes "is_approved" a checkbox in the list view
    list_editable = ('is_approved',)

@admin.register(PlaySession)
class PlaySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'start_time', 'end_time')
    list_filter = ('game', 'user', 'start_time', 'end_time')
    search_fields = ('user__username', 'game__name')

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('location', 'media_type', 'link', 'active')
    list_filter = ('location', 'media_type', 'active')

@admin.register(ShopOffer)
class ShopOfferAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "offer_type")
    list_filter = ("offer_type",)
    search_fields = ("title", "description")

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "active_background")  # ✅ fixed
    search_fields = ("user__username",)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("profile", "offer", "acquired_at", "used")
    list_filter = ("used", "acquired_at", "offer")
    search_fields = ("profile__user__username", "offer__title")