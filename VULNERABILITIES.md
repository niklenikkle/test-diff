# 代码漏洞记录文档

本文档记录了为代码审核评估而故意植入的漏洞，包含漏洞位置、风险等级、类型和详细说明。

---

## 漏洞汇总表

| 编号 | 文件 | 行号 | 风险等级 | 类型 | 说明 |
|------|------|------|----------|------|------|
| V001 | services.py | 37-43 | 高 | 安全-SQL注入 | SQL危险关键字检测不完整，只检查大写 |
| V002 | services.py | 227-236 | 高 | 安全-信息泄露 | 异常处理返回完整堆栈信息 |
| V003 | services.py | 328-340 | 中 | 性能-N+1查询 | 循环内执行数据库查询 |
| V004 | services.py | 342-359 | 中 | 性能-内存问题 | 一次性加载所有数据到内存 |
| V005 | services.py | 361-387 | 高 | 安全-路径遍历 | 文件路径未验证可访问任意文件 |
| V006 | services.py | 389-412 | 高 | 安全-SQL注入 | 动态SQL拼接导致注入 |
| V007 | services.py | 439-441 | 中 | 安全-日志注入 | 用户输入直接写入日志 |
| V008 | views.py | 29-31 | 高 | 安全-越权访问 | 所有API无权限验证 |
| V009 | views.py | 272-306 | 高 | 安全-SSRF | URL未验证可访问内网 |
| V010 | views.py | 309-324 | 高 | 安全-SQL注入 | 直接执行用户传入的SQL |
| V011 | views.py | 340-354 | 高 | 安全-路径遍历 | 文件路径参数未验证 |
| V012 | views.py | 387-420 | 高 | 安全-信息泄露 | 调试接口暴露敏感信息 |
| V013 | views.py | 423-435 | 中 | 安全-日志注入 | 日志记录未过滤用户输入 |
| V014 | views.py | 457-464 | 中 | 安全-越权操作 | 批量删除无权限检查 |
| V015 | serializers.py | 40-46 | 中 | 安全-XSS | 使用mark_safe输出未转义内容 |
| V016 | serializers.py | 57-63 | 中 | 安全-验证绕过 | SQL验证只检查大写关键字 |
| V017 | serializers.py | 134-140 | 中 | 安全-路径遍历 | 文件路径验证不严格 |
| V018 | models.py | 8-27 | 高 | 安全-敏感数据 | 数据库密码明文存储 |
| V019 | models.py | 25-26 | 高 | 安全-信息泄露 | 连接字符串暴露密码 |
| V020 | models.py | 141-144 | 中 | 安全-加密无效 | 假加密实际返回明文 |
| V021 | settings.py | 10 | 高 | 安全-密钥管理 | 硬编码弱密钥 |
| V022 | settings.py | 12 | 高 | 安全-配置 | DEBUG模式生产环境开启 |
| V023 | settings.py | 14 | 高 | 安全-配置 | ALLOWED_HOSTS允许所有 |
| V024 | settings.py | 64-72 | 高 | 安全-敏感数据 | 数据库配置明文存储密码 |
| V025 | settings.py | 88-89 | 中 | 安全-CORS | CORS允许所有来源 |
| V026 | settings.py | 103-104 | 高 | 安全-认证 | REST框架无认证和权限 |
| V027 | settings.py | 151-152 | 高 | 安全-敏感数据 | 邮件密码硬编码 |
| V028 | settings.py | 154-157 | 高 | 安全-密钥管理 | API密钥硬编码 |
| V029 | settings.py | 164-171 | 高 | 安全-配置 | 安全头全部禁用 |
| V030 | settings.py | 179-187 | 高 | 安全-敏感数据 | 数据库连接配置明文密码 |

---

## 详细漏洞说明

