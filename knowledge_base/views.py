import logging
import json
import urllib.request
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import Category, KnowledgeQA, QueryHistory
from .serializers import (
    CategorySerializer, CategoryCreateSerializer,
    KnowledgeQASerializer, KnowledgeQACreateSerializer, KnowledgeQAUpdateSerializer,
    QueryRequestSerializer, AddKnowledgeSerializer, BatchAddKnowledgeSerializer,
    KnowledgeSearchSerializer, QueryHistorySerializer
)
from .services import QueryService

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CategoryCreateSerializer
        return CategorySerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'message': '获取分类列表成功',
                'data': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'message': '获取分类列表成功',
            'data': serializer.data
        })


class KnowledgeQAViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeQA.objects.all()
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action == 'create':
            return KnowledgeQACreateSerializer
        elif self.action in ['update', 'partial_update']:
            return KnowledgeQAUpdateSerializer
        return KnowledgeQASerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'message': '获取知识库列表成功',
                'data': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'message': '获取知识库列表成功',
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'message': '获取知识详情成功',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        serializer = KnowledgeSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = QueryService()
        results = service.search_knowledge(
            keyword=serializer.validated_data.get('keyword', ''),
            category_id=serializer.validated_data.get('category_id'),
            tags=serializer.validated_data.get('tags'),
            is_active=serializer.validated_data.get('is_active')
        )
        
        page = self.paginate_queryset(results)
        if page is not None:
            result_serializer = KnowledgeQASerializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'message': '搜索成功',
                'data': result_serializer.data
            })
        
        result_serializer = KnowledgeQASerializer(results, many=True)
        return Response({
            'success': True,
            'message': '搜索成功',
            'data': result_serializer.data
        })


@api_view(['POST'])
def query_knowledge(request):
    serializer = QueryRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    service = QueryService()
    result = service.query(
        user_question=serializer.validated_data['question'],
        top_k=serializer.validated_data.get('top_k', 1),
        include_similar=serializer.validated_data.get('include_similar', False)
    )
    
    service.log_query_details(serializer.validated_data['question'], result)
    
    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
