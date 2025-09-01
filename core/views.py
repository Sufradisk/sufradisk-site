from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Game, GameReview
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .models import Profile
from django.contrib.auth import logout
from .forms import AvatarUploadForm
from .forms import EditNameForm
from django.contrib.auth import get_user_model
User = get_user_model()
from django.conf import settings
import random
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.translation import gettext as _
from django.core.mail import send_mail
from django.db.models import Avg
from reviews.models import Favorite
from .forms import ProfileFullEditForm
from .forms import CustomUserCreationForm
from .forms import RegistrationForm  # make sure this import is active
from .forms import GameForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import Advertisement
from .forms import AdvertisementForm

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Game, PlaySession
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from datetime import timedelta
from decimal import Decimal
from .models import DeveloperEarning
from .models import Transaction
from .forms import GameReviewForm
from .models import ShopOffer, OwnedOffer,InventoryItem

def get_items_with_ads(location, interval=9):
    games = list(Game.objects.all())
    ads = list(Advertisement.objects.filter(location=location, active=True))

    for g in games:
        g.type = "game"
    for ad in ads:
        ad.type = "ad"

    combined = []
    ad_index = 0

    for i, game in enumerate(games, start=1):
        combined.append(game)
        if i % interval == 0 and ad_index < len(ads):
            combined.append(ads[ad_index])
            ad_index += 1

    return combined

def home(request):
    now = timezone.now().date()  # use only the date for streak comparison
    daily_reward = None  # 👈 we’ll pass this to template

    # 🏆 Leaderboard (Top 10 richest)
    top_players = (
        User.objects.filter(profile__currency__gt=0)
        .select_related("profile")
        .order_by("-profile__currency")[:10]
    )

    # 🎁 Daily login reward with streaks
    if request.user.is_authenticated:
        profile = request.user.profile
        if profile.last_login_reward != now:  # not yet rewarded today
            if profile.last_login_reward == now - timedelta(days=1):
                profile.streak += 1  # consecutive day
            else:
                profile.streak = 1  # reset streak

            # base reward + streak bonus
            daily_reward = 10 + (profile.streak * 2)
            profile.currency += daily_reward
            profile.last_login_reward = now
            profile.save()

            # log transaction
            Transaction.objects.create(
                profile=profile,
                amount=daily_reward,
                reason=f"Daily login reward (Day {profile.streak})"
            )

    # 🎮 Recommended games
    recommended_qs = (
        Game.objects.filter(is_approved=True, is_recommended=True, recommended_until__gt=timezone.now())
        .order_by('-recommended_until')[:10]
    )
    recommended_games = list(recommended_qs)
    recommended_ids = [g.id for g in recommended_games]

    # 🎲 Random games excluding recommended
    all_games_qs = Game.objects.filter(is_approved=True).exclude(id__in=recommended_ids)
    all_games = list(all_games_qs)
    random.shuffle(all_games)
    random_games = all_games[:20]  # reduced from 50 → 20 for performance

    # 📢 Ads for "home"
    ads = list(Advertisement.objects.filter(active=True, location="home"))
    random.shuffle(ads)

    items = []
    ad_index = 0
    game_counter = 0

    # Recommended first
    for game in recommended_games:
        items.append({"type": "game", "object": game, "recommended": True})

    # Then random games + ads
    for game in random_games:
        items.append({"type": "game", "object": game, "recommended": False})
        game_counter += 1
        if game_counter % 4 == 0 and ad_index < len(ads):
            items.append({"type": "ad", "object": ads[ad_index]})
            ad_index += 1

    # Login / Register forms
    form_login = AuthenticationForm(request, data=request.POST or None)
    form_register = CustomUserCreationForm(request.POST or None)
    show_modal = False

    if request.method == 'POST':
        show_modal = True
        if 'password1' in request.POST:  # Register
            if form_register.is_valid():
                form_register.save()
                messages.success(request, 'Аккаунт создан успешно!')
                return redirect('dashboard')
        elif 'password' in request.POST:  # Login
            if form_login.is_valid():
                login(request, form_login.get_user())
                messages.success(request, 'Вы успешно вошли в систему!')
                return redirect('dashboard')

    return render(request, 'core/home.html', {
        'items': items,
        'form_login': form_login,
        'form_register': form_register,
        'show_modal': show_modal,
        'top_players': top_players,  # leaderboard
        'daily_reward': daily_reward,  # 👈 pass reward for SweetAlert
    })

