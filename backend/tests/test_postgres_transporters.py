"""PostgreSQL Integration & Concurrency Test Suite for Connected Transporters & Bilateral Assignment.

Verifies Module 5/11 transporter workflows against the isolated PostgreSQL test
database (`agridirect_module3_test`) at Alembic head:
- Live schema & Alembic single-head lineage assertions
- Unilateral transporter assignment bypass elimination
- Cross-entity order/offer authorization & pairing integrity
- Cancelled order safeguards across bilateral approval and transport coordination
- Real PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) concurrency races
- Atomic notification + assignment rollback guarantees

Safety Guarantee:
- Uses ONLY `agridirect_module3_test` via `tests.pg_test_utils`.
- NEVER accesses `agridirect_db`.
"""

import threading
import uuid
from collections.abc import Generator
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.db.session import get_db
from app.dependencies import create_access_token
from app.main import app
from app.models.chat import Conversation
from app.models.notification import Notification
from app.models.offer import Offer
from app.models.order import Order
from app.models.transporter_connection import TransportConnectionRequest
from app.models.user import BuyerProfile, FarmerProfile, ServiceArea, TransporterProfile, User
from app.orders.schemas import OrderCancelRequest
from app.orders.service import OrderService
from app.transporters.repository import TransporterRepository
from app.transporters.schemas import TransportConnectionApprovalResponse
from app.transporters.service import TransporterService
from tests.pg_test_utils import (
    PG_TEST_DB_URL,
    assert_pg_migration_state,
    cleanup_pg_test_tables,
    ensure_pg_test_schema_at_head,
)

