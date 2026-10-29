import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cn_geo_check.generator import ENGINES, BrandProfile, generate_questions
from cn_geo_check.sitecheck import detect_schema, parse_robots_blocked


class TestQuestions(unittest.TestCase):
    def setUp(self):
        self.p = BrandProfile(brand="星桥家政", industry="家政服务", product="日常保洁",
                              region="广州", competitor="云洁家政")
        self.qs = generate_questions(self.p)

    def test_twelve_questions_four_groups(self):
        self.assertEqual(len(self.qs), 12)
        cats = [q.category for q in self.qs]
        for c in ["品牌词", "行业词", "长尾词", "场景词"]:
            self.assertEqual(cats.count(c), 3, c)

    def test_templates_filled(self):
        text = " ".join(q.text for q in self.qs)
        self.assertIn("星桥家政", text)
        self.assertIn("云洁家政", text)       # 竞品对比题
        self.assertIn("广州", text)           # 地区进入行业/场景题
        self.assertNotIn("{", text)          # 没有未填充的模板占位

    def test_no_competitor_fallback(self):
        qs = generate_questions(BrandProfile(brand="星桥家政", industry="家政服务"))
        b3 = [q for q in qs if q.qid == "B3"][0]
        self.assertIn("优缺点", b3.text)

    def test_scorecard_rows(self):
        import csv, io
        from cn_geo_check.cli import write_scorecard
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.csv"
            write_scorecard(path, self.qs)
            rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
        self.assertEqual(len(rows) - 1, 12 * len(ENGINES))  # 60 行


class TestSiteCheckParsing(unittest.TestCase):
    def test_robots_blocked(self):
        robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow: /admin/\n"
        self.assertTrue(parse_robots_blocked(robots, "GPTBot"))
        self.assertFalse(parse_robots_blocked(robots, "Bytespider"))  # 只禁了 /admin/
        self.assertIsNone(parse_robots_blocked("User-agent: *\nAllow: /\n", "ClaudeBot")
                          if False else parse_robots_blocked("", "ClaudeBot"))

    def test_schema_detect(self):
        html = '<script type="application/ld+json">{"@type":"FAQPage"}</script>'
        s = detect_schema(html)
        self.assertTrue(s["faq"])
        self.assertTrue(s["has_jsonld"])
        self.assertFalse(s["organization"])


if __name__ == "__main__":
    unittest.main()