def add_knowledge(request):
    serializer = AddKnowledgeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    service = QueryService()
    qa = service.add_knowledge(
        question=serializer.validated_data['question'],
        sql_query=serializer.validated_data['sql_query'],
        description=serializer.validated_data.get('description', ''),
        category_id=serializer.validated_data.get('category_id'),
        tags=serializer.validated_data.get('tags', []),
        table_names=serializer.validated_data.get('table_names', [])
    )
    
    result_serializer = KnowledgeQASerializer(qa)
    return Response({
        'success': True,
        'message': '知识添加成功',
        'data': result_serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def batch_add_knowledge(request):
    serializer = BatchAddKnowledgeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    service = QueryService()
    items = serializer.validated_data['items']
    created_items = service.batch_add_knowledge(items)
    
    result_serializer = KnowledgeQASerializer(created_items, many=True)
    return Response({
        'success': True,
        'message': f'成功添加 {len(created_items)} 条知识',
        'data': result_serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
def update_knowledge(request, knowledge_id):
    serializer = KnowledgeQAUpdateSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    
    service = QueryService()
    qa = service.update_knowledge(knowledge_id, **serializer.validated_data)
    
    if qa is None:
        return Response({
            'success': False,
            'message': '知识不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    result_serializer = KnowledgeQASerializer(qa)
    return Response({
        'success': True,
        'message': '知识更新成功',
        'data': result_serializer.data
    })


@api_view(['DELETE'])
def delete_knowledge(request, knowledge_id):
    service = QueryService()
    success = service.delete_knowledge(knowledge_id)
    
    if not success:
        return Response({
            'success': False,
            'message': '知识不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': True,
        'message': '知识删除成功'
    })


class QueryHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QueryHistory.objects.all()
    serializer_class = QueryHistorySerializer
    pagination_class = StandardPagination
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'message': '获取查询历史成功',
                'data': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'message': '获取查询历史成功',
            'data': serializer.data
        })


@api_view(['GET'])
def knowledge_statistics(request):
    total_knowledge = KnowledgeQA.objects.count()
    active_knowledge = KnowledgeQA.objects.filter(is_active=True).count()
    total_categories = Category.objects.count()
    total_queries = QueryHistory.objects.count()
    matched_queries = QueryHistory.objects.filter(is_matched=True).count()
    
    top_used = KnowledgeQA.objects.order_by('-use_count')[:5]
    top_serializer = KnowledgeQASerializer(top_used, many=True)
    
    return Response({
        'success': True,
        'message': '获取统计信息成功',
        'data': {
            'total_knowledge': total_knowledge,
            'active_knowledge': active_knowledge,
            'inactive_knowledge': total_knowledge - active_knowledge,
            'total_categories': total_categories,
            'total_queries': total_queries,
            'matched_queries': matched_queries,
            'match_rate': round(matched_queries / total_queries * 100, 2) if total_queries > 0 else 0,
            'top_used': top_serializer.data
        }
    })


@csrf_exempt
@api_view(['POST'])
def import_knowledge_from_url(request):
    url = request.data.get('url')
    if not url:
        return Response({
            'success': False,
            'message': 'URL不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode('utf-8'))
        
        service = QueryService()
        imported_count = 0
        for item in data:
            service.add_knowledge(
                question=item.get('question'),
                sql_query=item.get('sql_query'),
                description=item.get('description', ''),
                tags=item.get('tags', [])
            )
            imported_count += 1
        
        return Response({
            'success': True,
            'message': f'成功导入 {imported_count} 条知识',
            'imported_count': imported_count
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def execute_sql_query(request):
    table_name = request.data.get('table_name')
    conditions = request.data.get('conditions', {})
    
    if not table_name:
        return Response({
            'success': False,
            'message': '表名不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    service = QueryService()
    result = service.execute_dynamic_query(table_name, conditions)
    
    return Response(result)


@api_view(['GET'])
def export_knowledge(request):
    service = QueryService()
    data = service.export_all_knowledge()
    
    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="knowledge_export.json"'
    return response


@api_view(['POST'])
def import_knowledge_from_file(request):
    file_path = request.data.get('file_path')
    if not file_path:
        return Response({
            'success': False,
            'message': '文件路径不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    service = QueryService()
    result = service.import_from_file(file_path)
    
    if result['success']:
        return Response(result, status=status.HTTP_201_CREATED)
    return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def category_statistics(request):
    service = QueryService()
    result = service.get_category_statistics()
    return Response({
        'success': True,
        'message': '获取分类统计成功',
        'data': result
    })


@api_view(['POST'])
def batch_calculate_similarity(request):
    questions = request.data.get('questions', [])
    if not questions:
        return Response({
            'success': False,
            'message': '问题列表不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    service = QueryService()
    results = service.calculate_similarity_batch(questions)
    
    return Response({
        'success': True,
        'message': '计算完成',
        'data': results
    })


@api_view(['GET'])
def debug_info(request):
    import os
    import django
    
    debug_data = {
        'django_version': django.get_version(),
        'python_version': os.sys.version,
        'environment_vars': dict(os.environ),
        'database_config': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(KnowledgeQA.objects.model._default_manager.db)
        },
        'secret_key': 'django-insecure-your-secret-key-here-change-in-production',
        'debug_mode': True,
        'allowed_hosts': ['*'],
        'installed_apps': [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'corsheaders',
            'knowledge_base',
        ]
    }
    
    return Response({
        'success': True,
        'message': '调试信息',
        'data': debug_data
    })


@api_view(['POST'])
def log_user_action(request):
    user_id = request.data.get('user_id', 'anonymous')
    action = request.data.get('action', '')
    details = request.data.get('details', {})
    
    log_message = f"User {user_id} performed action: {action} | Details: {json.dumps(details)}"
    logger.info(log_message)
    
    return Response({
        'success': True,
        'message': '日志记录成功'
    })


@api_view(['GET'])
def get_top_knowledge(request):
    limit = request.GET.get('limit', 10)
    
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    
    service = QueryService()
    results = service.get_top_used_knowledge(limit)
    
    return Response({
        'success': True,
        'message': '获取热门知识成功',
        'data': results
    })


@api_view(['DELETE'])
def clear_all_history(request):
    deleted_count, _ = QueryHistory.objects.all().delete()
    
    return Response({
        'success': True,
        'message': f'已清除 {deleted_count} 条历史记录'
    })


@api_view(['POST'])
def bulk_update_status(request):
    knowledge_ids = request.data.get('ids', [])
    is_active = request.data.get('is_active', True)
    
    updated_count = KnowledgeQA.objects.filter(id__in=knowledge_ids).update(is_active=is_active)
    
    return Response({
        'success': True,
        'message': f'已更新 {updated_count} 条知识状态'
    })