_pg_engine = create_engine(PG_TEST_DB_URL, pool_size=20, max_overflow=10)
_SessionLocal = sessionmaker(bind=_pg_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clean_pg_db() -> Generator[None, None, None]:
    """Ensure isolated PostgreSQL test DB is migrated to head and clean per test."""
    ensure_pg_test_schema_at_head()
    cleanup_pg_test_tables(_SessionLocal)
    yield
    cleanup_pg_test_tables(_SessionLocal)


@pytest.fixture
def pg_session() -> Generator[Session, None, None]:
    """Provide a real PostgreSQL SQLAlchemy session against agridirect_module3_test."""
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(pg_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient backed by the isolated PostgreSQL session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield pg_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "status": user.account_status}
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_pg_actors(db: Session) -> dict[str, User]:
    pwd = hash_password("Password123!")
    farmer = User(
        email="pg.farmer@example.com",
        password_hash=pwd,
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    buyer = User(
        email="pg.buyer@example.com",
        password_hash=pwd,
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    buyer2 = User(
        email="pg.buyer2@example.com",
        password_hash=pwd,
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    t1 = User(
        email="pg.transporter1@example.com",
        password_hash=pwd,
        role="transporter",
        verification_status="verified",
        account_status="active",
    )
    t2 = User(
        email="pg.transporter2@example.com",
        password_hash=pwd,
        role="transporter",
        verification_status="verified",
        account_status="active",
    )
    db.add_all([farmer, buyer, buyer2, t1, t2])
    db.flush()

    db.add(
        FarmerProfile(
            user_id=farmer.id,
            full_name="PG Farmer",
            farm_name="PG Organic Farms",
            farm_location_address="Gate 1, Nashik",
            city="Nashik",
            state="Maharashtra",
            postal_code="422003",
        )
    )
    db.add_all(
        [
            BuyerProfile(
                user_id=buyer.id,
                business_name="PG Fresh Mart",
                contact_person_name="Amit",
                business_type="retailer",
                delivery_receiving_address="Vashi Cold Storage",
                city="Mumbai",
                state="Maharashtra",
                postal_code="400703",
            ),
            BuyerProfile(
                user_id=buyer2.id,
                business_name="PG Other Mart",
                contact_person_name="Suresh",
                business_type="wholesaler",
                delivery_receiving_address="Pune Market",
                city="Pune",
                state="Maharashtra",
                postal_code="411001",
            ),
        ]
    )
    tp1 = TransporterProfile(
        user_id=t1.id,
        business_name="PG Carrier One",
        contact_name="Sanjay",
        phone_number="9876543001",
        transport_type="refrigerated",
        vehicle_capacity_kg=Decimal("5000.00"),
        vehicle_registration_number="MH-15-PG-1001",
        is_available=True,
    )
    tp2 = TransporterProfile(
        user_id=t2.id,
        business_name="PG Carrier Two",
        contact_name="Vikram",
        phone_number="9876543002",
        transport_type="covered_truck",
        vehicle_capacity_kg=Decimal("6000.00"),
        vehicle_registration_number="MH-15-PG-1002",
        is_available=True,
    )
    db.add_all([tp1, tp2])
    db.flush()
    db.add_all(
        [
            ServiceArea(
                transporter_profile_id=tp1.id,
                state="Maharashtra",
                district="Nashik",
                coverage_type="both",
                is_active=True,
            ),
            ServiceArea(
                transporter_profile_id=tp2.id,
                state="Maharashtra",
                district="Mumbai",
                coverage_type="both",
                is_active=True,
            ),
        ]
    )
    db.commit()
    return {
        "farmer": farmer,
        "buyer": buyer,
        "buyer2": buyer2,
        "t1": t1,
        "t2": t2,
    }


def test_pg_transporter_schema_and_constraints(pg_session: Session) -> None:
    """Verify PG schema matches Alembic head and enforces transport status check constraints."""
    assert_pg_migration_state(pg_session, minimum_revision="e6a1b2c3d4f5")

    cols = {
        row[0]
        for row in pg_session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'transport_connection_requests'
                """
            )
        ).fetchall()
    }
    expected_cols = {
        "transporter_accepted_at",
        "counterparty_approved_by_id",
        "counterparty_approved_at",
        "counterparty_rejected_by_id",
        "counterparty_rejected_at",
        "counterparty_rejection_reason",
    }
    assert expected_cols.issubset(cols)

    order_cols = {
        row[0]
        for row in pg_session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'orders'
                """
            )
        ).fetchall()
    }
    assert "idempotency_key" in order_cols

    actors = _seed_pg_actors(pg_session)
    bad_req = TransportConnectionRequest(
        requester_id=actors["farmer"].id,
        transporter_id=actors["t1"].id,
        status="invalid_status_value",
    )
    pg_session.add(bad_req)
    with pytest.raises(IntegrityError):
        pg_session.flush()
    pg_session.rollback()


def test_pg_legacy_unilateral_bypass_and_cancelled_order_guards(
    client: TestClient, pg_session: Session
) -> None:
    """PG API tests: block unilateral assignment, cross-entity exploits, and cancelled orders."""
    actors = _seed_pg_actors(pg_session)
    farmer = actors["farmer"]
    buyer = actors["buyer"]
    buyer2 = actors["buyer2"]
    t1 = actors["t1"]

    conv_real = Conversation(farmer_id=farmer.id, buyer_id=buyer.id)
    conv_other = Conversation(farmer_id=farmer.id, buyer_id=buyer2.id)
    pg_session.add_all([conv_real, conv_other])
    pg_session.flush()

    offer_real = Offer(
        offer_number="OFF-PG-REAL",
        conversation_id=conv_real.id,
        sender_id=farmer.id,
        recipient_id=buyer.id,
        total_amount=Decimal("40000.00"),
        status="accepted",
    )
    offer_other = Offer(
        offer_number="OFF-PG-OTHER",
        conversation_id=conv_other.id,
        sender_id=farmer.id,
        recipient_id=buyer2.id,
        total_amount=Decimal("15000.00"),
        status="accepted",
    )
    pg_session.add_all([offer_real, offer_other])
    pg_session.flush()

    order = Order(
        order_number="ORD-PG-SEC-01",
        source_offer_id=offer_real.id,
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("40000.00"),
        status="confirmed",
        transport_status="none",
    )
    pg_session.add(order)
    pg_session.commit()

    # 1. Legacy unilateral assignment bypass rejected (422 due to extra='forbid')
    bypass_res = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transporter_id": str(t1.id), "transport_status": "assigned"},
        headers=_auth_headers(farmer),
    )
    assert bypass_res.status_code == 422

    none_to_assigned = client.post(
        f"/api/v1/orders/{order.id}/transport-coordination",
        json={"transport_status": "assigned"},
        headers=_auth_headers(farmer),
    )
    assert none_to_assigned.status_code == 400

    # 2. Cross-entity mismatch blocked (400) and forged row blocks unrelated offer party (403)
    mismatch_res = client.post(
        "/api/v1/transporters/connection-requests",
        json={
            "transporter_user_id": str(t1.id),
            "order_id": str(order.id),
            "offer_id": str(offer_other.id),
        },
        headers=_auth_headers(farmer),
    )
    assert mismatch_res.status_code == 400

    forged = TransportConnectionRequest(
        requester_id=farmer.id,
        transporter_id=t1.id,
        order_id=order.id,
        offer_id=offer_other.id,
        status="transporter_accepted",
    )
    pg_session.add(forged)
    pg_session.commit()

    assert (
        client.get(
            f"/api/v1/transporters/connection-requests/{forged.id}",
            headers=_auth_headers(buyer2),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{forged.id}/approve",
            json={},
            headers=_auth_headers(buyer2),
        ).status_code
        == 403
    )

    # 3. Cancelled order blocks bilateral approval (400) and coordination changes (409)
    t2 = actors["t2"]
    valid_req_id = client.post(
        "/api/v1/transporters/connection-requests",
        json={"transporter_user_id": str(t2.id), "order_id": str(order.id)},
        headers=_auth_headers(farmer),
    ).json()["id"]
    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{valid_req_id}/accept",
            json={},
            headers=_auth_headers(t2),
        ).status_code
        == 200
    )

    order.status = "cancelled"
    pg_session.commit()

    assert (
        client.post(
            f"/api/v1/transporters/connection-requests/{valid_req_id}/approve",
            json={},
            headers=_auth_headers(buyer),
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/orders/{order.id}/transport-coordination",
            json={"transport_status": "in_transit"},
            headers=_auth_headers(farmer),
        ).status_code
        == 409
    )


