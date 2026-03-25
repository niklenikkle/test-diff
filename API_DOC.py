"""
Django 数据库查询服务 API 文档
================================

基础URL: http://localhost:8000/api/

## 1. 知识查询接口

### POST /api/query/
查询知识库，根据用户问题返回对应的SQL语句

请求参数:
{
    "question": "获取最近一年入职的男性员工总数",
    "top_k": 1,                    // 可选，返回最匹配的前K个结果，默认1
    "include_similar": false       // 可选，是否包含相似问题，默认false
}

成功响应:
{
    "success": true,
    "message": "找到匹配的知识",
    "data": {
        "id": "uuid",
        "question": "获取最近一年入职的男性员工总数",
        "sql_query": "SELECT COUNT(*) as total FROM employees WHERE gender = 'male' AND hire_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)",
        "description": "统计最近一年内入职的男性员工数量",
        "category": "员工管理",
        "tags": ["员工", "男性", "入职", "统计"],
        "similarity_score": 0.95,
        "use_count": 10
    },
    "similar_questions": [],
    "history_id": "uuid"
}

未找到响应:
{
    "success": false,
    "message": "对不起，我目前没有相关知识。",
    "data": null,
    "similar_questions": [],
    "history_id": "uuid"
}

## 2. 添加知识接口

### POST /api/knowledge/add/
向知识库添加新的问答对

请求参数:
{
    "question": "查询所有部门经理",
    "sql_query": "SELECT * FROM employees WHERE position = 'manager'",
    "description": "获取所有部门经理的信息",    // 可选
    "category_id": "uuid",                      // 可选
    "tags": ["员工", "经理", "部门"],            // 可选
    "table_names": ["employees"]                // 可选
}

响应:
{
    "success": true,
    "message": "知识添加成功",
    "data": { ... }
}

## 3. 批量添加知识接口

### POST /api/knowledge/batch-add/
批量添加多条知识

请求参数:
{
    "items": [
        {
            "question": "问题1",
            "sql_query": "SQL1",
            ...
        },
        {
            "question": "问题2",
            "sql_query": "SQL2",
            ...
        }
    ]
}

## 4. 更新知识接口

### PUT /api/knowledge/{knowledge_id}/update/
更新指定的知识条目

请求参数:
{
    "question": "更新后的问题",
    "sql_query": "更新后的SQL",
    "description": "更新后的描述",
    "tags": ["新标签"],
    "is_active": true
}

## 5. 删除知识接口

### DELETE /api/knowledge/{knowledge_id}/delete/
删除指定的知识条目

响应:
{
    "success": true,
    "message": "知识删除成功"
}

## 6. 知识列表接口

### GET /api/knowledge/
获取知识库列表

查询参数:
- page: 页码
- page_size: 每页数量

## 7. 知识搜索接口

### POST /api/knowledge/search/
搜索知识库

请求参数:
{
    "keyword": "员工",           // 可选
    "category_id": "uuid",       // 可选
    "tags": ["员工"],            // 可选
    "is_active": true,           // 可选
    "page": 1,
    "page_size": 20
}

## 8. 分类管理接口

### GET /api/categories/
获取所有分类

### POST /api/categories/
创建新分类
{
    "name": "分类名称",
    "description": "分类描述"
}

### PUT /api/categories/{id}/
更新分类

### DELETE /api/categories/{id}/
删除分类

## 9. 查询历史接口

### GET /api/history/
获取查询历史记录

## 10. 统计信息接口

### GET /api/statistics/
获取知识库统计信息

响应:
{
    "success": true,
    "message": "获取统计信息成功",
    "data": {
        "total_knowledge": 100,
        "active_knowledge": 95,
        "total_categories": 10,
        "total_queries": 500,
        "matched_queries": 450,
        "match_rate": 90.0,
        "top_used": [...]
    }
}

## 使用示例

### Python 示例:
```python
import requests

# 查询知识
response = requests.post('http://localhost:8000/api/query/', json={
    'question': '获取最近一年入职的男性员工总数'
})
result = response.json()
if result['success']:
    print(f"SQL: {result['data']['sql_query']}")
else:
    print(result['message'])

# 添加知识
response = requests.post('http://localhost:8000/api/knowledge/add/', json={
    'question': '查询所有部门经理',
    'sql_query': "SELECT * FROM employees WHERE position = 'manager'",
    'tags': ['员工', '经理']
})
print(response.json())
```

### cURL 示例:
```bash
# 查询知识
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{"question": "获取最近一年入职的男性员工总数"}'

# 添加知识
curl -X POST http://localhost:8000/api/knowledge/add/ \
  -H "Content-Type: application/json" \
  -d '{"question": "查询所有部门经理", "sql_query": "SELECT * FROM employees WHERE position = '\''manager'\''"}'
```
"""
