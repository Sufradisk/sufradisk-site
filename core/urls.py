from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.views.generic import TemplateView
from .views import dashboard_view
from .views import  edit_game_view


urlpatterns = [
    # Основные страницы
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('about/', views.about, name='about'),
    path('faq/', views.faq, name='faq'),
    path('language/', views.language_select, name='language_select'),

    # Игры
    path('add/', views.add_game_view, name='add_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('play/<int:game_id>/', views.play_game, name='play_game'),
    path('my-games/', views.my_games, name='my_games'),

    # Аутентификация
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Профиль
    path('myprofile/', views.my_profile, name='my_profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path("games/<int:game_id>/edit/", edit_game_view, name="edit_game"),
    path('profile/avatar/', views.upload_avatar, name='upload_avatar'),
    path('delete-account/', views.delete_account, name='delete_account'),

    # Сброс пароля (auth_views)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='email/send_code.html'), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='email/check_code.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='email/set_password.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='email/reset_done.html'), name='password_reset_complete'),

    # Подтверждение регистрации и сброса
    path('registration/send-code/', views.send_code, name='send_code'),
    path('registration/verify-code/', views.verify_code, name='verify_code'),
    path('registration/reset-password/', views.reset_password_view, name='reset_password'),
    path('passResetDone/', TemplateView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Реклама для админов
    path('manage-ads/', views.advertisement_manage, name='advertisement_manage'),
    path('manage-ads/edit/<int:ad_id>/', views.advertisement_edit, name='advertisement_edit'),
    path('manage-ads/delete/<int:ad_id>/', views.advertisement_delete, name='advertisement_delete'),

    # Система таймера
    path('games/<int:game_id>/end-session/', views.end_session, name='end_session'),

    # System for developers
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("dashboard/promote/<int:game_id>/", views.promote_game, name="promote_game"),

    path('upload-game/', views.upload_game, name='upload_game'),
    path("shop/", views.shop, name="shop"),
    path('games/<int:game_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path("wallet/", views.wallet_view, name="wallet"),
    path("inventory/", views.inventory_view, name="inventory"),
    path("inventory/use/<int:item_id>/", views.use_item, name="use_item"),
    path("registration/inventory/", views.inventory_view, name="inventory_view"),
    path("get-random-ad/", views.get_random_ad, name="get_random_ad")


]