def test_pg_concurrent_competing_transporters_for_update_race() -> None:
    """Real PostgreSQL FOR UPDATE row locks serialize competing transporter approvals cleanly."""
    with _SessionLocal() as seed:
        actors = _seed_pg_actors(seed)
        farmer = actors["farmer"]
        buyer = actors["buyer"]
        t1 = actors["t1"]
        t2 = actors["t2"]
        order = Order(
            order_number="ORD-PG-COMPETE-1",
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            total_amount=Decimal("45000.00"),
            status="confirmed",
            transport_status="none",
        )
        seed.add(order)
        seed.flush()
        req1 = TransportConnectionRequest(
            requester_id=farmer.id,
            transporter_id=t1.id,
            order_id=order.id,
            status="transporter_accepted",
        )
        req2 = TransportConnectionRequest(
            requester_id=farmer.id,
            transporter_id=t2.id,
            order_id=order.id,
            status="transporter_accepted",
        )
        seed.add_all([req1, req2])
        seed.commit()
        buyer_id = buyer.id
        order_id = order.id
        req1_id, req2_id = req1.id, req2.id
        t1_id, t2_id = t1.id, t2.id

    barrier = threading.Barrier(2)
    outcomes: list[tuple[str, uuid.UUID, int]] = []

    def approve_worker(target_req_id: uuid.UUID) -> None:
        with _SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = TransporterService(TransporterRepository(sess))
                barrier.wait()
                svc.approve_assignment(user_obj, target_req_id)
                outcomes.append(("ok", target_req_id, 200))
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                outcomes.append(("err", target_req_id, getattr(exc, "status_code", 500)))

    th1 = threading.Thread(target=approve_worker, args=(req1_id,))
    th2 = threading.Thread(target=approve_worker, args=(req2_id,))
    th1.start()
    th2.start()
    th1.join()
    th2.join()

    winners = [o for o in outcomes if o[0] == "ok"]
    losers = [o for o in outcomes if o[0] == "err"]
    assert len(winners) == 1
    assert len(losers) == 1
    assert losers[0][2] == 409

    with _SessionLocal() as check:
        final_order = check.get(Order, order_id)
        final_req1 = check.get(TransportConnectionRequest, req1_id)
        final_req2 = check.get(TransportConnectionRequest, req2_id)
        winner_id = winners[0][1]
        loser_id = losers[0][1]
        assert check.query(Notification).filter(Notification.reference_id == loser_id).count() == 0
        assert check.query(Notification).filter(Notification.reference_id == winner_id).count() == 3
        if winner_id == req1_id:
            assert final_order.transporter_id == t1_id
            assert final_req1.status == "counterparty_approved"
            assert final_req2.status == "transporter_accepted"
        else:
            assert final_order.transporter_id == t2_id
            assert final_req2.status == "counterparty_approved"
            assert final_req1.status == "transporter_accepted"


