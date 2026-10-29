"""Comparison must not treat renumbering, operators or answer permutations as harmless."""
import unittest
from scripts.compare_papers import normalized, option_permutation, changes, similarity


class ComparisonTests(unittest.TestCase):
    def test_whitespace_and_width_normalize_but_operators_do_not(self):
        self.assertEqual(normalized("Ａ， B\nC"), normalized("A,BC"))
        self.assertNotEqual(normalized("x<5"), normalized("x>5"))
        self.assertNotEqual(normalized("2,4"), normalized("4,2"))

    def test_option_permutation_maps_letters_without_changing_answers(self):
        self.assertEqual(option_permutation(["red", "blue", "green", "white"],
                                            ["blue", "red", "white", "green"]),
                         {"A":"B", "B":"A", "C":"D", "D":"C"})
        self.assertIsNone(option_permutation(["x"]*4,["x"]*4))

    def test_changed_number_is_reported(self):
        diff = changes("本题11分", "本题10分")
        self.assertEqual(len(diff), 1)
        self.assertEqual((diff[0]["local"], diff[0]["remote"]), ("1", "0"))

    def test_similarity_is_only_a_candidate_metric(self):
        self.assertGreater(similarity("比较树的结构及层序遍历", "比较树的结构及层序遍历结果"),
                           similarity("比较树的结构及层序遍历", "操作系统文件分配"))


if __name__ == "__main__":
    unittest.main()
