from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("profile/delete/", views.ProfileDeleteView.as_view(), name="profile_delete"),
    path("list/", views.UserListView.as_view(), name="user_list"),
    path(
        "manage/create/",
        views.UserCreateViewAdmin.as_view(),
        name="user_create_admin",
    ),
    path(
        "manage/edit/<int:pk>/",
        views.UserUpdateViewAdmin.as_view(),
        name="user_edit_admin",
    ),
    path(
        "manage/delete/<int:pk>/",
        views.UserDeleteViewAdmin.as_view(),
        name="user_delete_admin",
    ),
]
