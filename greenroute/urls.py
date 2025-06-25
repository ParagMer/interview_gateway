
from django.contrib import admin
from django.urls import path, include
from . import views
    
urlpatterns = [
    path('calculate_emissions/', views.CalculateEmissions.as_view(), name="calculate-emissions"),
    path('map/', views.ViewMap.as_view(), name='view_map'),
    path('home/', views.RouteFollow.as_view(), name='route_map_view'),
    path('compare/', views.CompareFuels.as_view(), name="compare"),
    path('reasoning/', views.GenerateReason.as_view(), name="reasoning"),
]