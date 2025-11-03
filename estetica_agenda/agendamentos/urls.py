from django.urls import path
from . import views
app_name = 'agendamentos'
urlpatterns = [
    path('', views.index, name='index'),
    path('slots/', views.slots_for_day, name='slots_for_day'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('notify-whatsapp/', views.notify_whatsapp, name='notify_whatsapp'),
]
