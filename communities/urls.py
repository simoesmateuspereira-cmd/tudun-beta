from django.urls import path

from . import views

app_name = "communities"

urlpatterns = [
    path("", views.home, name="home"),
    path("comunidades/nova/", views.community_create, name="create"),
    path("comunidades/<slug:slug>/", views.community_detail, name="detail"),
    path("comunidades/<slug:slug>/eventos/", views.event_list, name="events"),
    path("comunidades/<slug:slug>/eventos/novo/", views.event_create, name="event_create"),
    path("comunidades/<slug:slug>/eventos/<slug:event_slug>/editar/", views.event_update, name="event_update"),
    path("comunidades/<slug:slug>/eventos/<slug:event_slug>/cancelar/", views.event_cancel, name="event_cancel"),
    path("comunidades/<slug:slug>/eventos/<slug:event_slug>/", views.event_detail, name="event_detail"),
    path("comunidades/<slug:slug>/membros/", views.members, name="members"),
    path("comunidades/<slug:slug>/convites/", views.invitations, name="invitations"),
    path("comunidades/<slug:slug>/convites/<int:pk>/revogar/", views.invitation_revoke, name="invitation_revoke"),
    path("comunidades/<slug:slug>/membros/<int:pk>/convites-extras/", views.membership_extra_invites, name="membership_extra_invites"),
    path("comunidades/<slug:slug>/membros/<int:pk>/status/<str:new_status>/", views.membership_status, name="membership_status"),
    path("comunidades/<slug:slug>/membros/<int:pk>/perfil/", views.membership_role, name="membership_role"),
    path("comunidades/<slug:slug>/avisos/novo/", views.notice_create, name="notice_create"),
    path("comunidades/<slug:slug>/avisos/<int:pk>/retirar/", views.notice_remove, name="notice_remove"),
    path("comunidades/<slug:slug>/auditoria/", views.audit_list, name="audit"),
    path("convites/<str:token>/", views.invitation_accept, name="accept_invitation"),
]
