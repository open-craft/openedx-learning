from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("v1/", include("openedx_learning.rest_api.v1.urls"))]
