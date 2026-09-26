import time

import pytest

from app.core.permissions import (
    ApprovalGateManager,
    PermissionDeniedError,
    PermissionLevel,
    PermissionManager,
)


def test_permission_manager_levels():
    pm = PermissionManager(current_level=PermissionLevel.LEVEL_2_MODIFY_SOURCE)

    # Permitted operations
    assert pm.assert_permitted(PermissionLevel.LEVEL_0_READ_ONLY, "read_file") is True
    assert pm.assert_permitted(PermissionLevel.LEVEL_1_ANALYZE, "analyze_ast") is True
    assert (
        pm.assert_permitted(PermissionLevel.LEVEL_2_MODIFY_SOURCE, "edit_code") is True
    )

    # Blocked operations
    with pytest.raises(PermissionDeniedError) as exc1:
        pm.assert_permitted(PermissionLevel.LEVEL_3_RUN_TESTS, "run_pytest")
    assert "LEVEL_3_RUN_TESTS" in str(exc1.value)

    with pytest.raises(PermissionDeniedError) as exc2:
        pm.assert_permitted(PermissionLevel.LEVEL_5_DB_MUTATION, "run_migration")
    assert "LEVEL_5_DB_MUTATION" in str(exc2.value)


def test_approval_gate_lifecycle():
    gate = ApprovalGateManager(default_timeout_seconds=60)

    # 1. Create request
    req = gate.create_request(
        task_id="task_migration_01",
        operation_type="ALEMBIC_UPGRADE_HEAD",
        description="Add customer_loyalty table",
        required_level=PermissionLevel.LEVEL_5_DB_MUTATION,
    )
    assert req.status == "PENDING"
    assert req.approval_token is None

    # 2. Grant approval
    updated_req = gate.submit_decision(
        req.request_id, approved=True, notes="Verified schema changes in staging."
    )
    assert updated_req.status == "APPROVED"
    assert updated_req.approval_token is not None
    token = updated_req.approval_token

    # 3. Verify token
    assert (
        gate.verify_token(token, required_level=PermissionLevel.LEVEL_5_DB_MUTATION)
        is True
    )
    # Higher required level fails
    assert (
        gate.verify_token(token, required_level=PermissionLevel.LEVEL_6_DEPLOYMENT)
        is False
    )

    # 4. Consume token
    assert gate.consume_token(token) is True
    # Subsequent verification fails
    assert (
        gate.verify_token(token, required_level=PermissionLevel.LEVEL_5_DB_MUTATION)
        is False
    )


def test_approval_gate_rejection():
    gate = ApprovalGateManager()
    req = gate.create_request(
        task_id="task_drop_01",
        operation_type="DROP_TABLE",
        description="Drop legacy users table",
        required_level=PermissionLevel.LEVEL_5_DB_MUTATION,
    )

    updated_req = gate.submit_decision(
        req.request_id, approved=False, notes="Table still in active use."
    )
    assert updated_req.status == "REJECTED"
    assert updated_req.approval_token is None


def test_approval_gate_expiration():
    gate = ApprovalGateManager(default_timeout_seconds=1)
    req = gate.create_request(
        task_id="task_exp_01",
        operation_type="DEPLOY",
        description="Deploy to prod",
        required_level=PermissionLevel.LEVEL_6_DEPLOYMENT,
        timeout_seconds=0,  # Expires immediately
    )
    time.sleep(0.01)

    with pytest.raises(TimeoutError):
        gate.submit_decision(req.request_id, approved=True)
