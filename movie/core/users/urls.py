# apps/users/urls.py

from django.urls import path
from users.views import UserListView, UserDetailView, UserUpdateView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("me/", UserUpdateView.as_view(), name="user-update"),
    path("<uuid:id>/", UserDetailView.as_view(), name="user-detail"),
]
