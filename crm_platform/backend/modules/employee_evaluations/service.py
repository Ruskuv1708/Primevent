from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from modules.workflow import models as workflow_models  # noqa: F401
from modules.access_control.enums import UserRole
from modules.access_control.models import User
from modules.employee_evaluations.models import EmployeeEvaluation
from modules.employee_evaluations.schemas import EmployeeEvaluationCreate, EmployeeEvaluationUpdate


class EmployeeEvaluationService:
    @staticmethod
    def _serialize_user(user: User | object | None) -> dict | None:
        if user is None:
            return None
        role = getattr(user, "role", "")
        return {
            "id": str(user.id),
            "full_name": getattr(user, "full_name", ""),
            "email": getattr(user, "email", None),
            "role": getattr(role, "value", role),
        }

    @classmethod
    def _workspace_users(cls, db: Session, workspace_id: UUID) -> list[User | object]:
        users = db.query(User).filter(User.workspace_id == workspace_id).order_by(User.full_name.asc()).all()
        return [
            user
            for user in users
            if str(getattr(user, "workspace_id", workspace_id)) == str(workspace_id)
            and getattr(user, "is_active", True)
            and getattr(getattr(user, "role", ""), "value", getattr(user, "role", "")) != UserRole.SUPERADMIN.value
        ]

    @classmethod
    def _user_map(cls, db: Session, workspace_id: UUID) -> dict[str, User | object]:
        return {str(user.id): user for user in cls._workspace_users(db, workspace_id)}

    @classmethod
    def _ensure_employee_exists(cls, db: Session, workspace_id: UUID, employee_id: UUID) -> None:
        if str(employee_id) not in cls._user_map(db, workspace_id):
            raise HTTPException(status_code=404, detail="Employee was not found")

    @staticmethod
    def _update_data(data: EmployeeEvaluationUpdate) -> dict:
        if hasattr(data, "model_dump"):
            return data.model_dump(exclude_unset=True)
        return data.dict(exclude_unset=True)

    @classmethod
    def _serialize_evaluation(
        cls,
        evaluation: EmployeeEvaluation,
        users_by_id: dict[str, User | object],
    ) -> dict:
        return {
            "id": str(evaluation.id),
            "employee_id": str(evaluation.employee_id),
            "evaluator_id": str(evaluation.evaluator_id),
            "title": evaluation.title,
            "description": evaluation.description,
            "score": evaluation.score,
            "period_label": evaluation.period_label,
            "comment": evaluation.comment,
            "employee": cls._serialize_user(users_by_id.get(str(evaluation.employee_id))),
            "evaluator": cls._serialize_user(users_by_id.get(str(evaluation.evaluator_id))),
            "created_at": evaluation.created_at.isoformat() if getattr(evaluation, "created_at", None) else None,
            "updated_at": evaluation.updated_at.isoformat() if getattr(evaluation, "updated_at", None) else None,
        }

    @classmethod
    def _workspace_evaluations(cls, db: Session, workspace_id: UUID) -> list[EmployeeEvaluation]:
        evaluations = (
            db.query(EmployeeEvaluation)
            .filter(EmployeeEvaluation.workspace_id == workspace_id)
            .order_by(EmployeeEvaluation.updated_at.desc())
            .all()
        )
        return [
            evaluation
            for evaluation in evaluations
            if str(getattr(evaluation, "workspace_id", workspace_id)) == str(workspace_id)
        ]

    @classmethod
    def list_evaluations(
        cls,
        db: Session,
        workspace_id: UUID,
        employee_id: UUID | None = None,
    ) -> list[dict]:
        users_by_id = cls._user_map(db, workspace_id)
        evaluations = cls._workspace_evaluations(db, workspace_id)
        if employee_id:
            evaluations = [
                evaluation
                for evaluation in evaluations
                if str(evaluation.employee_id) == str(employee_id)
            ]
        return [cls._serialize_evaluation(evaluation, users_by_id) for evaluation in evaluations]

    @classmethod
    def list_employee_summaries(cls, db: Session, workspace_id: UUID) -> list[dict]:
        evaluations = cls._workspace_evaluations(db, workspace_id)
        scores_by_employee: dict[str, list[int]] = {}
        for evaluation in evaluations:
            scores_by_employee.setdefault(str(evaluation.employee_id), []).append(evaluation.score)

        summaries = []
        for user in cls._workspace_users(db, workspace_id):
            scores = scores_by_employee.get(str(user.id), [])
            total_score = sum(scores)
            summaries.append(
                {
                    **(cls._serialize_user(user) or {}),
                    "evaluation_count": len(scores),
                    "total_score": total_score,
                    "average_score": round(total_score / len(scores), 1) if scores else None,
                }
            )
        return summaries

    @classmethod
    def get_team_stats(cls, db: Session, workspace_id: UUID) -> dict:
        summaries = cls.list_employee_summaries(db, workspace_id)
        scored_rankings = [
            summary
            for summary in summaries
            if summary["evaluation_count"] > 0 and summary["average_score"] is not None
        ]
        scored_rankings.sort(
            key=lambda item: (
                -item["average_score"],
                -item["total_score"],
                -item["evaluation_count"],
                item["full_name"].lower(),
            )
        )

        last_rank_key = None
        current_rank = 0
        for index, item in enumerate(scored_rankings, start=1):
            rank_key = (item["average_score"], item["total_score"], item["evaluation_count"])
            if rank_key != last_rank_key:
                current_rank = index
                last_rank_key = rank_key
            item["rank"] = current_rank

        unscored_rankings = sorted(
            [
                {**summary, "rank": None}
                for summary in summaries
                if summary["evaluation_count"] == 0 or summary["average_score"] is None
            ],
            key=lambda item: item["full_name"].lower(),
        )
        rankings = [*scored_rankings, *unscored_rankings]
        team_total_score = sum(item["total_score"] for item in summaries)
        team_evaluation_count = sum(item["evaluation_count"] for item in summaries)

        return {
            "team_total_score": team_total_score,
            "team_average_score": round(team_total_score / team_evaluation_count, 1) if team_evaluation_count else None,
            "evaluation_count": team_evaluation_count,
            "employee_count": len(summaries),
            "evaluated_employee_count": len(scored_rankings),
            "top_employee": rankings[0] if scored_rankings else None,
            "rankings": rankings,
        }

    @classmethod
    def create_evaluation(
        cls,
        db: Session,
        workspace_id: UUID,
        evaluator_id: UUID,
        data: EmployeeEvaluationCreate,
    ) -> dict:
        cls._ensure_employee_exists(db, workspace_id, data.employee_id)
        evaluation = EmployeeEvaluation(
            workspace_id=workspace_id,
            employee_id=data.employee_id,
            evaluator_id=evaluator_id,
            title=data.title,
            description=data.description,
            score=data.score,
            period_label=data.period_label,
            comment=data.comment,
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        users_by_id = cls._user_map(db, workspace_id)
        return cls._serialize_evaluation(evaluation, users_by_id)

    @staticmethod
    def _get_evaluation(db: Session, workspace_id: UUID, evaluation_id: UUID) -> EmployeeEvaluation:
        evaluation = (
            db.query(EmployeeEvaluation)
            .filter(EmployeeEvaluation.workspace_id == workspace_id, EmployeeEvaluation.id == evaluation_id)
            .first()
        )
        if not evaluation or str(getattr(evaluation, "workspace_id", workspace_id)) != str(workspace_id):
            raise HTTPException(status_code=404, detail="Employee evaluation was not found")
        return evaluation

    @classmethod
    def update_evaluation(
        cls,
        db: Session,
        workspace_id: UUID,
        evaluation_id: UUID,
        data: EmployeeEvaluationUpdate,
    ) -> dict:
        evaluation = cls._get_evaluation(db, workspace_id, evaluation_id)
        update_data = cls._update_data(data)
        if update_data.get("employee_id"):
            cls._ensure_employee_exists(db, workspace_id, update_data["employee_id"])
        for field, value in update_data.items():
            setattr(evaluation, field, value)
        db.commit()
        db.refresh(evaluation)
        users_by_id = cls._user_map(db, workspace_id)
        return cls._serialize_evaluation(evaluation, users_by_id)

    @classmethod
    def delete_evaluation(cls, db: Session, workspace_id: UUID, evaluation_id: UUID) -> dict:
        evaluation = cls._get_evaluation(db, workspace_id, evaluation_id)
        db.delete(evaluation)
        db.commit()
        return {"deleted": True, "id": str(evaluation_id)}
