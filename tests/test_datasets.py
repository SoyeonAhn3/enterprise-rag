from copy import deepcopy
import json

import pytest

from config import DOCUMENTS_DIR
from eval import datasets, new_cases
from eval.expanded_cases import build_dataset as legacy_dataset
from eval import quality


def sample():
    return deepcopy(new_cases.build_dataset()[:2])


def test_v3_specification_matches_saved_file_and_every_reference_is_in_pdf():
    questions = datasets.validate_file(new_cases.DATASET_PATH,
                                       against=[quality.DATASET_PATH])
    assert questions == new_cases.build_dataset()
    summary = datasets.dataset_summary(questions)
    assert summary["total"]["questions"] == 40
    assert summary["total"]["answerable"] == 32
    for split in ("dev", "final"):
        part = summary["splits"][split]
        assert part["questions"] == 20 and part["answerable"] == 16
        assert part["test_types"] == {name: 4 for name in
                                      ("boundary", "composite", "exception", "timing", "unanswerable")}
        assert part["max_answers"] == part["max_judge_calls"] == 40
        assert part["max_total_calls"] == 80
    assert summary["model_calls"] == 0 and summary["human_review_completed"] is False


@pytest.mark.parametrize("mutation", [
    "empty", "object", "non_object", "unsafe_id", "case_duplicate", "duplicate_wording",
    "too_long", "missing_question", "missing_answer", "non_boolean", "category", "split",
    "family_leak", "missing_criteria", "duplicate_criteria", "empty_criterion",
    "missing_evidence", "duplicate_group", "missing_claim", "no_alternative",
    "bad_document", "zero_page", "bool_page", "wrong_page", "fabricated_quote", "duplicate_alternative",
])
def test_bad_annotations_fail_before_evaluation(mutation):
    questions = sample()
    q = questions[0]
    candidate = q["evidence_groups"][0]["any_of"][0]
    if mutation == "empty": questions = []
    elif mutation == "object": questions = {"questions": questions}
    elif mutation == "non_object": questions[0] = None
    elif mutation == "unsafe_id": q["id"] = "../../outside"
    elif mutation == "case_duplicate": questions[1]["id"] = q["id"].upper()
    elif mutation == "duplicate_wording": questions[1]["question"] = "  " + q["question"].replace(" ", "") + "!"
    elif mutation == "too_long": q["question"] = "가" * 501
    elif mutation == "missing_question": q.pop("question")
    elif mutation == "missing_answer": q["expected_answer"] = " "
    elif mutation == "non_boolean": q["answerable"] = 1
    elif mutation == "category": q["category"] = "unanswerable"
    elif mutation == "split": q["split"] = "training"
    elif mutation == "family_leak": questions[1].update(family=q["family"], split="final")
    elif mutation == "missing_criteria": q["grading_criteria"] = []
    elif mutation == "duplicate_criteria": q["grading_criteria"].append(q["grading_criteria"][0])
    elif mutation == "empty_criterion": q["grading_criteria"][0] = " "
    elif mutation == "missing_evidence": q["evidence_groups"] = []
    elif mutation == "duplicate_group": q["evidence_groups"].append(deepcopy(q["evidence_groups"][0]))
    elif mutation == "missing_claim": q["evidence_groups"][0].pop("claim")
    elif mutation == "no_alternative": q["evidence_groups"][0]["any_of"] = []
    elif mutation == "bad_document": candidate["document"] = "../private.pdf"
    elif mutation == "zero_page": candidate["page"] = 0
    elif mutation == "bool_page": candidate["page"] = True
    elif mutation == "wrong_page": candidate["page"] = 99
    elif mutation == "fabricated_quote": candidate["quote"] = "모든 구매는 검토 없이 승인된다."
    elif mutation == "duplicate_alternative": q["evidence_groups"][0]["any_of"].append(deepcopy(candidate))
    with pytest.raises(ValueError):
        datasets.validate_questions(questions, documents_dir=DOCUMENTS_DIR)


@pytest.mark.parametrize("content", ['[{"id":"first","id":"second"}]', '[{"value":NaN}]'])
def test_ambiguous_json_is_rejected(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        datasets.read_dataset(path)


def test_reference_checks_accept_only_whitespace_variation():
    questions = sample()
    candidate = questions[0]["evidence_groups"][0]["any_of"][0]
    candidate["quote"] = candidate["quote"].replace(" ", "\n")
    datasets.validate_questions(questions, documents_dir=DOCUMENTS_DIR)
    candidate["quote"] = candidate["quote"].replace("합산", "제외")
    with pytest.raises(ValueError, match="Quote not in PDF"):
        datasets.validate_questions(questions, documents_dir=DOCUMENTS_DIR)


def test_legacy_v2_still_passes_generic_structure_and_reference_checks():
    datasets.validate_questions(legacy_dataset(), documents_dir=DOCUMENTS_DIR)


def test_validate_cli_does_not_initialize_clients_settings_or_retrieval(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Validation must stay offline and must not initialize runtime resources")
    for name in ("run_settings", "open_retrievers", "ClaudeClient"):
        monkeypatch.setattr(quality, name, forbidden)
    assert quality.main(["validate", "--dataset", str(new_cases.DATASET_PATH),
                         "--against", str(quality.DATASET_PATH)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "validated_no_calls"
    assert quality.main(["validate", "--dataset", str(quality.DATASET_PATH),
                         "--against", str(quality.DATASET_PATH)]) == 1
    assert "repeat an earlier dataset" in capsys.readouterr().err


def test_references_do_not_change_unanswerable_contract():
    q = deepcopy(new_cases.build_dataset()[16])
    q["evidence_groups"] = sample()[0]["evidence_groups"]
    with pytest.raises(ValueError, match="evidence groups"):
        datasets.validate_questions([q])


def test_selected_split_is_explicit_and_nonempty():
    questions = sample()
    for split in (None, "all", "final"):
        with pytest.raises(ValueError):
            datasets.select_questions(questions, split)
    assert datasets.select_questions(questions, "dev") == questions


def test_v3_writer_preserves_existing_different_content(tmp_path, monkeypatch):
    path = tmp_path / "v3.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(new_cases, "DATASET_PATH", path)
    with pytest.raises(ValueError, match="instead of overwriting"):
        new_cases.main(["--write"])
    assert path.read_text(encoding="utf-8") == "[]"
