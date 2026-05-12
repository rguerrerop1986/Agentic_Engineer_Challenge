from collections.abc import Generator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.checkout import CheckoutConfig
from app.models.user import User


@dataclass
class IntegrationHarness:
    """TestClient plus a factory for new ORM sessions against the same isolated DB."""

    client: TestClient
    session_factory: sessionmaker[Session]


@pytest.fixture
def integration_harness() -> Generator[IntegrationHarness, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as db:
        db.add(
            User(
                email="integration-test@example.com",
                hashed_password=hash_password("test-secret"),
                is_active=True,
            )
        )
        db.add(
            CheckoutConfig(
                tax_rate=Decimal("0.13"),
                discount_rate=Decimal("0.10"),
                discount_threshold=Decimal("100.00"),
                is_active=True,
            )
        )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield IntegrationHarness(client=client, session_factory=TestingSessionLocal)

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
