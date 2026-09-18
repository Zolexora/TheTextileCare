from app.db import Base, SessionLocal, engine
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        from app.services.roles import RoleService

        RoleService(db).seed_defaults()


def _create_user_and_membership(tenant_name: str, email: str, role_name: str):
    from app.repositories.memberships import MembershipRepository
    from app.repositories.tenants import TenantRepository
    from app.repositories.users import UserRepository

    with SessionLocal() as db:
        user = UserRepository(db).create_or_get(email=email, auth_user_id=f'auth-{email}')
        tenant = TenantRepository(db).create(
            name=tenant_name, slug=tenant_name.lower().replace(' ', '-')
        )
        membership = MembershipRepository(db).create(
            tenant_id=tenant.id,
            user_id=user.id,
            role_name=role_name,
        )
        return user, tenant, membership


def test_tenant_member_cannot_escalate_role() -> None:
    _reset_db()
    owner_user, tenant, _ = _create_user_and_membership(
        'Alpha', 'owner@example.com', 'TENANT_OWNER'
    )
    member_user, _, _ = _create_user_and_membership('Alpha', 'member@example.com', 'TENANT_MEMBER')

    response = client.patch(
        f'/api/v1/tenants/{tenant.id}/members/{member_user.id}',
        json={'role': 'TENANT_OWNER'},
        headers={'X-User-Id': str(owner_user.id), 'X-Tenant-Id': str(tenant.id)},
    )

    assert response.status_code == 403


def test_cross_tenant_access_is_denied() -> None:
    _reset_db()
    user_a, tenant_a, _ = _create_user_and_membership('Alpha', 'usera@example.com', 'TENANT_OWNER')
    _, tenant_b, _ = _create_user_and_membership('Beta', 'userb@example.com', 'TENANT_OWNER')

    response = client.get(
        f'/api/v1/tenants/{tenant_b.id}',
        headers={'X-User-Id': str(user_a.id), 'X-Tenant-Id': str(tenant_a.id)},
    )

    assert response.status_code in {403, 404}


def test_membership_changes_create_audit_event() -> None:
    _reset_db()
    owner_user, tenant, _ = _create_user_and_membership(
        'Gamma', 'owner@example.com', 'TENANT_OWNER'
    )
    _member_user, _, membership = _create_user_and_membership(
        'Gamma', 'member@example.com', 'TENANT_MEMBER'
    )

    response = client.patch(
        f'/api/v1/tenants/{tenant.id}/members/{membership.id}',
        json={'role': 'TENANT_ADMIN'},
        headers={'X-User-Id': str(owner_user.id), 'X-Tenant-Id': str(tenant.id)},
    )

    assert response.status_code == 200
    assert response.json()['membership']['role'] == 'TENANT_ADMIN'

    with SessionLocal() as db:
        from app.repositories.audit import AuditRepository

        events = AuditRepository(db).list_for_tenant(tenant_id=tenant.id)
        assert any(event.event_type == 'MEMBERSHIP_ROLE_CHANGED' for event in events)
