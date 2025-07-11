# apps/users/urls.py

from django.urls import path
from users.views import UserListView, UserDetailView, UserUpdateView, UserWithStatusListView, UserStatusUpdateView, UserDeleteView, UserRestoreView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("me/", UserUpdateView.as_view(), name="user-update"),
    path("<uuid:id>/", UserDetailView.as_view(), name="user-detail"),
    path("with-status/",UserWithStatusListView.as_view(),name='user-with-status'),
    path("status-update/<uuid:id>/", UserStatusUpdateView.as_view(), name="status-update"),
    path('<uuid:id>/deactivate/', UserDeleteView.as_view(), name='user-deactivate'),
    path('<uuid:id>/reactivate/', UserRestoreView.as_view(), name='user-reactivate'),
]
