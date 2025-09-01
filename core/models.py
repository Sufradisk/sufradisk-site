from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
import uuid


ROLE_CHOICES = (
    ('player', 'Player'),
    ('developer', 'Developer'),
)

class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="games/", blank=True, null=True)
    source = models.FileField(upload_to="games/files/", blank=True, null=True)
    embed_code = models.TextField(blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    is_approved = models.BooleanField(default=False)

    # NEW FIELDS
    is_recommended = models.BooleanField(default=False)
    recommended_until = models.DateTimeField(blank=True, null=True)

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="games")
    earnings_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # renamed
    play_count = models.PositiveIntegerField(default=0)  # renamed

    def is_still_recommended(self):
        if self.is_recommended and self.recommended_until:
            return timezone.now() < self.recommended_until
        return False

    def __str__(self):
        return self.name


class GameReview(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.game.name} ({self.rating})"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    currency = models.PositiveIntegerField(default=100)
    streak = models.PositiveIntegerField(default=0)
    last_login_reward = models.DateField(null=True, blank=True)
    active_background = models.CharField(max_length=100, blank=True, null=True)
    favorite_games = models.ManyToManyField("Game", blank=True, related_name="favorited_by")
    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = str(uuid.uuid4())[:8].upper()
            while Profile.objects.filter(referral_code=code).exists():
                code = str(uuid.uuid4())[:8].upper()
            self.referral_code = code
        super().save(*args, **kwargs)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

class ShopOffer(models.Model):
    OFFER_TYPES = [
        ("background", "Background"),   # unlocks a background via css_class
        ("reward", "Reward"),           # any other reward (announcement, promo, etc.)
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="shop_offers/", blank=True, null=True)
    price = models.PositiveIntegerField()
    offer_type = models.CharField(
        max_length=50,
        choices=OFFER_TYPES,
        default="reward"
    )
    css_class = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="For backgrounds only: CSS class to apply"
    )

    def __str__(self):
        return self.title


class OwnedOffer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    offer = models.ForeignKey(ShopOffer, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} owns {self.offer.title}"


class Transaction(models.Model):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="transactions"   # 👈 add this
    )
    amount = models.IntegerField()  # can be + (earn) or - (spend)
    reason = models.CharField(max_length=255)  # e.g. "Upload bonus", "Promotion"
    created_at = models.DateTimeField(auto_now_add=True)
    offer = models.ForeignKey(ShopOffer, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        sign = "+" if self.amount > 0 else "-"
        return f"{self.profile.user.username}: {sign}{abs(self.amount)} ({self.reason})"

class InventoryItem(models.Model):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="inventory"
    )
    offer = models.ForeignKey(
        ShopOffer, on_delete=models.CASCADE, related_name="inventory_items"
    )
    acquired_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)  # for consumables like diamonds

    def __str__(self):
        return f"{self.profile.user.username} owns {self.offer.title}"



class DeveloperEarning(models.Model):
    developer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="developer_earnings")
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name="developer_earnings")
    total_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.developer.username} - ${self.amount_usd}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)


class Advertisement(models.Model):
    # New field to distinguish "frame ads" vs "popup ads"
    AD_TYPES = [
        ("frame", "Frame Ad"),
        ("popup", "Popup Ad"),
    ]

    # Where it appears (only used for frame ads)
    LOCATION_CHOICES = [
        ('home', 'Home Page'),
        ('catalog', 'Catalog Page'),
    ]

    ad_type = models.CharField(max_length=10, choices=AD_TYPES, default="frame")
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES, blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=[('image', 'Image'), ('video', 'Video')])
    file = models.FileField(upload_to='ads/', blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        if self.ad_type == "frame":
            return f"Frame Ad ({self.location}) - {self.media_type}"
        return f"Popup Ad - {self.media_type}"


class PlaySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_sessions", db_index=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="game_sessions", db_index=True)
    start_time = models.DateTimeField(auto_now_add=True, db_index=True)
    end_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'game', 'start_time']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                condition=Q(end_time__isnull=True),
                name='unique_open_session_per_user_game',
            )
        ]

    @property
    def duration_seconds(self):
        end = self.end_time or timezone.now()
        return int((end - self.start_time).total_seconds())

    def close(self):
        if not self.end_time:
            self.end_time = timezone.now()
            self.save(update_fields=['end_time'])