def catalog(request):
    filter_by = request.GET.get("filter", "all")
    genre = request.GET.get("genre", "")
    search_query = request.GET.get("q", "")

    # Base queryset
    games_qs = Game.objects.filter(is_approved=True)

    # Filters
    if filter_by == "popular":
        games_qs = games_qs.order_by("-play_count")
    elif filter_by == "newest":
        games_qs = games_qs.order_by("-id")
    elif filter_by == "recommended":
        games_qs = games_qs.filter(is_recommended=True)

    if genre:
        games_qs = games_qs.filter(genre__iexact=genre)

    if search_query:
        games_qs = games_qs.filter(name__icontains=search_query)

    games = list(games_qs)

    # --- Add a type field to games ---
    wrapped_games = []
    for g in games:
        g.type = "game"   # attach type so template works
        wrapped_games.append(g)

    # Get ads
    items = get_items_with_ads(location="catalog")
    ads = [i for i in items if i.type == "ad"]
    random.shuffle(ads)

    # Merge games + ads
    result = []
    ad_index = 0
    ad_interval = 6
    max_ads = 3

    for i, game in enumerate(wrapped_games, start=1):
        result.append(game)
        if i % ad_interval == 0 and ad_index < len(ads) and ad_index < max_ads:
            result.append(ads[ad_index])
            ad_index += 1

    genres = Game.objects.values_list("genre", flat=True).distinct()

    return render(request, "core/catalog.html", {
        "items": result,
        "filter": filter_by,
        "genres": genres,
        "selected_genre": genre,
        "search_query": search_query,
    })



def about(request):
    return render(request, 'core/about.html')

def faq(request):
    return render(request, 'core/faq.html')

