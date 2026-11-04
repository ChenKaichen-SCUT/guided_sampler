"""Compile and exercise the real C++ initialization code independently of Z3."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PartitionedInitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="highdiv-init-tests-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / "partitioned_initialization"
        command = [*shlex.split(os.environ.get("CXX", "g++")), "-std=c++20", "-O0",
                   "-D_GLIBCXX_ASSERTIONS",
                   "-fno-access-control", "-I", str(ROOT / "z3/src"),
                   str(ROOT / "tests/partitioned_initialization.cpp"),
                   str(ROOT / "z3/src/sampler/sampler.cpp"),
                   str(ROOT / "z3/src/sampler/Interval.cpp"), "-o", str(cls.binary)]
        result = subprocess.run(command, text=True, capture_output=True, timeout=120)
        if result.returncode:
            raise AssertionError("C++ test compilation failed:\n" + result.stderr)

    def check_case(self, name):
        result = subprocess.run([str(self.binary), name], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_complement_excludes_original_endpoints(self):
        self.check_case("complement_boundaries")

    def test_complement_can_select_either_side(self):
        self.check_case("complement_sides")

    def test_complement_handles_empty_full_and_extreme_intervals(self):
        self.check_case("complement_extremes")

    def test_equality_group_starts_at_zero_or_nearest_hard_bound(self):
        self.check_case("equality_initialization")

    def test_paper_example_for_high_frequency_and_general_groups(self):
        self.check_case("paper_example")

    def test_closures_are_disjoint_and_use_the_paper_threshold(self):
        self.check_case("partition_closures")

    def test_partitioned_initialization_honors_hard_bounds(self):
        self.check_case("bounded_reverse")

    def test_guidance_uses_correct_coefficients_and_satisfied_literals(self):
        self.check_case("coefficients_and_false_literals")

    def test_negated_inequality_uses_strict_integer_boundary(self):
        self.check_case("negative_literal")

    def test_unavailable_reverse_interval_falls_back_to_bounded_sampling(self):
        self.check_case("fallback")

    def test_missing_model_does_not_guide_from_zero(self):
        self.check_case("missing_model")

    def test_boolean_values_are_not_parsed_as_integers(self):
        self.check_case("boolean_model")

    def test_oversized_model_integer_does_not_wrap(self):
        self.check_case("oversized_model")

    def test_equality_group_preserves_sampling_bounds_for_moves(self):
        self.check_case("equality_sampling_bounds")

    def test_empty_complement_uses_bounded_fallback(self):
        self.check_case("empty_complement_fallback")

    def test_opposite_inequalities_require_conjunction_and_correct_pairing(self):
        self.check_case("equality_requires_conjunction")

    def test_domain_external_feasible_interval_is_not_discarded(self):
        self.check_case("feasible_interval_outside_sampling_domain")

    def test_paper_boundary_move_stays_inside_contextual_interval(self):
        self.check_case("boundary_move_interval")

    def test_boundary_move_singleton_has_no_extra_endpoint(self):
        self.check_case("boundary_move_singleton")

    def test_boundary_move_samples_intervals_wider_than_int64_max(self):
        self.check_case("boundary_move_wide_interval")

    def test_integer_parser_preserves_minimum_and_large_constants(self):
        self.check_case("parsed_integer_limits")

    def test_unsupported_integer_is_rejected_before_arithmetic(self):
        self.check_case("unsupported_integer_is_reported")

    def test_overflow_does_not_produce_a_satisfying_assignment(self):
        self.check_case("overflowing_search_is_not_a_model")

    def test_different_sampler_sizes_have_independent_temporary_storage(self):
        self.check_case("independent_sampler_sizes")