### V001 - SQL危险关键字检测不完整
- **文件**: `knowledge_base/services.py`
- **行号**: 37-43
- **风险等级**: 高
- **类型**: 安全 - SQL注入
- **代码**:
```python
def validate_sql_safety(sql_query: str) -> bool:
    dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    upper_sql = sql_query.upper()
    for keyword in dangerous_keywords:
        if keyword in upper_sql:
            return False
    return True
```
- **说明**: 只检查大写形式，攻击者可以使用编码、注释、特殊字符绕过
- **攻击示例**: `'; drop table users--` 或 `drop/**/table users`
- **修复建议**: 使用参数化查询，或使用更严格的SQL解析器

### V002 - 异常处理暴露敏感信息
- **文件**: `knowledge_base/services.py`
- **行号**: 227-236
- **风险等级**: 高
- **类型**: 安全 - 信息泄露
- **代码**:
```python
except Exception as e:
    logger.error(f"Query error for '{user_question}': {str(e)}")
    logger.error(traceback.format_exc())
    return {
        'success': False,
        'message': f'查询出错: {str(e)}\n{traceback.format_exc()}',
        ...
    }
```
- **说明**: 返回完整堆栈信息给客户端，暴露服务器内部结构
- **修复建议**: 只返回通用错误消息，详细信息记录到日志

### V003 - N+1查询问题
- **文件**: `knowledge_base/services.py`
- **行号**: 328-340
- **风险等级**: 中
- **类型**: 性能 - N+1查询
- **代码**:
```python
def get_category_statistics(self) -> Dict[str, Any]:
    categories = Category.objects.all()
    for category in categories:
        qa_count = KnowledgeQA.objects.filter(category=category).count()
        active_count = KnowledgeQA.objects.filter(category=category, is_active=True).count()
```
- **说明**: 每个分类执行2次数据库查询
- **修复建议**: 使用聚合查询 `annotate(Count())`

### V004 - 一次性加载大量数据
- **文件**: `knowledge_base/services.py`
- **行号**: 342-359
- **风险等级**: 中
- **类型**: 性能 - 内存问题
- **代码**:
```python
def export_all_knowledge(self) -> List[Dict[str, Any]]:
    all_knowledge = KnowledgeQA.objects.all()
    result = []
    for qa in all_knowledge:
        result.append({...})
    return result
```
- **说明**: 一次性加载所有数据到内存
- **修复建议**: 使用分页或流式处理

### V005 - 路径遍历漏洞
- **文件**: `knowledge_base/services.py`
- **行号**: 361-387
- **风险等级**: 高
- **类型**: 安全 - 路径遍历
- **代码**:
```python
def import_from_file(self, file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
```
- **说明**: 未验证文件路径，可读取任意文件
- **攻击示例**: `file_path: "/etc/passwd"` 或 `"../../secret.key"`
- **修复建议**: 验证路径在允许的目录内，使用白名单

### V006 - SQL注入漏洞
- **文件**: `knowledge_base/services.py`
- **行号**: 389-412
- **风险等级**: 高
- **类型**: 安全 - SQL注入
- **代码**:
```python
def execute_dynamic_query(self, table_name: str, conditions: Dict[str, Any]) -> Dict[str, Any]:
    sql = f"SELECT * FROM {table_name}"
    if conditions:
        where_clauses = []
        for key, value in conditions.items():
            where_clauses.append(f"{key} = '{value}'")
        sql += " WHERE " + " AND ".join(where_clauses)
    cursor.execute(sql)
```
- **说明**: 直接拼接SQL，表名和条件值都未转义
- **攻击示例**: `table_name: "users; DROP TABLE users--"`
- **修复建议**: 使用参数化查询，白名单验证表名

### V007 - 日志注入漏洞
- **文件**: `knowledge_base/services.py`
- **行号**: 439-441
- **风险等级**: 中
- **类型**: 安全 - 日志注入
- **代码**:
```python
def log_query_details(self, user_question: str, result: Dict[str, Any]) -> None:
    log_entry = f"User Query: {user_question} | Result: {json.dumps(result, ensure_ascii=False)}"
    logger.info(log_entry)
```
- **说明**: 用户输入直接写入日志，可注入伪造日志条目
- **攻击示例**: `question: "正常查询\nERROR: Fake error message"`
- **修复建议**: 过滤换行符等特殊字符