def test_pg_concurrent_same_request_double_approval_race() -> None:
    """Real PostgreSQL FOR UPDATE prevents duplicate notifications/approvals on same request."""
    with _SessionLocal() as seed:
        actors = _seed_pg_actors(seed)
        farmer = actors["farmer"]
        buyer = actors["buyer"]
        t1 = actors["t1"]
        order = Order(
            order_number="ORD-PG-DBL-1",
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            total_amount=Decimal("20000.00"),
            status="confirmed",
            transport_status="none",
        )
        seed.add(order)
        seed.flush()
        req = TransportConnectionRequest(
            requester_id=farmer.id,
            transporter_id=t1.id,
            order_id=order.id,
            status="transporter_accepted",
        )
        seed.add(req)
        seed.commit()
        buyer_id, req_id, order_id, t1_id = buyer.id, req.id, order.id, t1.id

    barrier = threading.Barrier(2)
    results: list[tuple[str, int]] = []

    def approve_same() -> None:
        with _SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = TransporterService(TransporterRepository(sess))
                barrier.wait()
                svc.approve_assignment(user_obj, req_id)
                results.append(("ok", 200))
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                results.append(("err", getattr(exc, "status_code", 500)))

    threads = [threading.Thread(target=approve_same), threading.Thread(target=approve_same)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert results.count(("ok", 200)) == 1
    assert sum(1 for kind, code in results if kind == "err" and code == 400) == 1

    with _SessionLocal() as check:
        final_order = check.get(Order, order_id)
        final_req = check.get(TransportConnectionRequest, req_id)
        assert final_order.transporter_id == t1_id
        assert final_order.transport_status == "assigned"
        assert final_req.status == "counterparty_approved"
        assert check.query(Notification).filter(Notification.reference_id == req_id).count() == 3


def test_pg_concurrent_cancel_order_vs_approve_assignment_race() -> None:
    """Real PostgreSQL lock contention between cancel_order and approve_assignment stays valid."""
    with _SessionLocal() as seed:
        actors = _seed_pg_actors(seed)
        farmer = actors["farmer"]
        buyer = actors["buyer"]
        t1 = actors["t1"]
        order = Order(
            order_number="ORD-PG-CANCEL-RACE",
            farmer_id=farmer.id,
            buyer_id=buyer.id,
            total_amount=Decimal("22000.00"),
            status="confirmed",
            transport_status="none",
        )
        seed.add(order)
        seed.flush()
        req = TransportConnectionRequest(
            requester_id=farmer.id,
            transporter_id=t1.id,
            order_id=order.id,
            status="transporter_accepted",
        )
        seed.add(req)
        seed.commit()
        buyer_id, req_id, order_id, t1_id = buyer.id, req.id, order.id, t1.id

    barrier = threading.Barrier(2)
    results: dict[str, tuple[str, int]] = {}

    def cancel_worker() -> None:
        with _SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = OrderService(sess)
                barrier.wait()
                svc.cancel_order(
                    user_obj, order_id, OrderCancelRequest(reason="PG concurrent cancel")
                )
                results["cancel"] = ("ok", 200)
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                results["cancel"] = ("err", getattr(exc, "status_code", 500))

    def approve_worker() -> None:
        with _SessionLocal() as sess:
            try:
                user_obj = sess.get(User, buyer_id)
                svc = TransporterService(TransporterRepository(sess))
                barrier.wait()
                svc.approve_assignment(user_obj, req_id)
                results["approve"] = ("ok", 200)
            except (HTTPException, SQLAlchemyError) as exc:
                sess.rollback()
                results["approve"] = ("err", getattr(exc, "status_code", 500))

    th_cancel = threading.Thread(target=cancel_worker)
    th_approve = threading.Thread(target=approve_worker)
    th_cancel.start()
    th_approve.start()
    th_cancel.join()
    th_approve.join()

    with _SessionLocal() as check:
        final_order = check.get(Order, order_id)
        final_req = check.get(TransportConnectionRequest, req_id)
        assert final_order.status == "cancelled"
        assert results["cancel"] == ("ok", 200)

        if results["approve"][0] == "err":
            assert results["approve"][1] in (400, 409)
            assert final_order.transporter_id is None
            assert final_order.transport_status == "none"
            assert final_req.status == "transporter_accepted"
            assert check.query(Notification).filter(Notification.reference_id == req_id).count() == 0
        else:
            assert results["approve"] == ("ok", 200)
            assert final_order.transporter_id == t1_id
            assert final_req.status == "counterparty_approved"
            assert check.query(Notification).filter(Notification.reference_id == req_id).count() == 3


def test_pg_notification_failure_rolls_back_atomically(pg_session: Session) -> None:
    """Notification insert failure rolls back PostgreSQL order assignment & request status."""
    actors = _seed_pg_actors(pg_session)
    farmer = actors["farmer"]
    buyer = actors["buyer"]
    t1 = actors["t1"]
    order = Order(
        order_number="ORD-PG-ROLLBACK-1",
        farmer_id=farmer.id,
        buyer_id=buyer.id,
        total_amount=Decimal("18500.00"),
        status="confirmed",
        transport_status="none",
    )
    pg_session.add(order)
    pg_session.flush()
    req = TransportConnectionRequest(
        requester_id=farmer.id,
        transporter_id=t1.id,
        order_id=order.id,
        status="transporter_accepted",
    )
    pg_session.add(req)
    pg_session.commit()

    orig_add_notif = TransporterRepository.add_notification
    call_count = 0

    def fail_on_second_notif(self_repo: TransporterRepository, notif: Notification) -> Notification:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Simulated PG notification failure")
        return orig_add_notif(self_repo, notif)

    svc = TransporterService(TransporterRepository(pg_session))
    with (
        patch.object(TransporterRepository, "add_notification", fail_on_second_notif),
        pytest.raises(RuntimeError, match="Simulated PG notification failure"),
    ):
        svc.approve_assignment(
            buyer,
            req.id,
            TransportConnectionApprovalResponse(approval_notes="Should roll back"),
        )

    pg_session.expire_all()
    refreshed_req = pg_session.get(TransportConnectionRequest, req.id)
    refreshed_order = pg_session.get(Order, order.id)
    assert refreshed_req.status == "transporter_accepted"
    assert refreshed_req.counterparty_approved_by_id is None
    assert refreshed_order.transporter_id is None
    assert refreshed_order.transport_status == "none"
    assert pg_session.query(Notification).filter(Notification.reference_id == req.id).count() == 0
