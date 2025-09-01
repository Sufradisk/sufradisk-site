from .models import Transaction
from django.utils import timezone
from .models import Transaction

def add_currency(profile, amount, reason):
    profile.currency += amount
    profile.save()
    Transaction.objects.create(profile=profile, amount=amount, reason=reason)

def give_daily_reward(profile):
    today = timezone.now().date()

    if profile.last_login_reward == today:
        return  # already claimed today

    if profile.last_login_reward == today - timezone.timedelta(days=1):
        profile.streak += 1  # continue streak
    else:
        profile.streak = 1  # reset streak

    reward = 10
    if profile.streak % 7 == 0:  # 7-day streak bonus
        reward += 50

    profile.currency += reward
    profile.last_login_reward = today
    profile.save()

    Transaction.objects.create(
        profile=profile,
        amount=reward,
        reason=f"Daily login reward (Streak: {profile.streak})"
    )