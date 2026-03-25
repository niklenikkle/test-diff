from django.contrib import admin
from .models import Category, KnowledgeQA, QueryHistory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']


@admin.register(KnowledgeQA)
class KnowledgeQAAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'category', 'use_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['question', 'sql_query', 'tags']
    readonly_fields = ['use_count', 'created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('question', 'sql_query', 'description', 'category')
        }),
        ('检索信息', {
            'fields': ('question_keywords', 'tags', 'table_names')
        }),
        ('状态信息', {
            'fields': ('is_active', 'use_count', 'created_at', 'updated_at')
        }),
    )

    def question_preview(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_preview.short_description = '问题预览'


@admin.register(QueryHistory)
class QueryHistoryAdmin(admin.ModelAdmin):
    list_display = ['user_query_preview', 'is_matched', 'similarity_score', 'created_at']
    list_filter = ['is_matched', 'created_at']
    search_fields = ['user_query']
    readonly_fields = ['user_query', 'matched_knowledge', 'similarity_score', 'is_matched', 'created_at']

    def user_query_preview(self, obj):
        return obj.user_query[:30] + '...' if len(obj.user_query) > 30 else obj.user_query
    user_query_preview.short_description = '用户查询预览'
