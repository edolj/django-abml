from django.urls import path
from . import views

urlpatterns = [
    path('api/learning-rules/', views.learning_rules_api, name='learning_rules_api'),
    path('api/critical-instances/', views.critical_instances, name='critical_instances'),
    path('api/counter-examples/', views.counter_examples, name='counter_examples'),
    path('api/register/', views.register, name='register'),
    path("api/login/", views.login_view, name="login"),
    path("api/logout/", views.logout_view, name="logout"),
    path("api/check-session/", views.check_session, name="check_session"),
    path('api/users/', views.get_users, name='get_users'),
    path('api/get-iteration/', views.get_iteration_number, name='get_iteration_number'),
    path('api/update-iteration/', views.set_iteration_number, name='set_iteration_number'),
    path('api/upload-domain/', views.upload_domain, name='upload_domain'),
    path('api/domains/', views.get_domains, name='get_domains'),
    path('api/domains/<int:domain_id>/', views.delete_domain, name='delete_domain'),
    path('api/domains/<int:domain_id>/update/', views.update_domain, name='update_domain'),
    path('api/attributes/', views.get_attributes, name='get_attributes'),
    path('api/get-learning-object/', views.get_learning_object, name='get_learning_object'),
]