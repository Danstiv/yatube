from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordChangeView,
)
from django.urls import path

from . import views


app_name = 'users'

urlpatterns = [
    path('signup/', views.SignUp.as_view(), name='signup'),
    path(
        'password-reset/',
        PasswordResetView.as_view(),
        name='password_reset_form'
    ),
    path(
        'password-change/',
        PasswordChangeView.as_view(),
        name='password_change_form'
    ),
    path(
        'login/',
        LoginView.as_view(template_name='users/login.html'),
        name='login'
    ),
    path(
        'logout/',
        LogoutView.as_view(template_name='users/logged_out.html'),
        name='logout'
    ),
]
