from app.services.operator_category_guide import recommend_categories


def _categories(task: str, columns: list[str]) -> list[str]:
    result = recommend_categories(task, columns, max_categories=2)
    return [item["category"] for item in result["recommended_categories"]]


def test_scientific_abstract_routes_to_core_text() -> None:
    categories = _categories(
        "Extract methods, measured metrics, findings, and evidence quotes from a scientific paper abstract",
        ["paper_id", "abstract"],
    )

    assert categories[0] == "core_text"
    assert "chemistry" not in categories


def test_scientific_pdf_routes_ingestion_then_core_text() -> None:
    categories = _categories(
        "Convert research paper PDFs into evidence-grounded question-answer pairs",
        ["paper_id", "pdf_path"],
    )

    assert categories == ["knowledge_cleaning", "core_text"]


def test_chemistry_paper_remains_a_text_task_without_smiles() -> None:
    categories = _categories(
        "Summarize a chemistry paper and bind each finding to an evidence quote",
        ["paper_id", "abstract"],
    )

    assert categories[0] == "core_text"
    assert "chemistry" not in categories


def test_explicit_smiles_task_routes_to_chemistry() -> None:
    categories = _categories(
        "Extract canonical SMILES strings from chemistry text",
        ["text"],
    )

    assert categories[0] == "chemistry"
