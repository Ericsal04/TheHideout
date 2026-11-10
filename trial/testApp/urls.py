from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/register/', views.register, name='register'),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='testApp/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]