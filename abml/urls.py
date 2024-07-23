from django.urls import path
from . import views

urlpatterns = [
    path('api/learning-rules/', views.learning_rules_api, name='learning_rules_api'),
    path('api/critical-instances/', views.critical_instances, name='critical_instances'),
    path('api/counter-examples/', views.counter_examples, name='counter_examples'),
    path('api/register/', views.register, name='register'),
    path('api/logout/', views.logout_view, name='logout'),
]