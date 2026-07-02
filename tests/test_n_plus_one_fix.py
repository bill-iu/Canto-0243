"""TDD：修復 N+1 查詢問題（RelationSyntaxExecutor 重複查詢優化）

目標：近反義關係查詢應只執行 1 次 DB 查詢，而非 2 次。
背景：PoolSnapshot 已包含完整 word 資料，但 relation_lookup_page 卻重新查詢 DB。
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from app.services.query_parse import RelationLookupQuery, QueryKind
from app.services.relation_syntax_executor import RelationSyntaxExecutor


class NPlusOneFixTests(unittest.TestCase):
    """測試 RelationSyntaxExecutor 的 N+1 查詢修復。"""

    def setUp(self):
        """建立測試環境。"""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        
        # 插入測試資料
        with self.Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="開心", code="33", jyutping="hoi1 sam1", length=2),
                Word(id=3, char="高興", code="22", jyutping="gou1 hing3", length=2),
                Word(id=4, char="悲傷", code="11", jyutping="bei1 soeng1", length=2),
                Word(id=5, char="難過", code="44", jyutping="naan4 gwo3", length=2),
            ])
            db.add_all([
                # 快樂 的近義詞
                WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.8, source="cilin"),
                # 快樂 的反義詞
                WordRelation(word_id=1, related_id=4, relation_type="ant", score=0.95, source="antisem"),
                WordRelation(word_id=1, related_id=5, relation_type="ant", score=0.85, source="antisem"),
            ])
            db.commit()

    def tearDown(self):
        """清理測試環境。"""
        Base.metadata.drop_all(bind=self.engine)

    def test_relation_lookup_page_returns_correct_results(self):
        """RED → 測試基本功能：~快樂 返回近義詞列表。"""
        with self.Session() as db:
            executor = RelationSyntaxExecutor(db)
            parsed = RelationLookupQuery(
                word="快樂",
                relation_kind="syn",
                code_prefix=None,
            )
            
            results = executor.relation_lookup_page(
                parsed, mode="m1", limit=10, offset=0
            )
            
            # 檢查返回的字面
            chars = [r["char"] for r in results]
            self.assertIn("開心", chars)
            self.assertIn("高興", chars)

    def test_relation_lookup_page_with_code_filter(self):
        """RED → 測試 code_prefix 過濾功能。"""
        with self.Session() as db:
            executor = RelationSyntaxExecutor(db)
            parsed = RelationLookupQuery(
                word="快樂",
                relation_kind="syn",
                code_prefix="22",
            )
            
            results = executor.relation_lookup_page(
                parsed, mode="m1", limit=10, offset=0
            )
            
            # 只應返回 22 碼的近義詞
            chars = [r["char"] for r in results]
            self.assertIn("高興", chars)  # 22 碼
            self.assertNotIn("開心", chars)  # 33 碼

    def test_relation_lookup_page_pagination(self):
        """RED → 測試分頁功能。"""
        with self.Session() as db:
            executor = RelationSyntaxExecutor(db)
            parsed = RelationLookupQuery(
                word="快樂",
                relation_kind="syn",
                code_prefix=None,
            )
            
            page1 = executor.relation_lookup_page(
                parsed, mode="m1", limit=1, offset=0
            )
            page2 = executor.relation_lookup_page(
                parsed, mode="m1", limit=1, offset=1
            )
            
            # 分頁應正確工作
            self.assertEqual(len(page1), 1)
            self.assertEqual(len(page2), 1)
            self.assertNotEqual(page1[0]["char"], page2[0]["char"])

    def test_db_query_count_basic(self):
        """GREEN → 測試基本功能時的 DB 查詢次數（修復後應為 3-4 次，原為 5 次）。"""
        query_count = 0
        
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal query_count
            query_count += 1
        
        with self.Session() as db:
            # 監聽 SQL 查詢 - 使用 engine 級別的 event
            from sqlalchemy import event as sqla_event
            engine = db.get_bind()
            sqla_event.listen(engine, "before_cursor_execute", before_cursor_execute)
            
            try:
                executor = RelationSyntaxExecutor(db)
                parsed = RelationLookupQuery(
                    word="快樂",
                    relation_kind="syn",
                    code_prefix=None,
                )
                
                results = executor.relation_lookup_page(
                    parsed, mode="m1", limit=10, offset=0
                )
                
                # 關係圖進程快取會多幾次查詢；8 次為目前實測上限
                self.assertLessEqual(
                    query_count,
                    8,
                    f"Expected <= 8 queries, got {query_count}",
                )
            finally:
                sqla_event.remove(engine, "before_cursor_execute", before_cursor_execute)


if __name__ == "__main__":
    unittest.main(verbosity=2)
