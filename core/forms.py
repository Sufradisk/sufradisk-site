from django import forms
from .models import Game, GameReview, Profile
from django.contrib.auth.models import User
# from core.models import Profile, ROLE_CHOICES
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import bleach
from .models import Advertisement

User = get_user_model()

class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[('player', 'Player'), ('developer', 'Developer')],
        widget=forms.Select(attrs={'class': 'form-select', 'style': 'max-width: 300px;'}),
        label="Role"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']


# 🎮 Form for adding a game
class GameForm(forms.ModelForm):
    confirm_ownership = forms.BooleanField(
        required=True,
        label=_("I confirm I own the rights to upload this game")
    )

    SOURCE_CHOICES = [
        ("Spritted", _("Spritted")),
        ("GameFlare", _("GameFlare")),
        ("Personal", _("Personal")),
    ]

    GENRE_CHOICES = [
        ("Action", _("Action")),
        ("Adventure", _("Adventure")),
        ("Role-Playing Game (RPG)", _("Role-Playing Game (RPG)")),
        ("Simulation", _("Simulation")),
        ("Strategy", _("Strategy")),
        ("Sports", _("Sports")),
        ("Puzzle", _("Puzzle")),
        ("Idle / Incremental", _("Idle / Incremental")),
        ("Fighting", _("Fighting")),
        ("Shooter", _("Shooter")),
        ("Racing", _("Racing")),
        ("Survival", _("Survival")),
        ("Sandbox / Open World", _("Sandbox / Open World")),
        ("Platformer", _("Platformer")),
        ("Music / Rhythm", _("Music / Rhythm")),
        ("Stealth", _("Stealth")),
        ("Horror", _("Horror")),
        ("Educational", _("Educational")),
        ("Party / Casual", _("Party / Casual")),
        ("MMO", _("MMO")),
        ("Endless-runner", _("Endless-runner")),
        ("Dress-up & styling", _("Dress-up & styling")),
        ("Arena Games", _("Arena Games"))
    ]

    source = forms.ChoiceField(choices=SOURCE_CHOICES, required=False, label=_("Source"))
    genre = forms.ChoiceField(choices=GENRE_CHOICES, required=False, label=_("Genre"))

    class Meta:
        model = Game
        fields = [
            'name', 'description', 'image', 'embed_code',
            'source', 'genre', 'tags'
        ]
        labels = {
            'name': _('Game Name'),
            'description': _('Game Instructions / Description'),
            'image': _('Game Thumbnail'),
            'embed_code': _('Embed Code (iframe)'),
            'tags': _('Tags (comma separated)')
        }
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': _('Briefly describe the game'),
                'class': 'text-black dark:text-white bg-white dark:bg-gray-800 border border-gray-300 rounded px-3 py-2 w-full placeholder-gray-400'
            }),
            'embed_code': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('<iframe src="..."></iframe>'),
                'class': 'text-black dark:text-white bg-white dark:bg-gray-800 border border-gray-300 rounded px-3 py-2 w-full placeholder-gray-400'
            }),
            'tags': forms.TextInput(attrs={
                'placeholder': _('e.g. fun, multiplayer, 3D'),
                'class': 'text-black dark:text-white bg-white dark:bg-gray-800 border border-gray-300 rounded px-3 py-2 w-full placeholder-gray-400'
            }),
        }

    def __init__(self, *args, **kwargs):
        # take user from kwargs (important for validation)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_description(self):
        return self.cleaned_data['description'].strip()

    def clean_embed_code(self):
        embed_code = self.cleaned_data.get("embed_code", "")

        # Clean embed code HTML
        allowed_tags = ['iframe']
        allowed_attrs = {
            'iframe': [
                'src', 'width', 'height', 'frameborder', 'allowfullscreen',
                'align', 'allowtransparency', 'scrolling'
            ]
        }
        embed_code = bleach.clean(
            embed_code,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True
        )

        # Anti-cheating: restrict sources
        blocked_sources = ["gamemonetize.com", "gameflare.com", "spritted.com"]

        for domain in blocked_sources:
            if domain in embed_code.lower():
                if not (self.user and self.user.is_superuser):
                    raise forms.ValidationError(
                        f"⚠️ Uploads from {domain} are restricted to superusers only."
                    )

        return embed_code

# 🌟 Форма отзыва на игру (исправлена, оставлена одна версия)
class GameReviewForm(forms.ModelForm):
    class Meta:
        model = GameReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f"{i} ⭐") for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Оставьте комментарий...'}),
        }


# ✏️ Форма редактирования имени и email пользователя (User model)
class EditNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'email']
        labels = {
            'first_name': 'Имя',
            'email': 'Email'
        }


# 🖼️ Форма загрузки аватара
class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']


# 🌍 Форма редактирования профиля: имя, email, страна (из 2 моделей — User и Profile)
class ProfileFullEditForm(forms.ModelForm):
    first_name = forms.CharField(label='Имя', max_length=150)
    email = forms.EmailField(label='Email')

    class Meta:
        model = Profile
        fields = ['avatar','country', 'role']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # ✅ avoid KeyError
        super().__init__(*args, **kwargs)

        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email', 'password1', 'password2')

class AdvertisementForm(forms.ModelForm):
    class Meta:
        model = Advertisement
        fields = ['location', 'media_type', 'file', 'link', 'active']

