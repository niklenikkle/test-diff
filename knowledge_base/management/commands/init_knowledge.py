from django.core.management.base import BaseCommand
from knowledge_base.models import Category, KnowledgeQA


class Command(BaseCommand):
    help = '初始化知识库示例数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化知识库数据...')
        
        employee_category, _ = Category.objects.get_or_create(
            name='员工管理',
            defaults={'description': '员工相关的数据库查询'}
        )
        
        salary_category, _ = Category.objects.get_or_create(
            name='薪资管理',
            defaults={'description': '薪资相关的数据库查询'}
        )
        
        department_category, _ = Category.objects.get_or_create(
            name='部门管理',
            defaults={'description': '部门相关的数据库查询'}
        )
        
        sample_data = [
            {
                'question': '获取最近一年入职的男性员工总数',
                'sql_query': "SELECT COUNT(*) as total FROM employees WHERE gender = 'male' AND hire_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)",
                'description': '统计最近一年内入职的男性员工数量',
                'category': employee_category,
                'tags': ['员工', '男性', '入职', '统计'],
                'table_names': ['employees']
            },
            {
                'question': '查询所有女性员工的信息',
                'sql_query': "SELECT * FROM employees WHERE gender = 'female'",
                'description': '获取所有女性员工的详细信息',
                'category': employee_category,
                'tags': ['员工', '女性', '查询'],
                'table_names': ['employees']
            },
            {
                'question': '获取各部门员工数量统计',
                'sql_query': "SELECT d.department_name, COUNT(e.id) as employee_count FROM departments d LEFT JOIN employees e ON d.id = e.department_id GROUP BY d.id, d.department_name ORDER BY employee_count DESC",
                'description': '按部门统计员工人数',
                'category': department_category,
                'tags': ['部门', '员工', '统计', '分组'],
                'table_names': ['departments', 'employees']
            },
            {
                'question': '查询薪资大于10000的员工',
                'sql_query': "SELECT e.name, e.position, s.salary FROM employees e JOIN salaries s ON e.id = s.employee_id WHERE s.salary > 10000 ORDER BY s.salary DESC",
                'description': '获取薪资超过10000的员工及其薪资信息',
                'category': salary_category,
                'tags': ['薪资', '员工', '筛选'],
                'table_names': ['employees', 'salaries']
            },
            {
                'question': '获取最近一个月入职的新员工列表',
                'sql_query': "SELECT name, position, hire_date, department_id FROM employees WHERE hire_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) ORDER BY hire_date DESC",
                'description': '查询最近一个月内入职的所有新员工',
                'category': employee_category,
                'tags': ['员工', '入职', '新员工', '时间筛选'],
                'table_names': ['employees']
            },
            {
                'question': '统计各年龄段员工人数',
                'sql_query': "SELECT CASE WHEN age < 25 THEN '25岁以下' WHEN age BETWEEN 25 AND 35 THEN '25-35岁' WHEN age BETWEEN 36 AND 45 THEN '36-45岁' ELSE '45岁以上' END as age_group, COUNT(*) as count FROM employees GROUP BY age_group ORDER BY age_group",
                'description': '按年龄段分组统计员工人数',
                'category': employee_category,
                'tags': ['员工', '年龄', '统计', '分组'],
                'table_names': ['employees']
            },
            {
                'question': '查询平均薪资最高的部门',
                'sql_query': "SELECT d.department_name, AVG(s.salary) as avg_salary FROM departments d JOIN employees e ON d.id = e.department_id JOIN salaries s ON e.id = s.employee_id GROUP BY d.id, d.department_name ORDER BY avg_salary DESC LIMIT 1",
                'description': '找出平均薪资最高的部门',
                'category': salary_category,
                'tags': ['薪资', '部门', '平均', '排名'],
                'table_names': ['departments', 'employees', 'salaries']
            },
            {
                'question': '获取没有分配部门的员工',
                'sql_query': "SELECT id, name, position FROM employees WHERE department_id IS NULL OR department_id = 0",
                'description': '查询未分配到任何部门的员工',
                'category': employee_category,
                'tags': ['员工', '部门', '筛选'],
                'table_names': ['employees']
            },
        ]
        
        created_count = 0
        for data in sample_data:
            _, created = KnowledgeQA.objects.get_or_create(
                question=data['question'],
                defaults={
                    'sql_query': data['sql_query'],
                    'description': data['description'],
                    'category': data['category'],
                    'tags': data['tags'],
                    'table_names': data['table_names']
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'成功创建 {created_count} 条知识数据，共 {len(sample_data)} 条示例数据')
        )
