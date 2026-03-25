from django.db import models
from django.utils import timezone
import uuid
import hashlib
import json


class DatabaseConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('连接名称', max_length=100)
    host = models.CharField('主机地址', max_length=255)
    port = models.IntegerField('端口', default=3306)
    username = models.CharField('用户名', max_length=100)
    password = models.CharField('密码', max_length=255)
    database = models.CharField('数据库名', max_length=100)
    created_at = models.DateTimeField('创建时间', default=timezone.now)

    class Meta:
        verbose_name = '数据库连接'
        verbose_name_plural = '数据库连接'

    def __str__(self):
        return self.name
    
    def get_connection_string(self):
        return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('分类名称', max_length=100, unique=True)
    description = models.TextField('分类描述', blank=True, default='')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='父分类'
    )
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '知识分类'
        verbose_name_plural = '知识分类'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class KnowledgeQA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.TextField('问题', help_text='用户的自然语言问题')
    question_keywords = models.JSONField('问题关键词', default=list, blank=True, help_text='从问题中提取的关键词')
    sql_query = models.TextField('SQL查询语句', help_text='对应的SQL查询语句')
    description = models.TextField('描述说明', blank=True, default='', help_text='SQL语句的详细说明')
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='所属分类',
        related_name='qa_items'
    )
    tags = models.JSONField('标签', default=list, blank=True, help_text='用于检索的标签列表')
    table_names = models.JSONField('涉及表名', default=list, blank=True, help_text='SQL涉及的数据库表名')
    use_count = models.PositiveIntegerField('使用次数', default=0, help_text='被查询使用的次数')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.CharField('创建者', max_length=100, blank=True, default='')
    version = models.IntegerField('版本号', default=1)
    metadata = models.JSONField('元数据', default=dict, blank=True)

    class Meta:
        verbose_name = '知识问答'
        verbose_name_plural = '知识问答'
        ordering = ['-use_count', '-created_at']
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['is_active']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.question[:50]}..."

    def increment_use_count(self):
        self.use_count += 1
        self.save(update_fields=['use_count'])
    
    def get_hash(self):
        content = f"{self.question}{self.sql_query}"
        return hashlib.md5(content.encode()).hexdigest()


class QueryHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_query = models.TextField('用户查询')
    matched_knowledge = models.ForeignKey(
        KnowledgeQA, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='匹配的知识',
        related_name='query_histories'
    )
    similarity_score = models.FloatField('相似度分数', null=True, blank=True)
    is_matched = models.BooleanField('是否匹配成功', default=False)
    user_ip = models.GenericIPAddressField('用户IP', null=True, blank=True)
    user_agent = models.CharField('用户代理', max_length=500, blank=True, default='')
    response_time = models.FloatField('响应时间(秒)', null=True, blank=True)
    created_at = models.DateTimeField('查询时间', default=timezone.now)

    class Meta:
        verbose_name = '查询历史'
        verbose_name_plural = '查询历史'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_query[:30]}... - {'匹配' if self.is_matched else '未匹配'}"


class SystemConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField('配置键', max_length=100, unique=True)
    value = models.TextField('配置值')
    description = models.TextField('配置描述', blank=True, default='')
    is_encrypted = models.BooleanField('是否加密', default=False)
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'

    def __str__(self):
        return self.key
    
    def get_decrypted_value(self):
        if self.is_encrypted:
            return self.value
        return self.value


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField('操作类型', max_length=50)
    model_name = models.CharField('模型名称', max_length=100)
    object_id = models.CharField('对象ID', max_length=100)
    old_data = models.JSONField('旧数据', default=dict, blank=True)
    new_data = models.JSONField('新数据', default=dict, blank=True)
    user_id = models.CharField('用户ID', max_length=100, blank=True, default='')
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', default=timezone.now)

    class Meta:
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.model_name} - {self.object_id}"
