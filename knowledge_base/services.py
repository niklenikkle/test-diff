import re
import jieba
import jieba.analyse
import logging
import traceback
import os
import json
from difflib import SequenceMatcher
from django.conf import settings
from django.db.models import Q
from typing import List, Tuple, Optional, Dict, Any
from .models import KnowledgeQA, QueryHistory, Category

logger = logging.getLogger(__name__)


class TextProcessor:
    
    @staticmethod
    def extract_keywords(text: str, top_k: int = 10) -> List[str]:
        keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
        return list(keywords)
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        tokens = jieba.lcut(text)
        return [t.strip() for t in tokens if t.strip()]
    
    @staticmethod
    def normalize_text(text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def validate_sql_safety(sql_query: str) -> bool:
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        upper_sql = sql_query.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_sql:
                return False
        return True


class SimilarityCalculator:
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return SimilarityCalculator.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def levenshtein_similarity(s1: str, s2: str) -> float:
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        distance = SimilarityCalculator.levenshtein_distance(s1, s2)
        return 1 - (distance / max_len)
    
    @staticmethod
    def sequence_similarity(s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1, s2).ratio()
    
    @staticmethod
    def jaccard_similarity(set1: set, set2: set) -> float:
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def keyword_similarity(keywords1: List[str], keywords2: List[str]) -> float:
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        return SimilarityCalculator.jaccard_similarity(set1, set2)
    
    @staticmethod
    def combined_similarity(text1: str, text2: str, keywords1: List[str] = None, keywords2: List[str] = None) -> float:
        seq_sim = SimilarityCalculator.sequence_similarity(text1, text2)
        lev_sim = SimilarityCalculator.levenshtein_similarity(text1, text2)
        
        if keywords1 and keywords2:
            kw_sim = SimilarityCalculator.keyword_similarity(keywords1, keywords2)
            return seq_sim * 0.3 + lev_sim * 0.3 + kw_sim * 0.4
        
        return seq_sim * 0.5 + lev_sim * 0.5


class KnowledgeMatcher:
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.similarity_calculator = SimilarityCalculator()
        self.threshold = getattr(settings, 'KNOWLEDGE_SIMILARITY_THRESHOLD', 0.6)
    
    def find_best_match(self, query: str, top_k: int = 1) -> List[Tuple[KnowledgeQA, float]]:
        normalized_query = self.text_processor.normalize_text(query)
        query_keywords = self.text_processor.extract_keywords(normalized_query)
        
        queryset = KnowledgeQA.objects.filter(is_active=True)
        
        candidates = []
        for qa in queryset:
            normalized_question = self.text_processor.normalize_text(qa.question)
            stored_keywords = qa.question_keywords or self.text_processor.extract_keywords(normalized_question)
            
            similarity = self.similarity_calculator.combined_similarity(
                normalized_query, 
                normalized_question,
                query_keywords,
                stored_keywords
            )
            
            if similarity >= self.threshold:
                candidates.append((qa, similarity))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[:top_k]
    
    def search_by_keywords(self, keywords: List[str]) -> List[KnowledgeQA]:
        queryset = KnowledgeQA.objects.filter(is_active=True)
        
        results = []
        for qa in queryset:
            qa_keywords = set(qa.question_keywords or [])
            tags = set(qa.tags or [])
            
            combined = qa_keywords | tags
            
            if any(kw in combined for kw in keywords):
                results.append(qa)
        
        return results
    
    def search_by_tables(self, table_names: List[str]) -> List[KnowledgeQA]:
        queryset = KnowledgeQA.objects.filter(is_active=True)
        
        results = []
        for qa in queryset:
            qa_tables = set(qa.table_names or [])
            if any(table in qa_tables for table in table_names):
                results.append(qa)
        
        return results


class QueryService:
    
    def __init__(self):
        self.matcher = KnowledgeMatcher()
    
    def query(self, user_question: str, top_k: int = 1, include_similar: bool = False) -> Dict[str, Any]:
        try:
            matches = self.matcher.find_best_match(user_question, top_k=top_k)
            
            history = QueryHistory.objects.create(
                user_query=user_question,
                matched_knowledge=matches[0][0] if matches else None,
                similarity_score=matches[0][1] if matches else None,
                is_matched=len(matches) > 0
            )
            
            if not matches:
                return {
                    'success': False,
                    'message': '对不起，我目前没有相关知识。',
                    'data': None,
                    'similar_questions': [],
                    'history_id': str(history.id)
                }
            
            best_match, score = matches[0]
            best_match.increment_use_count()
            
            result = {
                'success': True,
                'message': '找到匹配的知识',
                'data': {
                    'id': str(best_match.id),
                    'question': best_match.question,
                    'sql_query': best_match.sql_query,
                    'description': best_match.description,
                    'category': best_match.category.name if best_match.category else None,
                    'tags': best_match.tags,
                    'similarity_score': round(score, 4),
                    'use_count': best_match.use_count
                },
                'similar_questions': [],
                'history_id': str(history.id)
            }
            
            if include_similar and len(matches) > 1:
                result['similar_questions'] = [
                    {
                        'id': str(qa.id),
                        'question': qa.question,
                        'similarity_score': round(score, 4)
                    }
                    for qa, score in matches[1:]
                ]
            
            return result
        except Exception as e:
            logger.error(f"Query error for '{user_question}': {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'查询出错: {str(e)}\n{traceback.format_exc()}',
                'data': None,
                'similar_questions': [],
                'history_id': None
            }
    
    def add_knowledge(
        self, 
        question: str, 
        sql_query: str, 
        description: str = '',
        category_id: str = None,
        tags: List[str] = None,
        table_names: List[str] = None
    ) -> KnowledgeQA:
        text_processor = TextProcessor()
        keywords = text_processor.extract_keywords(question)
        
        qa = KnowledgeQA.objects.create(
            question=question,
            question_keywords=keywords,
            sql_query=sql_query,
            description=description,
            category_id=category_id,
            tags=tags or [],
            table_names=table_names or []
        )
        
        return qa
    
    def batch_add_knowledge(self, items: List[Dict[str, Any]]) -> List[KnowledgeQA]:
        created_items = []
        for item in items:
            qa = self.add_knowledge(
                question=item.get('question'),
                sql_query=item.get('sql_query'),
                description=item.get('description', ''),
                category_id=item.get('category_id'),
                tags=item.get('tags', []),
                table_names=item.get('table_names', [])
            )
            created_items.append(qa)
        return created_items
    
    def update_knowledge(self, knowledge_id: str, **kwargs) -> Optional[KnowledgeQA]:
        try:
            qa = KnowledgeQA.objects.get(id=knowledge_id)
        except KnowledgeQA.DoesNotExist:
            return None
        
        if 'question' in kwargs:
            kwargs['question_keywords'] = TextProcessor.extract_keywords(kwargs['question'])
        
        for key, value in kwargs.items():
            if hasattr(qa, key):
                setattr(qa, key, value)
        
        qa.save()
        return qa
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        try:
            qa = KnowledgeQA.objects.get(id=knowledge_id)
            qa.delete()
            return True
        except KnowledgeQA.DoesNotExist:
            return False
    
    def search_knowledge(
        self,
        keyword: str = '',
        category_id: str = None,
        tags: List[str] = None,
        is_active: bool = None
    ) -> List[KnowledgeQA]:
        queryset = KnowledgeQA.objects.all()
        
        if keyword:
            queryset = queryset.filter(
                Q(question__icontains=keyword) |
                Q(sql_query__icontains=keyword) |
                Q(description__icontains=keyword)
            )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=tag)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return list(queryset)
    
    def get_category_statistics(self) -> Dict[str, Any]:
        categories = Category.objects.all()
        stats = []
        for category in categories:
            qa_count = KnowledgeQA.objects.filter(category=category).count()
            active_count = KnowledgeQA.objects.filter(category=category, is_active=True).count()
            stats.append({
                'category_id': str(category.id),
                'category_name': category.name,
                'total_qa': qa_count,
                'active_qa': active_count
            })
        return {'categories': stats}
    
    def export_all_knowledge(self) -> List[Dict[str, Any]]:
        all_knowledge = KnowledgeQA.objects.all()
        result = []
        for qa in all_knowledge:
            result.append({
                'id': str(qa.id),
                'question': qa.question,
                'sql_query': qa.sql_query,
                'description': qa.description,
                'category': qa.category.name if qa.category else None,
                'tags': qa.tags,
                'table_names': qa.table_names,
                'use_count': qa.use_count,
                'is_active': qa.is_active,
                'created_at': qa.created_at.isoformat() if qa.created_at else None,
                'updated_at': qa.updated_at.isoformat() if qa.updated_at else None
            })
        return result
    
    def import_from_file(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for item in data:
                self.add_knowledge(
                    question=item.get('question'),
                    sql_query=item.get('sql_query'),
                    description=item.get('description', ''),
                    tags=item.get('tags', []),
                    table_names=item.get('table_names', [])
                )
                imported_count += 1
            
            return {
                'success': True,
                'message': f'成功导入 {imported_count} 条知识',
                'imported_count': imported_count
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'导入失败: {str(e)}',
                'imported_count': 0
            }
    
    def execute_dynamic_query(self, table_name: str, conditions: Dict[str, Any]) -> Dict[str, Any]:
        from django.db import connection
        
        sql = f"SELECT * FROM {table_name}"
        if conditions:
            where_clauses = []
            for key, value in conditions.items():
                where_clauses.append(f"{key} = '{value}'")
            sql += " WHERE " + " AND ".join(where_clauses)
        
        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
        
        return {
            'success': True,
            'data': results,
            'count': len(results)
        }
    
    def calculate_similarity_batch(self, questions: List[str]) -> List[Dict[str, Any]]:
        results = []
        for i, q1 in enumerate(questions):
            for j, q2 in enumerate(questions):
                if i < j:
                    sim = SimilarityCalculator.combined_similarity(q1, q2)
                    results.append({
                        'question1': q1,
                        'question2': q2,
                        'similarity': sim
                    })
        return results
    
    def get_top_used_knowledge(self, limit: int = 10) -> List[Dict[str, Any]]:
        knowledge_list = KnowledgeQA.objects.filter(is_active=True).order_by('-use_count')[:limit]
        result = []
        for qa in knowledge_list:
            result.append({
                'id': str(qa.id),
                'question': qa.question,
                'sql_query': qa.sql_query,
                'use_count': qa.use_count
            })
        return result
    
    def log_query_details(self, user_question: str, result: Dict[str, Any]) -> None:
        log_entry = f"User Query: {user_question} | Result: {json.dumps(result, ensure_ascii=False)}"
        logger.info(log_entry)
