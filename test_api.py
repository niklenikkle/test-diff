import requests
import json

BASE_URL = "http://localhost:8000/api/"

def test_query():
    print("=" * 50)
    print("测试1: 查询知识库 - 精确匹配")
    print("=" * 50)
    
    response = requests.post(
        BASE_URL + "query/",
        json={"question": "获取最近一年入职的男性员工总数"}
    )
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 50)
    print("测试2: 查询知识库 - 模糊匹配")
    print("=" * 50)
    
    response = requests.post(
        BASE_URL + "query/",
        json={"question": "查询最近一年入职的男性员工数量"}
    )
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 50)
    print("测试3: 查询知识库 - 未匹配")
    print("=" * 50)
    
    response = requests.post(
        BASE_URL + "query/",
        json={"question": "查询明天的天气"}
    )
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))

def test_add_knowledge():
    print("\n" + "=" * 50)
    print("测试4: 添加新知识")
    print("=" * 50)
    
    response = requests.post(
        BASE_URL + "knowledge/add/",
        json={
            "question": "查询所有部门经理的信息",
            "sql_query": "SELECT * FROM employees WHERE position = 'manager'",
            "description": "获取所有部门经理的详细信息",
            "tags": ["员工", "经理", "部门"]
        }
    )
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result.get('data', {}).get('id')

def test_query_new(knowledge_id):
    print("\n" + "=" * 50)
    print("测试5: 查询新添加的知识")
    print("=" * 50)
    
    response = requests.post(
        BASE_URL + "query/",
        json={"question": "查询部门经理"}
    )
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))

def test_statistics():
    print("\n" + "=" * 50)
    print("测试6: 获取统计信息")
    print("=" * 50)
    
    response = requests.get(BASE_URL + "statistics/")
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))

def test_categories():
    print("\n" + "=" * 50)
    print("测试7: 获取分类列表")
    print("=" * 50)
    
    response = requests.get(BASE_URL + "categories/")
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))

def test_knowledge_list():
    print("\n" + "=" * 50)
    print("测试8: 获取知识列表")
    print("=" * 50)
    
    response = requests.get(BASE_URL + "knowledge/")
    result = response.json()
    print(f"总数: {result.get('count', 0)}")
    if 'results' in result:
        for item in result['results']['data'][:2]:
            print(f"  - {item['question'][:40]}...")

if __name__ == "__main__":
    test_query()
    knowledge_id = test_add_knowledge()
    if knowledge_id:
        test_query_new(knowledge_id)
    test_statistics()
    test_categories()
    test_knowledge_list()
    print("\n" + "=" * 50)
    print("所有测试完成!")
    print("=" * 50)
