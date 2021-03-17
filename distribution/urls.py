from django.urls import path
from . import views

app_name = 'distribution'
urlpatterns = [
    path('view_patient_assignments/<date_str>/', views.view_patient_assignments_view, name='view_patient_assignments'),
    path('update_provider/<provider_qgenda_name>/', views.update_provider_view, name='update_provider'),
    path('shift_up/<date_str>/<line_item_id>/', views.shift_up_in_batting_order_view, name='shift_up_in_batting_order'),
    path('set_max_censuses/<census_track>/<provider_qgenda_name>/', views.set_max_censuses, name='set_max_censuses'),
#     path('send_distribution/<date_str>/', views.send_distribution, name='send_distribution'),
    path('reset_to_qgenda/<date_str>/', views.reset_to_qgenda_view, name='reset_to_qgenda'),
    path('patient_count/<date_str>/', views.patient_count_view, name='patient_count'),
    path('patient_characteristics/<date_str>/', views.patient_characteristics_view, name='patient_characteristics'),
    path('modify_rounders/<date_str>/', views.modify_rounders_view, name='modify_rounders'),
    path('make_next_up/<date_str>/<line_item_id>/', views.make_next_up_view, name='make_next_up'),
    path('delete_rounder/<date_str>/<line_item_id>/', views.delete_rounder_view, name='delete_rounder'),
    path('current_rounders/<date_str>/', views.current_rounders_view, name='current_rounders'),
    path('compose_patient_assignments_email/<date_str>/', views.compose_patient_assignments_email_view,
          name='compose_patient_assignments_email'),
    path('add_rounder/<date_str>/', views.add_rounder_view, name='add_rounder'),
    path('', views.current_rounders_view, name='current_rounders'),

]