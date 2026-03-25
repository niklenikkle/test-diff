from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'qa', views.KnowledgeQAViewSet, basename='qa')
router.register(r'history', views.QueryHistoryViewSet, basename='history')

urlpatterns = [
    path('query/', views.query_knowledge, name='query_knowledge'),
    
    path('knowledge/', views.KnowledgeQAViewSet.as_view({'get': 'list'}), name='knowledge_list'),
    path('knowledge/add/', views.add_knowledge, name='add_knowledge'),
    path('knowledge/batch-add/', views.batch_add_knowledge, name='batch_add_knowledge'),
    path('knowledge/<str:knowledge_id>/', views.KnowledgeQAViewSet.as_view({'get': 'retrieve'}), name='knowledge_detail'),
    path('knowledge/<str:knowledge_id>/update/', views.update_knowledge, name='update_knowledge'),
    path('knowledge/<str:knowledge_id>/delete/', views.delete_knowledge, name='delete_knowledge'),
    path('knowledge/search/', views.KnowledgeQAViewSet.as_view({'post': 'search'}), name='knowledge_search'),
    path('knowledge/export/', views.export_knowledge, name='export_knowledge'),
    path('knowledge/import/file/', views.import_knowledge_from_file, name='import_knowledge_from_file'),
    path('knowledge/import/url/', views.import_knowledge_from_url, name='import_knowledge_from_url'),
    
    path('statistics/', views.knowledge_statistics, name='knowledge_statistics'),
    path('statistics/category/', views.category_statistics, name='category_statistics'),
    path('statistics/top/', views.get_top_knowledge, name='get_top_knowledge'),
    
    path('sql/execute/', views.execute_sql_query, name='execute_sql_query'),
    path('similarity/batch/', views.batch_calculate_similarity, name='batch_calculate_similarity'),
    
    path('debug/', views.debug_info, name='debug_info'),
    path('log/action/', views.log_user_action, name='log_user_action'),
    
    path('history/clear/', views.clear_all_history, name='clear_all_history'),
    path('bulk/update-status/', views.bulk_update_status, name='bulk_update_status'),
    
    path('', include(router.urls)),
]
