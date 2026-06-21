from __future__ import annotations


def _contains_cyrillic(value: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in value)


class DeterministicRefinementProvider:
    @staticmethod
    def _normalized(value: str) -> str:
        return value.strip().lower()

    @classmethod
    def _find(cls, items: list[dict], name: str) -> dict | None:
        expected = cls._normalized(name)
        for item in items:
            if cls._normalized(str(item.get("name", ""))) == expected:
                return item
        return None

    def generate_refinement(
        self,
        message: str,
        artifacts: dict,
        blueprint: dict | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        normalized = self._normalized(message)
        is_russian = _contains_cyrillic(message)

        if is_russian and "финанс" in normalized and "отдел" in normalized:
            existing = self._find(artifacts.get("departments", []), "Финансы")
            if not existing:
                return {
                    "kind": "proposal",
                    "proposal_type": "departments",
                    "operation": "create",
                    "title": "Создать отдел Финансы",
                    "description": "Создать отдельный отдел для финансовых задач.",
                    "rationale": "Финансовые процессы лучше отделить от операционной работы.",
                    "generated_artifacts": [{"type": "department", "name": "Финансы"}],
                    "target_artifacts": [],
                    "before_state": {},
                    "after_state": {},
                    "risk_level": "low",
                }

        if is_russian and "еженедель" in normalized and "отчет" in normalized:
            return {
                "kind": "proposal",
                "proposal_type": "reports",
                "operation": "create",
                "title": "Создать еженедельный отчет",
                "description": "Создать отчет для еженедельного контроля ключевых задач.",
                "rationale": "Регулярный отчет помогает владельцу быстрее видеть проблемы и прогресс.",
                "generated_artifacts": [{"type": "report", "name": "Еженедельный отчет"}],
                "target_artifacts": [],
                "before_state": {},
                "after_state": {},
                "risk_level": "low",
            }

        if "parent phone" in normalized and "student intake" in normalized:
            template = self._find(artifacts.get("forms", []), "Student intake")
            if template:
                before = list(template.get("schema_structure") or [])
                if not any(field.get("key") == "parent_phone" for field in before):
                    after = [
                        *before,
                        {"key": "parent_phone", "label": "Parent phone", "type": "text", "required": False},
                    ]
                else:
                    after = before
                return {
                    "kind": "proposal",
                    "proposal_type": "forms",
                    "operation": "update",
                    "title": "Add parent phone to Student intake",
                    "description": "Add a parent phone field to the Student intake form.",
                    "rationale": "Parents are part of the student intake process.",
                    "generated_artifacts": [],
                    "target_artifacts": [
                        {"type": "form", "id": str(template["id"]), "name": template["name"]},
                    ],
                    "before_state": {"schema_structure": before},
                    "after_state": {"schema_structure": after},
                    "risk_level": "low",
                }

        if "weekly" in normalized and "overdue" in normalized and "report" in normalized:
            return {
                "kind": "proposal",
                "proposal_type": "reports",
                "operation": "create",
                "title": "Create weekly overdue payments report",
                "description": "Create a weekly report for overdue payments.",
                "rationale": "Recurring overdue-payment visibility helps owners act before balances drift.",
                "generated_artifacts": [{"type": "report", "name": "Weekly overdue payments"}],
                "target_artifacts": [],
                "before_state": {},
                "after_state": {},
                "risk_level": "low",
            }

        if "finance" in normalized and "department" in normalized:
            existing = self._find(artifacts.get("departments", []), "Finance")
            if not existing:
                return {
                    "kind": "proposal",
                    "proposal_type": "departments",
                    "operation": "create",
                    "title": "Create Finance department",
                    "description": "Create a separate Finance department.",
                    "rationale": "Separating money work from operations keeps ownership clearer.",
                    "generated_artifacts": [{"type": "department", "name": "Finance"}],
                    "target_artifacts": [],
                    "before_state": {},
                    "after_state": {},
                    "risk_level": "low",
                }

        return {
            "kind": "clarification",
            "message": (
                "Могу помочь, но нужно уточнить конкретное изменение: поле, форму, отдел или отчет."
                if is_russian
                else "I can help with that, but I need a more specific change such as a field, form, department, or report."
            ),
        }