@login_required
def add_game_view(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'developer':
        return redirect('home')  # block players

    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            game = form.save(commit=False)
            game.author = request.user
            game.save()

            # ✅ reward developer
            request.user.profile.currency += 50
            request.user.profile.save()
            Transaction.objects.create(
                profile=request.user.profile,
                amount=+50,
                reason="Game uploaded"
            )

            # ✅ promotion option
            if request.user.profile.currency >= 100:
                request.user.profile.currency -= 100
                request.user.profile.save()
                Transaction.objects.create(
                    profile=request.user.profile,
                    amount=-100,
                    reason="Game promotion"
                )
                game.promoted_until = timezone.now() + timedelta(hours=24)
                game.save()
                messages.success(request, "✅ Game uploaded & promoted successfully!")
            else:
                messages.info(request, "✅ Game uploaded! (Not promoted, not enough currency)")

            return redirect('catalog')
    else:
        form = GameForm(user=request.user)

    return render(request, 'core/add_game.html', {'form': form})


@login_required
def wallet_view(request):
    transactions = request.user.profile.transactions.order_by("-created_at")
    return render(request, "core/wallet.html", {
        "profile": request.user.profile,
        "transactions": transactions
    })

@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    reviews = game.reviews.select_related("user").order_by("-created_at")

    # Average rating & total reviews
    avg_rating = reviews.aggregate(avg=Avg("rating"))["avg"]
    if avg_rating:
        avg_rating = round(avg_rating, 1)
    total_reviews = reviews.count()

    # Check if this user already reviewed the game
    existing_review = GameReview.objects.filter(game=game, user=request.user).first()

    if request.method == "POST":
        if existing_review:
            messages.warning(request, "❗ Вы уже оставили отзыв для этой игры.")
            return redirect("game_detail", game_id=game.id)

        form = GameReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.game = game
            review.user = request.user
            review.save()
            messages.success(request, "✅ Ваш отзыв успешно добавлен!")
            return redirect("game_detail", game_id=game.id)
    else:
        form = GameReviewForm()

    return render(request, "core/game_detail.html", {
        "game": game,
        "reviews": reviews,
        "form": form,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "existing_review": existing_review,
    })

# def play_game(request, game_id):
#     game = get_object_or_404(Game, id=game_id)
#     return render(request, 'core/play_game.html', {'game': game})

def my_games(request):
    return render(request, 'core/my_games.html')

def language_select(request):
    return render(request, 'core/language_select.html')

# views.py
def register_view(request):
    referral_code = request.GET.get("ref")  # 🔑 check ?ref=CODE in URL

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            profile, created = Profile.objects.get_or_create(user=user)

            if role:
                profile.role = role

            # handle referral
            if referral_code:
                try:
                    referrer = Profile.objects.get(referral_code=referral_code)
                    profile.referred_by = referrer

                    # 🎁 rewards
                    profile.currency += 50
                    referrer.currency += 100
                    profile.save()
                    referrer.save()

                    Transaction.objects.create(
                        profile=profile,
                        amount=50,
                        reason="Referral bonus (new user)"
                    )
                    Transaction.objects.create(
                        profile=referrer,
                        amount=100,
                        reason=f"Referral bonus (invited {profile.user.username})"
                    )

                    # ✅ floating text trigger (store a message)
                    messages.success(request, "+50 coins earned from referral!")

                except Profile.DoesNotExist:
                    profile.save()
            else:
                profile.save()

            login(request, user)
            return redirect('dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')  # send to dashboard
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def my_profile(request):
    role = getattr(request.user.profile, 'role', None)

    total_hours = None
    dev_total_hours = None

    if role == 'player':
        total = (
            PlaySession.objects.filter(user=request.user, end_time__isnull=False)
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F('end_time') - F('start_time'),
                        output_field=DurationField(),
                    )
                )
            )['total']
        )
        if total and isinstance(total, timedelta):
            total_hours = int(total.total_seconds() // 3600)

    elif role == 'developer':
        dev_total = (
            PlaySession.objects.filter(game__author=request.user, end_time__isnull=False)
            .aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F('end_time') - F('start_time'),
                        output_field=DurationField(),
                    )
                )
            )['total']
        )
        if dev_total and isinstance(dev_total, timedelta):
            dev_total_hours = int(dev_total.total_seconds() // 3600)

    # ✅ new context
    favorite_games = request.user.profile.favorite_games.all()
    user_reviews = GameReview.objects.filter(user=request.user).select_related("game").order_by("-created_at")

    return render(request, 'registration/my_profile.html', {
        'total_time_hours': total_hours,
        'dev_total_hours': dev_total_hours,
        'favorite_games': favorite_games,
        'user_reviews': user_reviews,
    })


@login_required
def edit_profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        print("✅ POST received")
        form = ProfileFullEditForm(request.POST, request.FILES, instance=profile, user=request.user)

        # 🚫 Prevent role change for non-admins
        if not request.user.is_superuser:
            form.instance.role = profile.role

        if form.is_valid():
            print("✅ Form is valid")
            profile = form.save()
            print("✅ Profile saved:", profile)

            # Save user data
            request.user.first_name = form.cleaned_data['first_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            print("✅ User info updated:", request.user.first_name, request.user.email)

            return redirect('my_profile')
        else:
            print("❌ Form errors:", form.errors)
    else:
        print("🔵 GET request")
        form = ProfileFullEditForm(instance=profile, user=request.user)

    return render(request, 'edit_profile.html', {'form': form})

@login_required
def edit_game_view(request, game_id):
    game = get_object_or_404(Game, id=game_id, author=request.user)  # ✅ only owner can edit
    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            form.save()
            return redirect('catalog')  # or dashboard
    else:
        form = GameForm(instance=game)

    return render(request, 'core/add_game.html', {'form': form, 'editing': True})

# Upload avatar
@login_required
def upload_avatar(request):
    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('my_profile')
    else:
        form = AvatarUploadForm(instance=request.user.profile)
    return render(request, 'upload_avatar.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)  # чтобы пользователь сразу вышел
        user.delete()  # удаление пользователя
        messages.success(request, 'Аккаунт успешно удалён.')
        return redirect('home')
    return render(request, 'delete_account.html')


# Для временного хранения кода
reset_codes = {}

def send_reset_code(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            code = str(random.randint(100000, 999999))
            reset_codes[email] = code  # сохраняем временно

            send_mail(
                'Ваш код восстановления пароля',
                f'Ваш код: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            request.session['reset_email'] = email
            return redirect('check_code')
        except User.DoesNotExist:
            messages.error(request, 'Пользователь с таким e-mail не найден.')

    return render(request, 'email/send_code.html')


def check_reset_code(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, "Сессия сброшена. Повторите процесс.")
        return redirect('send_code')

    if request.method == 'POST':
        entered_code = request.POST.get('code')
        if email in reset_codes and reset_codes[email] == entered_code:
            return redirect('set_password')
        else:
            messages.error(request, 'Неверный код.')
    return render(request, 'email/check_code.html')


def set_new_password(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, "Сессия сброшена. Повторите процесс.")
        return redirect('send_code')

    if request.method == 'POST':
        new_password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            reset_codes.pop(email, None)  # удалим код
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('login')  # или твоя страница входа
        except User.DoesNotExist:
            messages.error(request, 'Ошибка, пользователь не найден.')
    return render(request, 'email/set_password.html')

def send_code(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        code = random.randint(100000, 999999)
        request.session['reset_email'] = email
        request.session['verification_code'] = str(code)  # 🔧 ВАЖНО

        send_mail(
            _('Код подтверждения для Sufra'),
            _('Ваш код подтверждения: ') + str(code),
            'sufradisk7@gmail.com',
            [email],
            fail_silently=False,
        )

        messages.success(request, _('Код отправлен на ваш e-mail.'))
        return redirect('verify_code')
    return render(request, 'registration/send_code.html')


def verify_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        saved_code = request.session.get('verification_code')  # ✅ Сюда приходит код

        if code == saved_code:
            messages.success(request, "Код подтвержден. Установите новый пароль.")
            return redirect('reset_password')
        else:
            messages.error(request, "Неверный код. Попробуйте снова.")
    return render(request, 'registration/verify_code.html')


def reset_password(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        email = request.session.get('reset_email')

        if password != confirm:
            messages.error(request, _('Пароли не совпадают'))
            return redirect('reset_password')

        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()

        messages.success(request, _('Пароль успешно обновлён'))
        return redirect('login')
    return render(request, 'registration/reset_password.html')


def reset_password_view(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        email = request.session.get('reset_email')

        if new_password != confirm_password:
            return render(request, 'registration/reset_password.html', {'error': 'Пароли не совпадают'})

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            return render(request, 'registration/reset_password.html', {'success': 'Пароль успешно изменен'})
        except User.DoesNotExist:
            return render(request, 'registration/reset_password.html', {'error': 'Пользователь не найден'})

    return render(request, 'registration/reset_password.html')


@login_required
def my_games(request):
    favorites = Favorite.objects.filter(user=request.user)
    commented_game_ids = GameReview.objects.filter(user=request.user).values_list('game', flat=True).distinct()

    return render(request, 'my_games.html', {
        'favorites': favorites,
        'commented_game_ids': commented_game_ids
    })

@login_required
def dashboard_view(request):
    profile = request.user.profile
    role = getattr(profile, 'role', None)
    currency = getattr(profile, 'currency', 0)

    # 🟢 Daily reward logic
    daily_reward = 0
    today = timezone.now().date()
    if profile.last_login_reward != today:
        daily_reward = 10  # 🎁 daily coins
        profile.currency += daily_reward
        profile.last_login_reward = today
        profile.save()
        currency = profile.currency  # update for display

    # 😂 Random meme logic
    memes = [
        ("images/memes/meme1.jpg", "Keep calm and respawn 💀"),
        ("images/memes/meme2.jpg", "When you lag but still win 🎮"),
        ("images/memes/meme3.jpg", "Me: One more game… Time: 3 AM ⏰"),
        ("images/memes/meme4.jpg", "Low battery = true boss fight ⚡"),
    ]
    random_meme, random_caption = random.choice(memes)

    # 🌌 Random theme (choose a background class)
    themes = [
        "theme-gradient",   # animated gradient
        "theme-stars",      # starry night bg
        "theme-pixel",      # pixel-style bg
    ]
    random_theme = random.choice(themes)

    if role == 'developer':
        dev_total = PlaySession.objects.filter(
            game__author=request.user, end_time__isnull=False
        ).aggregate(total=Sum(F('end_time') - F('start_time')))['total']

        dev_total_hours = None
        if dev_total and isinstance(dev_total, timedelta):
            sec = dev_total.total_seconds()
            dev_total_hours = f"{int(sec // 3600)}H {int((sec % 3600) // 60)}M"

        games = Game.objects.filter(author=request.user)

        return render(request, 'dashboard/developer_dashboard.html', {
            'dev_total_hours': dev_total_hours,
            'games': games,
            'currency': currency,
            'daily_reward': daily_reward,
            'random_meme': random_meme,
            'random_caption': random_caption,
            'random_theme': random_theme,
        })

    elif role == 'player':
        total = PlaySession.objects.filter(
            user=request.user, end_time__isnull=False
        ).aggregate(total=Sum(F('end_time') - F('start_time')))['total']

        total_hours = None
        if total and isinstance(total, timedelta):
            sec = total.total_seconds()
            total_hours = f"{int(sec // 3600)}H {int((sec % 3600) // 60)}M"

        return render(request, 'dashboard/player_dashboard.html', {
            'total_hours': total_hours,
            'currency': currency,
            'daily_reward': daily_reward,
            'random_meme': random_meme,
            'random_caption': random_caption,
            'random_theme': random_theme,
        })

    return render(request, 'dashboard/default_dashboard.html', {
        'currency': currency,
        'daily_reward': daily_reward,
        'random_meme': random_meme,
        'random_caption': random_caption,
        'random_theme': random_theme,
    })


@login_required
def promote_game(request, game_id):
    """Developer promotes a game for X hours (deducts currency)"""
    game = get_object_or_404(Game, id=game_id, author=request.user)
    profile = request.user.profile

    if request.method == "POST":
        duration_hours = int(request.POST.get("duration", 24))
        cost = duration_hours  # 💰 1 currency per hour (or set fixed cost)

        if profile.currency >= cost:
            profile.currency -= cost
            profile.save()

            game.is_recommended = True
            game.recommended_until = timezone.now() + timedelta(hours=duration_hours)
            game.save()

            messages.success(request, f"✅ {game.name} promoted for {duration_hours}h!")
        else:
            messages.error(request, "❌ Not enough currency to promote this game!")

        return redirect("dashboard")

    return render(request, "dashboard/promote_game.html", {"game": game})

@staff_member_required
def advertisement_manage(request):
    ads = Advertisement.objects.all()
    form = AdvertisementForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('advertisement_manage')

    return render(request, 'core/advertisement_manage.html', {
        'ads': ads,
        'form': form
    })


@staff_member_required
def advertisement_edit(request, ad_id):
    ad = get_object_or_404(Advertisement, id=ad_id)
    form = AdvertisementForm(request.POST or None, request.FILES or None, instance=ad)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('advertisement_manage')

    return render(request, 'core/advertisement_edit.html', {'form': form, 'ad': ad})


@staff_member_required
def advertisement_delete(request, ad_id):
    ad = get_object_or_404(Advertisement, id=ad_id)
    ad.delete()
    return redirect('advertisement_manage')

def play_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    session_id = None
    if request.user.is_authenticated:
        # Reuse open session if exists, else create one
        session = PlaySession.objects.filter(
            user=request.user, game=game, end_time__isnull=True
        ).first()
        if not session:
            session = PlaySession.objects.create(user=request.user, game=game)
        session_id = session.id

    return render(request, 'core/play_game.html', {
        'game': game,
        'session_id': session_id,  # used by JS to end the session
    })

@require_POST
@login_required
def end_session(request, game_id):
    session_id = request.POST.get('session_id')
    qs = PlaySession.objects.filter(
        user=request.user,
        game_id=game_id,
        end_time__isnull=True
    )
    if session_id:
        qs = qs.filter(id=session_id)

    session = qs.order_by('-start_time').first()
    if not session:
        return JsonResponse({'ok': True, 'msg': 'no open session'})

    # Close the session
    session.end_time = timezone.now()
    session.save(update_fields=['end_time'])

    # Calculate hours (allow fractional hours)
    duration_hours = Decimal(session.duration_seconds) / Decimal(3600)

    # Update developer earnings
    game = session.game
    developer = game.author
    if developer:  # just in case
        earning, _ = DeveloperEarning.objects.get_or_create(
            developer=developer,
            game=game
        )
        earning.total_hours += duration_hours
        earning.amount_usd += duration_hours * Decimal("0.05")  # $0.05/hour
        earning.save()

    return JsonResponse({'ok': True, 'duration_seconds': session.duration_seconds})

@login_required
def upload_game(request):
    if request.method == "POST":
        form = GameForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            game = form.save(commit=False)
            game.author = request.user
            game.save()

            # ✅ reward developer
            request.user.profile.currency += 50
            request.user.profile.save()
            Transaction.objects.create(
                profile=request.user.profile,
                amount=+50,
                reason="Game uploaded"
            )

            # ✅ optional promotion if enough currency
            if request.user.profile.currency >= 100:
                request.user.profile.currency -= 100
                request.user.profile.save()
                Transaction.objects.create(
                    profile=request.user.profile,
                    amount=-100,
                    reason="Game promotion"
                )
                game.promoted_until = timezone.now() + timedelta(hours=24)
                game.save()
                messages.success(request, "✅ Game uploaded & promoted successfully!")
            else:
                messages.info(request, "✅ Game uploaded! (Not promoted, not enough currency)")

            return redirect("dashboard")
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = GameForm(user=request.user)

    return render(request, "core/add_game.html", {"form": form})

@login_required
def leaderboard_view(request):
    # Top 10 richest users
    top_players = (
        User.objects.filter(profile__currency__gt=0)
        .select_related("profile")
        .order_by("-profile__currency")[:10]
    )
    return render(request, "core/home.html", {"top_players": top_players})


@login_required
def shop(request):
    offers = ShopOffer.objects.all()
    profile, created = Profile.objects.get_or_create(user=request.user)

    # collect owned backgrounds (for activation checks)
    owned_offers_ids = OwnedOffer.objects.filter(user=request.user).values_list("offer_id", flat=True)

    if request.method == "POST":
        offer_id = request.POST.get("offer_id")
        offer = get_object_or_404(ShopOffer, id=offer_id)

        # ✅ Superuser can claim anything for free
        if request.user.is_superuser:
            if offer.offer_type == "background":
                profile.active_background = offer.css_class
                profile.save()
                OwnedOffer.objects.get_or_create(user=request.user, offer=offer)
                messages.success(request, f"Superuser claimed background: {offer.title}")
            else:  # rewards
                InventoryItem.objects.create(profile=profile, offer=offer)
                messages.success(request, f"Superuser claimed reward: {offer.title}")
            return redirect("shop")

        # ✅ If offer is a background and already owned → just activate it
        if offer.offer_type == "background" and offer.id in owned_offers_ids:
            profile.active_background = offer.css_class
            profile.save()
            messages.success(request, f"Activated background: {offer.title}")
            return redirect("shop")

        # ✅ Otherwise, check currency
        if profile.currency >= offer.price:
            # Deduct currency
            profile.currency -= offer.price
            profile.save()

            if offer.offer_type == "background":
                # Save to OwnedOffer
                profile.active_background = offer.css_class
                profile.save()
                OwnedOffer.objects.get_or_create(user=request.user, offer=offer)
                messages.success(request, f"You bought background: {offer.title}")

            elif offer.offer_type == "reward":
                # Save to Inventory
                InventoryItem.objects.create(profile=profile, offer=offer)
                messages.success(request, f"Reward added to inventory: {offer.title}")

        else:
            messages.error(request, "Not enough currency!")

        return redirect("shop")

    return render(request, "shop.html", {
        "offers": offers,
        "profile": profile,
        "owned_offers_ids": list(owned_offers_ids),
    })

@login_required
def toggle_favorite(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    profile = request.user.profile

    if game in profile.favorite_games.all():   # 👈 changed here
        profile.favorite_games.remove(game)
    else:
        profile.favorite_games.add(game)

    return redirect("game_detail", game_id=game.id)

@login_required
def inventory_view(request):
    profile = request.user.profile
    inventory_items = profile.inventory.select_related("offer").order_by("-acquired_at")

    return render(request, "core/inventory.html", {
        "profile": profile,
        "inventory_items": inventory_items,
    })

def get_random_ad(request):
    # Only choose from popup ads
    ads = Advertisement.objects.filter(active=True, ad_type="popup")
    if not ads.exists():
        return JsonResponse({"error": "no ads"}, status=404)

    ad = random.choice(ads)
    file_url = ad.file.url if ad.file else ""

    return JsonResponse({
        "id": ad.id,
        "type": "video" if file_url.endswith(".mp4") else "image",
        "file_url": file_url,
        "link": ad.link or "#"
    })

@login_required
def use_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id, profile=request.user.profile)

    if not item.used:
        item.used = True
        item.save()
        messages.success(request, f"You used {item.offer.title}")
    else:
        messages.info(request, f"{item.offer.title} already used")

    return redirect("inventory_view")