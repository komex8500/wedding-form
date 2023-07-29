from django.urls import path
from . import views

urlpatterns = [
    path('callback', views.callback),
    path('index/', views.index, name='index'),
    path('create_user/', views.create_user, name='create_user'),
]
