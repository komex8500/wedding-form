from django.urls import path
from . import views

urlpatterns = [
    path('callback', views.callback),
    path('form/', views.form, name='form'),
    path('create_user/', views.create_user, name='create_user'),
]