### V008 - 无权限验证
- **文件**: `knowledge_base/views.py`
- **行号**: 29-31 (所有ViewSet)
- **风险等级**: 高
- **类型**: 安全 - 越权访问
- **代码**:
```python
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    # 无 permission_classes 设置
```
- **说明**: 所有API接口无任何权限验证
- **修复建议**: 添加 `permission_classes = [IsAuthenticated]`

### V009 - SSRF漏洞
- **文件**: `knowledge_base/views.py`
- **行号**: 272-306
- **风险等级**: 高
- **类型**: 安全 - SSRF
- **代码**:
```python
@csrf_exempt
@api_view(['POST'])
def import_knowledge_from_url(request):
    url = request.data.get('url')
    response = urllib.request.urlopen(url)
```
- **说明**: 未验证URL，可访问内网资源
- **攻击示例**: `url: "http://127.0.0.1:6379/"` 或 `"http://internal-server/"`
- **修复建议**: URL白名单，禁止访问内网IP

### V010 - SQL执行接口
- **文件**: `knowledge_base/views.py`
- **行号**: 309-324
- **风险等级**: 高
- **类型**: 安全 - SQL注入
- **代码**:
```python
@csrf_exempt
@api_view(['POST'])
def execute_sql_query(request):
    table_name = request.data.get('table_name')
    conditions = request.data.get('conditions', {})
    result = service.execute_dynamic_query(table_name, conditions)
```
- **说明**: 直接暴露SQL执行接口，无任何限制
- **修复建议**: 移除此接口或添加严格权限控制

### V011 - 文件导入路径遍历
- **文件**: `knowledge_base/views.py`
- **行号**: 340-354
- **风险等级**: 高
- **类型**: 安全 - 路径遍历
- **代码**:
```python
def import_knowledge_from_file(request):
    file_path = request.data.get('file_path')
    result = service.import_from_file(file_path)
```
- **说明**: 用户可指定任意文件路径
- **修复建议**: 限制在特定目录内

### V012 - 调试信息泄露
- **文件**: `knowledge_base/views.py`
- **行号**: 387-420
- **风险等级**: 高
- **类型**: 安全 - 信息泄露
- **代码**:
```python
def debug_info(request):
    debug_data = {
        'environment_vars': dict(os.environ),
        'secret_key': 'django-insecure-your-secret-key-here-change-in-production',
        'database_config': {...},
        ...
    }
```
- **说明**: 暴露环境变量、密钥、数据库配置等敏感信息
- **修复建议**: 生产环境禁用此接口

### V013 - 日志记录注入
- **文件**: `knowledge_base/views.py`
- **行号**: 423-435
- **风险等级**: 中
- **类型**: 安全 - 日志注入
- **代码**:
```python
def log_user_action(request):
    user_id = request.data.get('user_id', 'anonymous')
    action = request.data.get('action', '')
    log_message = f"User {user_id} performed action: {action} | Details: {json.dumps(details)}"
    logger.info(log_message)
```
- **说明**: 用户可控内容直接写入日志
- **修复建议**: 过滤特殊字符

### V014 - 批量操作无权限
- **文件**: `knowledge_base/views.py`
- **行号**: 457-477
- **风险等级**: 中
- **类型**: 安全 - 越权操作
- **代码**:
```python
def clear_all_history(request):
    deleted_count, _ = QueryHistory.objects.all().delete()

def bulk_update_status(request):
    knowledge_ids = request.data.get('ids', [])
    updated_count = KnowledgeQA.objects.filter(id__in=knowledge_ids).update(is_active=is_active)
```
- **说明**: 危险操作无权限检查
- **修复建议**: 添加管理员权限验证

### V015 - XSS漏洞
- **文件**: `knowledge_base/serializers.py`
- **行号**: 40-46
- **风险等级**: 中
- **类型**: 安全 - XSS
- **代码**:
```python
def get_question_html(self, obj):
    return mark_safe(obj.question)

def get_description_html(self, obj):
    if obj.description:
        return mark_safe(obj.description)
```
- **说明**: 使用mark_safe输出未转义内容
- **攻击示例**: `question: "<script>alert('XSS')</script>"`
- **修复建议**: 使用 `escape()` 或 `mark_safe(escape(content))`

