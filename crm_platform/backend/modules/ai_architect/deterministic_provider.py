from __future__ import annotations

from modules.ai_architect.provider_base import ArchitectProvider
from modules.ai_architect.refinement_provider import DeterministicRefinementProvider


def _contains_cyrillic(value: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in value)


def _blueprint_is_russian(blueprint: dict) -> bool:
    values = [
        blueprint.get("business_summary", ""),
        *blueprint.get("departments", []),
        *blueprint.get("forms", []),
        *blueprint.get("reports", []),
    ]
    return _contains_cyrillic(" ".join(str(value) for value in values))


class DeterministicArchitectProvider(ArchitectProvider):
    def generate_blueprint(self, owner_messages: list[str]) -> dict:
        transcript = " ".join(owner_messages).lower()
        is_russian = _contains_cyrillic(transcript)

        if is_russian and any(word in transcript for word in ("аниматор", "праздник", "шоу", "квест", "выпускн", "ведущ", "мероприят", "тимбилдинг", "корпоратив")):
            return {
                "business_summary": "Аниматорская организация с заказами, графиком, аниматорами, костюмами, инвентарем и оплатами.",
                "business_profile": "general",
                "departments": ["Продажи", "Координация", "Аниматоры", "Склад"],
                "roles": ["Владелец", "Менеджер", "Координатор", "Аниматор", "Склад"],
                "entities": ["Клиенты", "Заказы", "Аниматоры", "Программы", "Костюмы", "Инвентарь", "Оплаты"],
                "forms": ["Заявка на праздник", "Профиль аниматора", "Инвентарь и костюмы", "Выплата аниматору"],
                "reports": ["График заказов", "Накладки по аниматорам", "Выручка и выплаты"],
                "assumptions": ["Заказы планируются по дате, времени, длительности и назначенным аниматорам."],
            }

        if is_russian and any(word in transcript for word in ("студент", "ученик", "учител", "обуч", "курс", "посещаем")):
            return {
                "business_summary": "Учебный центр с учениками, группами, посещаемостью и оплатами.",
                "business_profile": "general",
                "departments": ["Прием", "Преподаватели", "Финансы"],
                "roles": ["Владелец", "Менеджер", "Преподаватель"],
                "entities": ["Ученики", "Родители", "Группы", "Посещаемость", "Оплаты"],
                "forms": ["Анкета ученика", "Отметка посещаемости", "Запись оплаты"],
                "reports": ["Выручка по группам", "Просроченные оплаты"],
                "assumptions": ["Ежемесячные оплаты отслеживаются по каждому ученику."],
            }

        if is_russian and any(word in transcript for word in ("пациент", "врач", "клиник", "прием", "запись")):
            return {
                "business_summary": "Клиника с регистрацией пациентов, записями на прием и оплатами.",
                "business_profile": "general",
                "departments": ["Ресепшен", "Врачи", "Финансы"],
                "roles": ["Владелец", "Администратор", "Врач"],
                "entities": ["Пациенты", "Записи", "Приемы", "Оплаты"],
                "forms": ["Анкета пациента", "Заметка приема", "Запись оплаты"],
                "reports": ["Приемы на сегодня", "Неоплаченные счета"],
                "assumptions": ["Записи на прием ведет администратор."],
            }

        if is_russian and any(word in transcript for word in ("магазин", "товар", "склад", "продаж", "розниц")):
            return {
                "business_summary": "Розничный бизнес с клиентами, товарами, продажами и складом.",
                "business_profile": "general",
                "departments": ["Продажи", "Склад", "Финансы"],
                "roles": ["Владелец", "Кассир", "Складской менеджер"],
                "entities": ["Клиенты", "Товары", "Продажи", "Склад", "Оплаты"],
                "forms": ["Запись продажи", "Приход товара", "Запись оплаты"],
                "reports": ["Продажи за день", "Низкие остатки"],
                "assumptions": ["Товары отслеживаются с остатками на складе."],
            }

        if any(word in transcript for word in ("student", "teacher", "attendance", "education", "course")):
            return {
                "business_summary": "Education center with student, group, attendance, and payment workflows.",
                "business_profile": "general",
                "departments": ["Admissions", "Teaching", "Finance"],
                "roles": ["Owner", "Manager", "Teacher"],
                "entities": ["Students", "Parents", "Groups", "Attendance", "Payments"],
                "forms": ["Student intake", "Attendance record", "Payment record"],
                "reports": ["Group revenue", "Overdue fees"],
                "assumptions": ["Monthly fees are tracked per student."],
            }

        if any(word in transcript for word in ("patient", "doctor", "clinic", "appointment")):
            return {
                "business_summary": "Clinic with patient registration, appointment, and visit workflows.",
                "business_profile": "general",
                "departments": ["Reception", "Doctors", "Finance"],
                "roles": ["Owner", "Receptionist", "Doctor"],
                "entities": ["Patients", "Appointments", "Visits", "Payments"],
                "forms": ["Patient intake", "Visit note", "Payment record"],
                "reports": ["Appointments today", "Unpaid bills"],
                "assumptions": ["Appointments are scheduled by reception staff."],
            }

        if any(word in transcript for word in ("shop", "product", "stock", "sale", "retail")):
            return {
                "business_summary": "Retail business with customers, products, sales, and stock workflows.",
                "business_profile": "general",
                "departments": ["Sales", "Stock", "Finance"],
                "roles": ["Owner", "Cashier", "Stock manager"],
                "entities": ["Customers", "Products", "Sales", "Stock", "Payments"],
                "forms": ["Sale record", "Stock intake", "Payment record"],
                "reports": ["Daily sales", "Low stock"],
                "assumptions": ["Products are tracked with stock balances."],
            }

        return {
            "business_summary": "General business with customers and recurring internal work.",
            "business_profile": "general",
            "departments": ["Operations"],
            "roles": ["Owner", "Manager"],
            "entities": ["Customers", "Requests"],
            "forms": ["Request intake"],
            "reports": ["Open requests"],
            "assumptions": ["The business uses a general request workflow."],
        }

    @staticmethod
    def _form_schema_for_name(form_name: str) -> list[dict] | None:
        normalized = form_name.lower()
        if "заяв" in normalized or "праздник" in normalized or "order" in normalized:
            labels = [
                ("client_name", "Имя клиента", "text"),
                ("client_phone", "Телефон клиента", "text"),
                ("event_date", "Дата мероприятия", "date"),
                ("start_time", "Время начала", "text"),
                ("duration_minutes", "Длительность минут", "number"),
                ("address", "Адрес", "text"),
                ("program", "Программа", "text"),
                ("assigned_animators", "Назначенные аниматоры", "text"),
                ("costumes", "Костюмы", "text"),
                ("inventory", "Инвентарь", "text"),
                ("price", "Стоимость", "number"),
                ("prepayment", "Предоплата", "number"),
                ("payment_status", "Статус оплаты", "text"),
                ("notes", "Заметки", "text"),
            ]
            return [{"key": key, "label": label, "type": field_type, "required": False} for key, label, field_type in labels]
        if "аниматор" in normalized:
            labels = [
                ("animator_name", "Имя аниматора", "text"),
                ("phone", "Телефон", "text"),
                ("characters", "Персонажи", "text"),
                ("program_skills", "Навыки программ", "text"),
                ("base_rate", "Ставка", "number"),
                ("availability_notes", "Доступность", "text"),
            ]
            return [{"key": key, "label": label, "type": field_type, "required": False} for key, label, field_type in labels]
        if "инвентар" in normalized or "костюм" in normalized:
            labels = [
                ("item_name", "Название", "text"),
                ("category", "Категория", "text"),
                ("quantity", "Количество", "number"),
                ("condition", "Состояние", "text"),
                ("storage_location", "Место хранения", "text"),
                ("assigned_order", "Связанный заказ", "text"),
                ("return_date", "Дата возврата", "date"),
            ]
            return [{"key": key, "label": label, "type": field_type, "required": False} for key, label, field_type in labels]
        return None

    @classmethod
    def _form_artifact(cls, form_name: str) -> dict:
        artifact = {"type": "form", "name": form_name}
        schema = cls._form_schema_for_name(form_name)
        if schema:
            artifact["schema_structure"] = schema
        return artifact

    def generate_proposals(self, blueprint: dict) -> list[dict]:
        if _blueprint_is_russian(blueprint):
            return [
                {
                    "proposal_type": "departments",
                    "operation": "create",
                    "title": "Создать стартовые отделы",
                    "description": "Настроить основные команды из blueprint бизнеса.",
                    "rationale": "Отделы помогают сразу распределить ответственность и маршрутизацию задач.",
                    "generated_artifacts": [
                        {"type": "department", "name": department}
                        for department in blueprint["departments"]
                    ],
                    "target_artifacts": [],
                    "before_state": {},
                    "after_state": {},
                    "risk_level": "low",
                },
                {
                    "proposal_type": "forms",
                    "operation": "create",
                    "title": "Создать стартовые формы",
                    "description": "Создать первые формы для заявок и операционной работы.",
                    "rationale": "Формы превращают blueprint в ежедневные процессы команды.",
                    "generated_artifacts": [
                        self._form_artifact(form_name)
                        for form_name in blueprint["forms"]
                    ],
                    "target_artifacts": [],
                    "before_state": {},
                    "after_state": {},
                    "risk_level": "low",
                },
                {
                    "proposal_type": "reports",
                    "operation": "create",
                    "title": "Создать стартовые отчеты",
                    "description": "Создать первые отчеты для владельца по данным blueprint.",
                    "rationale": "Владелец должен сразу видеть полезные показатели после настройки.",
                    "generated_artifacts": [
                        {"type": "report", "name": report_name}
                        for report_name in blueprint["reports"]
                    ],
                    "target_artifacts": [],
                    "before_state": {},
                    "after_state": {},
                    "risk_level": "low",
                },
            ]

        return [
            {
                "proposal_type": "departments",
                "operation": "create",
                "title": "Create starter departments",
                "description": "Set up the core teams that appear in the business blueprint.",
                "rationale": "Clear departments make ownership and routing easier from day one.",
                "generated_artifacts": [
                    {"type": "department", "name": department}
                    for department in blueprint["departments"]
                ],
                "target_artifacts": [],
                "before_state": {},
                "after_state": {},
                "risk_level": "low",
            },
            {
                "proposal_type": "forms",
                "operation": "create",
                "title": "Create starter forms",
                "description": "Create the first intake and operating forms for this business.",
                "rationale": "Starter forms turn the blueprint into daily workflows the team can actually use.",
                "generated_artifacts": [
                    self._form_artifact(form_name)
                    for form_name in blueprint["forms"]
                ],
                "target_artifacts": [],
                "before_state": {},
                "after_state": {},
                "risk_level": "low",
            },
            {
                "proposal_type": "reports",
                "operation": "create",
                "title": "Create starter reports",
                "description": "Create the first owner-facing reports from the blueprint.",
                "rationale": "The owner should see useful outputs immediately after setup.",
                "generated_artifacts": [
                    {"type": "report", "name": report_name}
                    for report_name in blueprint["reports"]
                ],
                "target_artifacts": [],
                "before_state": {},
                "after_state": {},
                "risk_level": "low",
            },
        ]

    def generate_refinement(
        self,
        message: str,
        artifacts: dict,
        blueprint: dict | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        return DeterministicRefinementProvider().generate_refinement(message, artifacts, blueprint, history)
