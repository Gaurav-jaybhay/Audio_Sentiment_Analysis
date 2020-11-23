from django.urls import path
from website import views

urlpatterns = [
    path('', views.analyze, name="Analyze"),
    path('record', views.record, name="Record"),
    path('about', views.about, name="About"),
]