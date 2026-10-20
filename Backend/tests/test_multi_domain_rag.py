"""
Test Suite: Multi-Domain Knowledge Base RAG System
Tests the automatic routing, candidate pooling, and provenance tagging across:
- MAIN KB (14,143 chunks)
- DEFENCE KB (397 chunks)
- MARITIME KB (273 chunks)
"""

import sys
import unittest
from rag.multi_kb_retriever import get_unified_retriever
from rag.retrieval import retrieve


class TestMultiDomainRAG(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n" + "=" * 70)
        print("INITIALIZING TEST SUITE: MULTI-DOMAIN RAG")
        print("=" * 70)
        cls.retriever = get_unified_retriever()

    def test_01_kb_status_and_invariants(self):
        """Verify all 3 KBs are loaded with exact chunk & vector invariants."""
        status = self.retriever.get_status()
        self.assertEqual(status["status"], "READY")

        # Invariant 1: MAIN KB has 14,143 chunks & vectors
        self.assertEqual(status["MAIN"]["chunks"], 14143)
        self.assertEqual(status["MAIN"]["vectors"], 14143)
        self.assertEqual(status["MAIN"]["dimension"], 1024)

        # Invariant 2: DEFENCE KB has 397 chunks & vectors
        self.assertEqual(status["DEFENCE"]["chunks"], 397)
        self.assertEqual(status["DEFENCE"]["vectors"], 397)
        self.assertEqual(status["DEFENCE"]["dimension"], 1024)

        # Invariant 3: MARITIME KB has 273 chunks & vectors
        self.assertEqual(status["MARITIME"]["chunks"], 273)
        self.assertEqual(status["MARITIME"]["vectors"], 273)
        self.assertEqual(status["MARITIME"]["dimension"], 1024)
        print("[PASS] Test 1: KB Status and Invariants Verified")

    def test_02_telecom_routes_to_main_only(self):
        """Scenario 1: Pure Telecom/5G query searches MAIN only."""
        query = "5G network slicing security requirements and isolation mechanisms"
        results = retrieve(query, k=8, jurisdiction="India", domains=["Telecom/5G"])
        self.assertGreater(len(results), 0)
        kbs = set(r["kb"] for r in results)
        self.assertEqual(kbs, {"MAIN"})
        print(f"[PASS] Test 2: Telecom query -> KBs: {kbs}")

    def test_03_defence_routes_to_defence_and_main(self):
        """Scenario 2: Defence/DRDO drone query retrieves from DEFENCE and MAIN."""
        query = "DRDO drone procurement guidelines and military UAS clearance"
        results = retrieve(query, k=8, jurisdiction="India", domains=["Defence"])
        self.assertGreater(len(results), 0)
        kbs = set(r["kb"] for r in results)
        self.assertIn("DEFENCE", kbs)
        self.assertIn("MAIN", kbs)
        print(f"[PASS] Test 3: Defence query -> KBs: {kbs}")

    def test_04_maritime_routes_to_maritime_and_main(self):
        """Scenario 3: Maritime pollution / AIS query retrieves from MARITIME and MAIN."""
        query = "NOSDCP maritime pollution response and IMO AIS transponder standards"
        results = retrieve(query, k=8, jurisdiction="India", domains=["Maritime"])
        self.assertGreater(len(results), 0)
        kbs = set(r["kb"] for r in results)
        self.assertIn("MARITIME", kbs)
        self.assertIn("MAIN", kbs)
        print(f"[PASS] Test 4: Maritime query -> KBs: {kbs}")

    def test_05_cross_domain_defence_telecom(self):
        """Scenario 4: Cross-domain Defence + Telecom query routes to DEFENCE and MAIN."""
        query = "Military tactical drone communication encryption and 5G command link"
        results = retrieve(query, k=8, jurisdiction="India", domains=["Defence", "Telecom/5G"])
        self.assertGreater(len(results), 0)
        kbs = set(r["kb"] for r in results)
        self.assertIn("DEFENCE", kbs)
        self.assertIn("MAIN", kbs)
        print(f"[PASS] Test 5: Cross Defence+Telecom -> KBs: {kbs}")

    def test_06_cross_domain_defence_maritime(self):
        """Scenario 6: Cross-domain Defence + Maritime routes to DEFENCE, MARITIME, and MAIN."""
        query = "Naval coastal defence drone surveillance and maritime pollution monitoring"
        results = retrieve(query, k=10, jurisdiction="India", domains=["Defence", "Maritime"])
        self.assertGreater(len(results), 0)
        kbs = set(r["kb"] for r in results)
        self.assertIn("DEFENCE", kbs)
        self.assertIn("MARITIME", kbs)
        self.assertIn("MAIN", kbs)
        print(f"[PASS] Test 6: Cross Defence+Maritime -> KBs: {kbs}")


if __name__ == "__main__":
    unittest.main()
