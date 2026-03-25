from django.test import TestCase
from .models import Category, KnowledgeQA
from .services import TextProcessor, SimilarityCalculator, KnowledgeMatcher, QueryService


class TextProcessorTest(TestCase):
    
    def setUp(self):
        self.processor = TextProcessor()
    
    def test_extract_keywords(self):
        text = "获取最近一年入职的男性员工总数"
        keywords = self.processor.extract_keywords(text)
        self.assertIsInstance(keywords, list)
        self.assertTrue(len(keywords) > 0)
    
    def test_tokenize(self):
        text = "查询所有员工"
        tokens = self.processor.tokenize(text)
        self.assertIsInstance(tokens, list)
        self.assertIn('查询', tokens)
        self.assertIn('员工', tokens)
    
    def test_normalize_text(self):
        text = "查询所有员工!!!"
        normalized = self.processor.normalize_text(text)
        self.assertEqual(normalized, "查询所有员工")


class SimilarityCalculatorTest(TestCase):
    
    def setUp(self):
        self.calculator = SimilarityCalculator()
    
    def test_sequence_similarity(self):
        s1 = "查询员工"
        s2 = "查询员工信息"
        similarity = self.calculator.sequence_similarity(s1, s2)
        self.assertGreater(similarity, 0.5)
    
    def test_jaccard_similarity(self):
        set1 = {'员工', '查询', '男性'}
        set2 = {'员工', '查询', '女性'}
        similarity = self.calculator.jaccard_similarity(set1, set2)
        self.assertGreater(similarity, 0.3)
    
    def test_combined_similarity(self):
        text1 = "查询男性员工"
        text2 = "查询女性员工"
        similarity = self.calculator.combined_similarity(text1, text2)
        self.assertGreater(similarity, 0.5)


class KnowledgeMatcherTest(TestCase):
    
    def setUp(self):
        self.matcher = KnowledgeMatcher()
        
        self.category = Category.objects.create(
            name='测试分类',
            description='测试用分类'
        )
        
        self.qa = KnowledgeQA.objects.create(
            question='获取最近一年入职的男性员工总数',
            sql_query='SELECT COUNT(*) FROM employees WHERE gender = "male"',
            category=self.category,
            tags=['员工', '男性', '统计']
        )
    
    def test_find_best_match(self):
        query = '查询最近一年入职的男性员工数量'
        matches = self.matcher.find_best_match(query)
        
        self.assertTrue(len(matches) > 0)
        best_match, score = matches[0]
        self.assertEqual(best_match.id, self.qa.id)
        self.assertGreater(score, 0.5)


class QueryServiceTest(TestCase):
    
    def setUp(self):
        self.service = QueryService()
        
        self.category = Category.objects.create(
            name='员工管理',
            description='员工相关查询'
        )
        
        self.qa = KnowledgeQA.objects.create(
            question='查询所有女性员工',
            sql_query='SELECT * FROM employees WHERE gender = "female"',
            category=self.category,
            tags=['员工', '女性']
        )
    
    def test_query_found(self):
        result = self.service.query('查询女性员工')
        
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['data'])
        self.assertEqual(result['data']['question'], self.qa.question)
    
    def test_query_not_found(self):
        result = self.service.query('查询明天天气')
        
        self.assertFalse(result['success'])
        self.assertIsNone(result['data'])
    
    def test_add_knowledge(self):
        qa = self.service.add_knowledge(
            question='测试问题',
            sql_query='SELECT 1',
            description='测试描述'
        )
        
        self.assertIsNotNone(qa.id)
        self.assertEqual(qa.question, '测试问题')


class CategoryModelTest(TestCase):
    
    def test_create_category(self):
        category = Category.objects.create(
            name='测试分类',
            description='这是一个测试分类'
        )
        
        self.assertIsNotNone(category.id)
        self.assertEqual(str(category), '测试分类')


class KnowledgeQAModelTest(TestCase):
    
    def test_create_knowledge_qa(self):
        qa = KnowledgeQA.objects.create(
            question='测试问题',
            sql_query='SELECT * FROM test',
            description='测试描述'
        )
        
        self.assertIsNotNone(qa.id)
        self.assertTrue(qa.is_active)
        self.assertEqual(qa.use_count, 0)
    
    def test_increment_use_count(self):
        qa = KnowledgeQA.objects.create(
            question='测试问题',
            sql_query='SELECT 1'
        )
        
        initial_count = qa.use_count
        qa.increment_use_count()
        
        qa.refresh_from_db()
        self.assertEqual(qa.use_count, initial_count + 1)
