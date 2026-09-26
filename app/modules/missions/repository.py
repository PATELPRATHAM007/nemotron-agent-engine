"""
Mission Persistence Repository
==============================
Handles CRUD for missions, messages, events, plans, selections,
permission requests, diffs, checkpoints, and artifacts.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.session import DatabaseService
from app.modules.missions.models import (
    Mission,
    MissionArtifact,
    MissionAttachment,
    MissionCheckpoint,
    MissionDiff,
    MissionEvent,
    MissionMessage,
    MissionPermissionRequest,
    MissionPlan,
    MissionSelection,
)

logger = get_logger(__name__)


class MissionRepository:
    """Manages persistent lifecycle records for missions."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self._fallback_dir = Path(workspace_root) / ".agent" / "missions"
        self._fallback_dir.mkdir(parents=True, exist_ok=True)
        # Ensure database tables exist
        self._init_db_tables()

    def _init_db_tables(self) -> None:
        try:
            from app.db.session import Base, engine
            Base.metadata.create_all(bind=engine, checkfirst=True)
        except Exception as e:
            logger.warning(f"Could not auto-create mission tables in DB: {e}")

    def create_mission(
        self,
        mission_id: str | None = None,
        title: str = "Autonomous Mission",
        goal: str = "",
        execution_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mid = mission_id or str(uuid.uuid4())
        pol = execution_policy or {"autonomy": "high", "review_policy": "interactive"}

        try:
            with DatabaseService.get_session() as session:
                mission = Mission(
                    id=mid,
                    title=title,
                    goal=goal,
                    status="IDLE",
                    current_phase="INIT",
                    execution_policy=pol,
                )
                session.add(mission)
                session.commit()
                session.refresh(mission)
                return mission.to_dict()
        except Exception as e:
            logger.warning(f"DB save failed for mission {mid}, using fallback file: {e}")
            data = {
                "id": mid,
                "title": title,
                "goal": goal,
                "status": "IDLE",
                "current_phase": "INIT",
                "execution_policy": pol,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_fallback(mid, "meta.json", data)
            return data

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        try:
            with DatabaseService.get_session() as session:
                mission = session.get(Mission, mission_id)
                if mission:
                    return mission.to_dict()
        except Exception as e:
            logger.warning(f"DB lookup failed for mission {mission_id}: {e}")

        # Fallback check
        meta = self._load_fallback(mission_id, "meta.json")
        return meta

    def list_missions(self, limit: int = 20) -> list[dict[str, Any]]:
        results = []
        try:
            with DatabaseService.get_session() as session:
                stmt = select(Mission).order_by(desc(Mission.created_at)).limit(limit)
                missions = session.scalars(stmt).all()
                if missions:
                    return [m.to_dict() for m in missions]
        except Exception as e:
            logger.warning(f"DB list missions failed: {e}")

        # Fallback
        for path in sorted(self._fallback_dir.glob("*/meta.json"), reverse=True)[:limit]:
            try:
                with open(path) as f:
                    results.append(json.load(f))
            except Exception:
                pass
        return results

    def update_mission_status(
        self,
        mission_id: str,
        status: str,
        current_phase: str | None = None,
        tokens_added: int = 0,
        cost_added: float = 0.0,
    ) -> None:
        try:
            with DatabaseService.get_session() as session:
                mission = session.get(Mission, mission_id)
                if mission:
                    mission.status = status
                    if current_phase:
                        mission.current_phase = current_phase
                    if tokens_added:
                        mission.total_tokens += tokens_added
                    if cost_added:
                        mission.total_cost_usd += cost_added
                    session.commit()
                    return
        except Exception as e:
            logger.warning(f"DB update failed for mission status: {e}")

        meta = self._load_fallback(mission_id, "meta.json") or {"id": mission_id}
        meta["status"] = status
        if current_phase:
            meta["current_phase"] = current_phase
        meta["total_tokens"] = meta.get("total_tokens", 0) + tokens_added
        meta["total_cost_usd"] = meta.get("total_cost_usd", 0.0) + cost_added
        self._save_fallback(mission_id, "meta.json", meta)

    def save_message(
        self,
        mission_id: str,
        role: str,
        content: str,
        attachment_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        msg_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                msg = MissionMessage(
                    id=msg_id,
                    mission_id=mission_id,
                    role=role,
                    content=content,
                )
                session.add(msg)
                session.commit()
                session.refresh(msg)
                return msg.to_dict()
        except Exception as e:
            logger.warning(f"DB save message failed: {e}")
            data = {
                "id": msg_id,
                "mission_id": mission_id,
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._append_fallback_list(mission_id, "messages.json", data)
            return data

    def get_messages(self, mission_id: str) -> list[dict[str, Any]]:
        try:
            with DatabaseService.get_session() as session:
                stmt = select(MissionMessage).where(MissionMessage.mission_id == mission_id).order_by(MissionMessage.created_at)
                messages = session.scalars(stmt).all()
                if messages:
                    return [m.to_dict() for m in messages]
        except Exception as e:
            logger.warning(f"DB get messages failed: {e}")

        return self._load_fallback_list(mission_id, "messages.json")

    def append_event(
        self,
        mission_id: str,
        event_type: str,
        payload: dict[str, Any],
        sequence: int = 0,
    ) -> dict[str, Any]:
        event_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                ev = MissionEvent(
                    id=event_id,
                    mission_id=mission_id,
                    sequence=sequence,
                    event_type=event_type,
                    payload=payload,
                )
                session.add(ev)
                session.commit()
                return ev.to_dict()
        except Exception as e:
            logger.warning(f"DB append event failed: {e}")
            data = {
                "id": event_id,
                "mission_id": mission_id,
                "sequence": sequence,
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._append_fallback_list(mission_id, "events.json", data)
            return data

    def get_events(self, mission_id: str, since_sequence: int = 0) -> list[dict[str, Any]]:
        try:
            with DatabaseService.get_session() as session:
                stmt = select(MissionEvent).where(
                    MissionEvent.mission_id == mission_id,
                    MissionEvent.sequence >= since_sequence,
                ).order_by(MissionEvent.sequence)
                events = session.scalars(stmt).all()
                if events:
                    return [e.to_dict() for e in events]
        except Exception as e:
            logger.warning(f"DB get events failed: {e}")

        events = self._load_fallback_list(mission_id, "events.json")
        return [e for e in events if e.get("sequence", 0) >= since_sequence]

    def save_plan(
        self,
        mission_id: str,
        steps: list[dict[str, Any]],
        summary: str = "",
        status: str = "PROPOSED",
    ) -> dict[str, Any]:
        plan_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                plan = MissionPlan(
                    id=plan_id,
                    mission_id=mission_id,
                    status=status,
                    steps=steps,
                    summary=summary,
                )
                session.add(plan)
                session.commit()
                return plan.to_dict()
        except Exception as e:
            logger.warning(f"DB save plan failed: {e}")
            data = {
                "id": plan_id,
                "mission_id": mission_id,
                "status": status,
                "steps": steps,
                "summary": summary,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_fallback(mission_id, "latest_plan.json", data)
            return data

    def get_latest_plan(self, mission_id: str) -> dict[str, Any] | None:
        try:
            with DatabaseService.get_session() as session:
                stmt = select(MissionPlan).where(MissionPlan.mission_id == mission_id).order_by(desc(MissionPlan.created_at)).limit(1)
                plan = session.scalars(stmt).first()
                if plan:
                    return plan.to_dict()
        except Exception as e:
            logger.warning(f"DB get plan failed: {e}")
        return self._load_fallback(mission_id, "latest_plan.json")

    def save_selection(
        self,
        mission_id: str,
        prompt: str,
        options: list[dict[str, Any]],
        recommended_option: str | None = None,
    ) -> dict[str, Any]:
        sel_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                sel = MissionSelection(
                    id=sel_id,
                    mission_id=mission_id,
                    prompt=prompt,
                    options=options,
                    recommended_option=recommended_option,
                    status="PENDING",
                )
                session.add(sel)
                session.commit()
                return sel.to_dict()
        except Exception as e:
            logger.warning(f"DB save selection failed: {e}")
            data = {
                "id": sel_id,
                "mission_id": mission_id,
                "prompt": prompt,
                "options": options,
                "recommended_option": recommended_option,
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_fallback(mission_id, f"sel_{sel_id}.json", data)
            return data

    def record_selection_answer(self, selection_id: str, selected_option: str) -> bool:
        try:
            with DatabaseService.get_session() as session:
                sel = session.get(MissionSelection, selection_id)
                if sel:
                    sel.selected_option = selected_option
                    sel.status = "ANSWERED"
                    sel.answered_at = datetime.now(timezone.utc)
                    session.commit()
                    return True
        except Exception as e:
            logger.warning(f"DB record selection answer failed: {e}")
        return False

    def create_permission_request(
        self,
        mission_id: str,
        action: str,
        target: str,
        directory: str = ".",
        risk_level: str = "LOW",
        reason: str = "",
    ) -> dict[str, Any]:
        req_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                perm = MissionPermissionRequest(
                    id=req_id,
                    mission_id=mission_id,
                    action=action,
                    target=target,
                    directory=directory,
                    risk_level=risk_level,
                    reason=reason,
                    status="PENDING",
                )
                session.add(perm)
                session.commit()
                return perm.to_dict()
        except Exception as e:
            logger.warning(f"DB create permission request failed: {e}")
            data = {
                "id": req_id,
                "mission_id": mission_id,
                "action": action,
                "target": target,
                "directory": directory,
                "risk_level": risk_level,
                "reason": reason,
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_fallback(mission_id, f"perm_{req_id}.json", data)
            return data

    def record_permission_decision(
        self,
        request_id: str,
        status: str,
        granted_scope: str | None = None,
    ) -> bool:
        try:
            with DatabaseService.get_session() as session:
                perm = session.get(MissionPermissionRequest, request_id)
                if perm:
                    perm.status = status
                    perm.granted_scope = granted_scope
                    perm.decided_at = datetime.now(timezone.utc)
                    session.commit()
                    return True
        except Exception as e:
            logger.warning(f"DB record permission decision failed: {e}")
        return False

    def save_checkpoint(
        self,
        mission_id: str,
        phase: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        cp_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                cp = MissionCheckpoint(
                    id=cp_id,
                    mission_id=mission_id,
                    phase=phase,
                    snapshot=snapshot,
                )
                session.add(cp)
                session.commit()
                return cp.to_dict()
        except Exception as e:
            logger.warning(f"DB save checkpoint failed: {e}")
            data = {
                "id": cp_id,
                "mission_id": mission_id,
                "phase": phase,
                "snapshot": snapshot,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_fallback(mission_id, "latest_checkpoint.json", data)
            return data

    def save_artifact(
        self,
        mission_id: str,
        artifact_type: str,
        title: str,
        content: str,
    ) -> dict[str, Any]:
        art_id = str(uuid.uuid4())
        try:
            with DatabaseService.get_session() as session:
                art = MissionArtifact(
                    id=art_id,
                    mission_id=mission_id,
                    artifact_type=artifact_type,
                    title=title,
                    content=content,
                )
                session.add(art)
                session.commit()
                return art.to_dict()
        except Exception as e:
            logger.warning(f"DB save artifact failed: {e}")
            data = {
                "id": art_id,
                "mission_id": mission_id,
                "artifact_type": artifact_type,
                "title": title,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._append_fallback_list(mission_id, "artifacts.json", data)
            return data

    def get_artifacts(self, mission_id: str) -> list[dict[str, Any]]:
        try:
            with DatabaseService.get_session() as session:
                stmt = select(MissionArtifact).where(MissionArtifact.mission_id == mission_id).order_by(MissionArtifact.created_at)
                arts = session.scalars(stmt).all()
                if arts:
                    return [a.to_dict() for a in arts]
        except Exception as e:
            logger.warning(f"DB get artifacts failed: {e}")
        return self._load_fallback_list(mission_id, "artifacts.json")

    # Helper fallback disk operations
    def _save_fallback(self, mission_id: str, filename: str, data: Any) -> None:
        m_dir = self._fallback_dir / mission_id
        m_dir.mkdir(parents=True, exist_ok=True)
        with open(m_dir / filename, "w") as f:
            json.dump(data, f, indent=2)

    def _load_fallback(self, mission_id: str, filename: str) -> Any | None:
        path = self._fallback_dir / mission_id / filename
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _append_fallback_list(self, mission_id: str, filename: str, item: Any) -> None:
        items = self._load_fallback_list(mission_id, filename)
        items.append(item)
        self._save_fallback(mission_id, filename, items)

    def _load_fallback_list(self, mission_id: str, filename: str) -> list[Any]:
        data = self._load_fallback(mission_id, filename)
        return data if isinstance(data, list) else []


mission_repository = MissionRepository()
