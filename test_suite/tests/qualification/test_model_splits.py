"""Teacher forcing and leakage protection, independent of any model library."""

from __future__ import annotations

import unittest

from gibbsiq.qualification.model_evaluation import (
    CorpusSplit,
    SplitManifest,
    TokenDocument,
    tiny_split_manifest,
)


def manifest() -> SplitManifest:
    return SplitManifest(
        CorpusSplit(
            "calibration",
            (
                TokenDocument("c1", "cal-group", (0, 1, 2)),
                TokenDocument("c2", "cal-group", (1, 2, 3)),
            ),
        ),
        CorpusSplit("development", (TokenDocument("d1", "dev-group", (2, 3, 4)),)),
        CorpusSplit("evaluation", (TokenDocument("e1", "eval-group", (4, 5, 6)),)),
    )


class ModelSplitTests(unittest.TestCase):
    def test_shift_and_mask_are_per_document(self) -> None:
        document = TokenDocument("first", "source-a", (1, 2, 3, 4), (True, False, True))
        other = TokenDocument("second", "source-b", (5, 6))
        self.assertEqual(document.inputs, (1, 2, 3))
        self.assertEqual(document.targets, (2, 3, 4))
        self.assertEqual(document.mask, (True, False, True))
        self.assertEqual(other.inputs, (5,))
        self.assertEqual(other.targets, (6,))
        self.assertEqual(other.mask, (True,))
        self.assertNotIn((4, 5), tuple(zip(document.inputs, document.targets)))

    def test_serialized_manifest_preserves_roles_content_and_groups(self) -> None:
        original = manifest()
        restored = SplitManifest.from_dict(original.to_dict())
        self.assertEqual(restored, original)
        self.assertEqual(restored.calibration.name, "calibration")
        self.assertEqual(restored.development.documents[0].group_id, "dev-group")
        self.assertEqual(restored.evaluation.documents[0].targets, (5, 6))

    def test_repeated_group_is_allowed_within_one_split(self) -> None:
        self.assertEqual(len(manifest().calibration.documents), 2)

    def test_group_id_leakage_is_rejected_even_with_distinct_tokens(self) -> None:
        original = manifest()
        with self.assertRaises(ValueError):
            SplitManifest(
                original.calibration,
                original.development,
                CorpusSplit("evaluation", (TokenDocument("e2", "cal-group", (7, 6, 5)),)),
            )

    def test_content_leakage_is_rejected_even_after_renaming(self) -> None:
        original = manifest()
        with self.assertRaises(ValueError):
            SplitManifest(
                original.calibration,
                original.development,
                CorpusSplit("evaluation", (TokenDocument("renamed", "new-group", (0, 1, 2)),)),
            )

    def test_changing_the_mask_does_not_make_reused_tokens_held_out(self) -> None:
        original = manifest()
        with self.assertRaises(ValueError):
            SplitManifest(
                original.calibration,
                original.development,
                CorpusSplit("evaluation", (TokenDocument("renamed", "new-group", (0, 1, 2), (True, False)),)),
            )

    def test_duplicate_ids_and_wrong_roles_are_rejected(self) -> None:
        original = manifest()
        with self.assertRaises(ValueError):
            SplitManifest(
                original.calibration,
                original.development,
                CorpusSplit("evaluation", (TokenDocument("c1", "new-group", (7, 6)),)),
            )
        with self.assertRaises(ValueError):
            SplitManifest(original.development, original.calibration, original.evaluation)

    def test_mutable_input_cannot_change_an_existing_document(self) -> None:
        tokens, mask = [0, 1, 2], [True, False]
        document = TokenDocument("doc", "group", tokens, mask)
        tokens[0], mask[0] = 6, False
        self.assertEqual(document.inputs, (0, 1))
        self.assertEqual(document.mask, (True, False))

    def test_invalid_documents_and_unknown_serialized_fields_fail(self) -> None:
        for tokens, mask in (
            ([0], None),
            ([0, True], None),
            ([0, -1], None),
            ([0, 1], [False]),
            ([0, 1], [1]),
            ([0, 1, 2], [True]),
        ):
            with self.subTest(tokens=tokens, mask=mask), self.assertRaises(ValueError):
                TokenDocument("doc", "group", tokens, mask)
        value = manifest().to_dict()
        value["unrecognized"] = "not accepted"
        with self.assertRaises(ValueError):
            SplitManifest.from_dict(value)

    def test_content_digest_excludes_ids_but_includes_mask(self) -> None:
        source = TokenDocument("one", "source", (0, 1, 2), (True, False))
        renamed = TokenDocument("two", "other", (0, 1, 2), (True, False))
        remasked = TokenDocument("three", "source", (0, 1, 2), (False, True))
        self.assertEqual(source.content_digest, renamed.content_digest)
        self.assertNotEqual(source.semantic_digest(), renamed.semantic_digest())
        self.assertNotEqual(source.content_digest, remasked.content_digest)

    def test_serialized_records_are_fresh_and_unknown_nested_fields_fail(self) -> None:
        original = manifest()
        payload = original.to_dict()
        payload["evaluation"]["documents"][0]["tokens"][0] = 99
        self.assertEqual(original.evaluation.documents[0].tokens[0], 4)
        nested = original.to_dict()
        nested["evaluation"]["documents"][0]["extra"] = 1
        with self.assertRaises(ValueError):
            SplitManifest.from_dict(nested)

    def test_tiny_fixture_has_five_valid_evaluation_targets(self) -> None:
        frozen = tiny_split_manifest()
        self.assertEqual(
            sum(sum(document.mask or ()) for document in frozen.evaluation.documents),
            5,
        )
        self.assertEqual(frozen.evaluation.documents[0].targets, (2, 4, 6, 0))
        self.assertEqual(frozen.evaluation.documents[0].mask, (True, True, False, True))

    def test_all_masked_document_and_oversize_split_fail(self) -> None:
        with self.assertRaises(ValueError):
            TokenDocument("all-masked", "group", (0, 1, 2), (False, False))
        with self.assertRaises(ValueError):
            CorpusSplit(
                "calibration",
                tuple(TokenDocument(f"d{index}", "group", (index, index + 1)) for index in range(17)),
            )


if __name__ == "__main__":
    unittest.main()