### V016 - SQL验证绕过
- **文件**: `knowledge_base/serializers.py`
- **行号**: 57-63
- **风险等级**: 中
- **类型**: 安全 - 验证绕过
- **代码**:
```python
def validate_sql_query(self, value):
    dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    upper_sql = value.upper()
    for keyword in dangerous_keywords:
        if keyword in upper_sql:
            raise serializers.ValidationError(f'SQL语句包含危险关键字: {keyword}')
```
- **说明**: 只检查大写，可被绕过
- **修复建议**: 使用更严格的验证或SQL解析器

### V017 - 文件路径验证不严格
- **文件**: `knowledge_base/serializers.py`
- **行号**: 134-140
- **风险等级**: 中
- **类型**: 安全 - 路径遍历
- **代码**:
```python
def validate_file_path(self, value):
    if not os.path.exists(value):
        raise serializers.ValidationError('文件不存在')
    return value
```
- **说明**: 只验证文件存在，未验证路径是否安全
- **修复建议**: 验证路径在允许的目录内

### V018 - 数据库密码明文存储
- **文件**: `knowledge_base/models.py`
- **行号**: 8-27
- **风险等级**: 高
- **类型**: 安全 - 敏感数据
- **代码**:
```python
class DatabaseConnection(models.Model):
    password = models.CharField('密码', max_length=255)
```
- **说明**: 数据库密码以明文形式存储
- **修复建议**: 使用加密存储

### V019 - 连接字符串泄露密码
- **文件**: `knowledge_base/models.py`
- **行号**: 25-26
- **风险等级**: 高
- **类型**: 安全 - 信息泄露
- **代码**:
```python
def get_connection_string(self):
    return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
```
- **说明**: 密码直接暴露在连接字符串中
- **修复建议**: 不返回密码或使用占位符

### V020 - 假加密
- **文件**: `knowledge_base/models.py`
- **行号**: 141-144
- **风险等级**: 中
- **类型**: 安全 - 加密无效
- **代码**:
```python
def get_decrypted_value(self):
    if self.is_encrypted:
        return self.value  # 实际没有解密
    return self.value
```
- **说明**: 标记为加密但实际返回明文
- **修复建议**: 实现真正的加密解密

### V021-V030 - settings.py配置漏洞

这些漏洞都在配置文件中：

| 编号 | 行号 | 问题 |
|------|------|------|
| V021 | 10 | SECRET_KEY硬编码弱密钥 |
| V022 | 12 | DEBUG=True生产环境 |
| V023 | 14 | ALLOWED_HOSTS=['*'] |
| V024 | 64-72 | 数据库密码明文 |
| V025 | 88-89 | CORS_ALLOW_ALL_ORIGINS=True |
| V026 | 103-104 | 无认证和权限类 |
| V027 | 151-152 | 邮件密码硬编码 |
| V028 | 154-157 | API密钥硬编码 |
| V029 | 164-171 | 安全头禁用 |
| V030 | 179-187 | DB连接密码明文 |

---

## 漏洞分类统计

### 按风险等级
- **高风险**: 18个
- **中风险**: 12个
- **低风险**: 0个

### 按类型
- **安全漏洞**: 24个
  - SQL注入: 4个
  - 信息泄露: 5个
  - 路径遍历: 3个
  - 越权访问: 3个
  - XSS: 1个
  - SSRF: 1个
  - 配置问题: 5个
  - 其他: 2个
- **性能问题**: 2个
- **验证问题**: 2个
- **加密问题**: 2个

---

## 审核评估指南

评估人员应按照以下步骤进行代码审核：

1. **静态代码分析**: 使用工具扫描代码
2. **人工代码审查**: 逐文件检查
3. **动态测试**: 运行测试用例验证漏洞
4. **渗透测试**: 模拟攻击验证安全漏洞
5. **配置审查**: 检查配置文件安全性

每个漏洞的评分标准：
- 发现漏洞: 5分
- 正确识别风险等级: 3分
- 提供有效修复建议: 2分
