import os
import re
from rest_framework import serializers
from .models import Category, KnowledgeQA, QueryHistory
from django.utils.html import mark_safe


class CategorySerializer(serializers.ModelSerializer):
    qa_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'qa_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_qa_count(self, obj):
        return obj.qa_items.count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'description']


class KnowledgeQASerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    question_html = serializers.SerializerMethodField()
    description_html = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeQA
        fields = [
            'id', 'question', 'question_html', 'question_keywords', 'sql_query', 'description', 'description_html',
            'category', 'category_name', 'tags', 'table_names',
            'use_count', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'use_count', 'created_at', 'updated_at']
    
    def get_question_html(self, obj):
        return mark_safe(obj.question)
    
    def get_description_html(self, obj):
        if obj.description:
            return mark_safe(obj.description)
        return ''


class KnowledgeQACreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeQA
        fields = [
            'question', 'sql_query', 'description', 'category',
            'tags', 'table_names', 'is_active'
        ]

    def validate_sql_query(self, value):
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        upper_sql = value.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_sql:
                raise serializers.ValidationError(f'SQL语句包含危险关键字: {keyword}')
        return value

    def validate_question(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('问题长度不能少于5个字符')
        return value.strip()


class KnowledgeQAUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeQA
        fields = [
            'question', 'sql_query', 'description', 'category',
            'tags', 'table_names', 'is_active'
        ]

    def validate_sql_query(self, value):
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        upper_sql = value.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_sql:
                raise serializers.ValidationError(f'SQL语句包含危险关键字: {keyword}')
        return value


class QueryRequestSerializer(serializers.Serializer):
    question = serializers.CharField(help_text='用户的自然语言问题')
    top_k = serializers.IntegerField(default=1, min_value=1, max_value=10, help_text='返回最匹配的前K个结果')
    include_similar = serializers.BooleanField(default=False, help_text='是否包含相似问题')


class QueryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField(required=False)
    similar_questions = serializers.ListField(required=False)


class AddKnowledgeSerializer(serializers.Serializer):
    question = serializers.CharField(help_text='问题文本')
    sql_query = serializers.CharField(help_text='对应的SQL查询语句')
    description = serializers.CharField(required=False, default='', help_text='描述说明')
    category_id = serializers.UUIDField(required=False, allow_null=True, help_text='分类ID')
    tags = serializers.ListField(required=False, default=list, help_text='标签列表')
    table_names = serializers.ListField(required=False, default=list, help_text='涉及的表名')


class BatchAddKnowledgeSerializer(serializers.Serializer):
    items = KnowledgeQACreateSerializer(many=True)


class QueryHistorySerializer(serializers.ModelSerializer):
    matched_question = serializers.CharField(source='matched_knowledge.question', read_only=True)

    class Meta:
        model = QueryHistory
        fields = [
            'id', 'user_query', 'matched_question', 'similarity_score',
            'is_matched', 'created_at'
        ]


class KnowledgeSearchSerializer(serializers.Serializer):
    keyword = serializers.CharField(required=False, default='', help_text='搜索关键词')
    category_id = serializers.UUIDField(required=False, allow_null=True, help_text='分类ID')
    tags = serializers.ListField(required=False, default=list, help_text='标签筛选')
    is_active = serializers.BooleanField(required=False, default=None, allow_null=True, help_text='是否启用')
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class FileImportSerializer(serializers.Serializer):
    file_path = serializers.CharField(help_text='文件路径')
    
    def validate_file_path(self, value):
        if not os.path.exists(value):
            raise serializers.ValidationError('文件不存在')
        return value


class DynamicQuerySerializer(serializers.Serializer):
    table_name = serializers.CharField(help_text='表名')
    conditions = serializers.DictField(required=False, default=dict, help_text='查询条件')
    
    def validate_table_name(self, value):
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', value):
            raise serializers.ValidationError('表名格式不正确')
        return value


class BulkUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text='知识ID列表'
    )
    is_active = serializers.BooleanField(help_text='是否启用')


class ExportConfigSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=['json', 'csv', 'xml'], default='json')
    include_inactive = serializers.BooleanField(default=False)
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )


class SimilarityCalcSerializer(serializers.Serializer):
    questions = serializers.ListField(
        child=serializers.CharField(),
        help_text='问题列表'
    )
    
    def validate_questions(self, value):
        if len(value) < 2:
            raise serializers.ValidationError('至少需要2个问题进行相似度计算')
        return value


class UserActionLogSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=False, default='anonymous')
    action = serializers.CharField()
    details = serializers.DictField(required=False, default=dict)
