"""Automated unit and integration tests for contextual communication (Group 6) ORM models.

Tests cover:
- Model registration in ``Base.metadata`` for:
  - ``conversations``
  - ``conversation_participants``
  - ``messages``
  - ``message_attachments``
- Column definitions, data types, precision, nullabilities, and server defaults
- Primary key generation via ``UUIDPrimaryKeyMixin``
- Foreign key definitions and on-delete rules:
  - ``conversations.farmer_id -> users.id`` (ON DELETE RESTRICT)
  - ``conversations.buyer_id -> users.id`` (ON DELETE RESTRICT)
  - ``conversation_participants.conversation_id -> conversations.id`` (ON DELETE CASCADE)
  - ``conversation_participants.user_id -> users.id`` (ON DELETE RESTRICT)
  - ``messages.conversation_id -> conversations.id`` (ON DELETE CASCADE)
  - ``messages.sender_id -> users.id`` (ON DELETE RESTRICT)
  - ``message_attachments.message_id -> messages.id`` (ON DELETE CASCADE)
- Unique constraints:
  - ``uq_conversations_counterparts`` on (farmer_id, buyer_id)
  - ``uq_conversation_participants`` on (conversation_id, user_id)
- Check constraints:
  - ``chk_conversations_counterparts`` (farmer_id <> buyer_id)
  - ``chk_msg_attachments_file_size`` (file_size_bytes > 0)
- Indexes:
  - ``idx_conversations_counterparts`` on (farmer_id, buyer_id)
  - ``idx_conversations_last_msg`` on (last_message_at DESC)
  - ``idx_messages_conversation`` on (conversation_id, created_at)
  - ``idx_msg_attachments_message`` on (message_id)
- Database execution:
  - Creation of conversation, participants, messages, and attachments
  - Reusable chat thread (multiple messages in same thread)
  - Bidirectional navigation
  - Enforcement of counterparts constraint (farmer <> buyer)
  - Enforcement of unique conversation between same counterparts
  - Enforcement of unique participant per conversation
  - Enforcement of positive file size on attachments
  - Cascade deletion on conversation removal (deletes participants, messages, attachments)
  - Cascade deletion on message removal (deletes attachments)
  - Restriction on user deletion with existing conversation/message records
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.chat import (
    CONTEXT_TYPE_GENERAL,
    CONTEXT_TYPE_LISTING,
    CONTEXT_TYPE_REQUIREMENT,
    VALID_CONTEXT_TYPES,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)
from app.models.user import User


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def sqlite_engine():
    """Create an isolated in-memory SQLite database engine with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Provide a transactional database session for each test."""
    session_factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_farmer(db_session: Session) -> User:
    """Create and persist a verified farmer user."""
    farmer = User(
        email="chat_farmer@agridirect.test",
        password_hash="hashed_secret_farmer",
        role="farmer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(farmer)
    db_session.commit()
    db_session.refresh(farmer)
    return farmer


@pytest.fixture
def sample_buyer(db_session: Session) -> User:
    """Create and persist a verified buyer user."""
    buyer = User(
        email="chat_buyer@agridirect.test",
        password_hash="hashed_secret_buyer",
        role="buyer",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(buyer)
    db_session.commit()
    db_session.refresh(buyer)
    return buyer


# ===========================================================================
# 1. Metadata & Schema Structure Tests
# ===========================================================================


class TestChatMetadata:
    """Verify table structure, column definitions, constraints, and indexes in Base.metadata."""

    def test_tables_registered_in_metadata(self) -> None:
        """All four Group 6 tables must be registered in Base.metadata."""
        assert "conversations" in Base.metadata.tables
        assert "conversation_participants" in Base.metadata.tables
        assert "messages" in Base.metadata.tables
        assert "message_attachments" in Base.metadata.tables

    def test_conversations_columns_and_nullability(self) -> None:
        """conversations must have all 9 columns with exact nullabilities."""
        table = Base.metadata.tables["conversations"]
        expected = {
            "id": False,
            "farmer_id": False,
            "buyer_id": False,
            "initial_context_type": True,
            "initial_context_id": True,
            "created_at": False,
            "last_message_at": False,
            "order_id": True,
            "status": False,
        }
        assert len(table.columns) == 9
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from conversations"
            assert table.c[col_name].nullable == nullable

    def test_conversation_participants_columns_and_nullability(self) -> None:
        """conversation_participants must have all 6 columns with exact nullabilities."""
        table = Base.metadata.tables["conversation_participants"]
        expected = {
            "id": False,
            "conversation_id": False,
            "user_id": False,
            "share_contact_details": False,
            "last_read_at": True,
            "created_at": False,
        }
        assert len(table.columns) == 6
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from conversation_participants"
            assert table.c[col_name].nullable == nullable

    def test_messages_columns_and_nullability(self) -> None:
        """messages must have all 11 columns with exact nullabilities."""
        table = Base.metadata.tables["messages"]
        expected = {
            "id": False,
            "conversation_id": False,
            "sender_id": False,
            "content": False,
            "is_read": False,
            "created_at": False,
            "message_type": False,
            "delivery_status": False,
            "delivered_at": True,
            "read_at": True,
            "order_id": True,
        }
        assert len(table.columns) == 11
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from messages"
            assert table.c[col_name].nullable == nullable

    def test_message_attachments_columns_and_nullability(self) -> None:
        """message_attachments must have all 8 columns with exact nullabilities."""
        table = Base.metadata.tables["message_attachments"]
        expected = {
            "id": False,
            "message_id": False,
            "file_uri": False,
            "file_name": False,
            "file_mime_type": False,
            "file_size_bytes": False,
            "created_at": False,
            "attachment_type": False,
        }
        assert len(table.columns) == 8
        for col_name, nullable in expected.items():
            assert col_name in table.c, f"Column {col_name} missing from message_attachments"
            assert table.c[col_name].nullable == nullable

    def test_primary_keys_and_mixins(self) -> None:
        """All four tables must use UUID primary keys via UUIDPrimaryKeyMixin."""
        for tbl_name in [
            "conversations",
            "conversation_participants",
            "messages",
            "message_attachments",
        ]:
            table = Base.metadata.tables[tbl_name]
            assert "id" in table.primary_key.columns
            pk_col = table.c.id
            assert isinstance(pk_col.type, PG_UUID)
            assert pk_col.type.as_uuid is True

    def test_foreign_keys_and_on_delete_rules(self) -> None:
        """Foreign keys across all four models must match specified ondelete actions."""
        # 1. conversations
        conv_table = Base.metadata.tables["conversations"]
        conv_fks = {fk.parent.name: fk for fk in conv_table.foreign_keys}
        assert conv_fks["farmer_id"].column.table.name == "users"
        assert conv_fks["farmer_id"].ondelete == "RESTRICT"
        assert conv_fks["buyer_id"].column.table.name == "users"
        assert conv_fks["buyer_id"].ondelete == "RESTRICT"

        # 2. conversation_participants
        part_table = Base.metadata.tables["conversation_participants"]
        part_fks = {fk.parent.name: fk for fk in part_table.foreign_keys}
        assert part_fks["conversation_id"].column.table.name == "conversations"
        assert part_fks["conversation_id"].ondelete == "CASCADE"
        assert part_fks["user_id"].column.table.name == "users"
        assert part_fks["user_id"].ondelete == "RESTRICT"

        # 3. messages
        msg_table = Base.metadata.tables["messages"]
        msg_fks = {fk.parent.name: fk for fk in msg_table.foreign_keys}
        assert msg_fks["conversation_id"].column.table.name == "conversations"
        assert msg_fks["conversation_id"].ondelete == "CASCADE"
        assert msg_fks["sender_id"].column.table.name == "users"
        assert msg_fks["sender_id"].ondelete == "RESTRICT"

        # 4. message_attachments
        att_table = Base.metadata.tables["message_attachments"]
        att_fks = {fk.parent.name: fk for fk in att_table.foreign_keys}
        assert att_fks["message_id"].column.table.name == "messages"
        assert att_fks["message_id"].ondelete == "CASCADE"

    def test_constraints_and_indexes(self) -> None:
        """All unique and check constraints and indexes must be defined in metadata."""
        # conversations
        conv_table = Base.metadata.tables["conversations"]
        conv_checks = {c.name for c in conv_table.constraints if hasattr(c, "sqltext")}
        assert "chk_conversations_counterparts" in conv_checks
        conv_unique = {c.name for c in conv_table.constraints if hasattr(c, "columns") and not hasattr(c, "sqltext")}
        assert "uq_conversations_counterparts" in conv_unique
        conv_idx = {idx.name for idx in conv_table.indexes}
        assert "idx_conversations_counterparts" in conv_idx
        assert "idx_conversations_last_msg" in conv_idx

        # conversation_participants
        part_table = Base.metadata.tables["conversation_participants"]
        part_unique = {c.name for c in part_table.constraints if hasattr(c, "columns") and not hasattr(c, "sqltext")}
        assert "uq_conversation_participants" in part_unique

        # messages
        msg_table = Base.metadata.tables["messages"]
        msg_idx = {idx.name for idx in msg_table.indexes}
        assert "idx_messages_conversation" in msg_idx

        # message_attachments
        att_table = Base.metadata.tables["message_attachments"]
        att_checks = {c.name for c in att_table.constraints if hasattr(c, "sqltext")}
        assert "chk_msg_attachments_file_size" in att_checks
        att_idx = {idx.name for idx in att_table.indexes}
        assert "idx_msg_attachments_message" in att_idx

    def test_canonical_constants(self) -> None:
        """Canonical context types must match specification."""
        assert CONTEXT_TYPE_LISTING == "listing"
        assert CONTEXT_TYPE_REQUIREMENT == "requirement"
        assert CONTEXT_TYPE_GENERAL == "general"
        assert set(VALID_CONTEXT_TYPES) == {"listing", "requirement", "general", "order", "offer"}


# ===========================================================================
# 2. Database Operations & Persistence Tests
# ===========================================================================


class TestChatPersistence:
    """Verify database CRUD and relationship operations."""

    def test_create_conversation_participants_and_messages(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """Create conversation, participants, messages, and attachments in SQLite."""
        conv = Conversation(
            farmer_id=sample_farmer.id,
            buyer_id=sample_buyer.id,
            initial_context_type=CONTEXT_TYPE_LISTING,
            initial_context_id=uuid.uuid4(),
        )
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        assert isinstance(conv.id, uuid.UUID)
        assert conv.farmer_id == sample_farmer.id
        assert conv.buyer_id == sample_buyer.id
        assert conv.created_at is not None
        assert conv.last_message_at is not None

        # Add participants
        p_farmer = ConversationParticipant(
            conversation_id=conv.id,
            user_id=sample_farmer.id,
            share_contact_details=True,
        )
        p_buyer = ConversationParticipant(
            conversation_id=conv.id,
            user_id=sample_buyer.id,
            share_contact_details=False,
        )
        db_session.add_all([p_farmer, p_buyer])
        db_session.commit()

        # Add message
        msg = Message(
            conversation_id=conv.id,
            sender_id=sample_buyer.id,
            content="Hello, is this wheat batch available for dispatch next week?",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.is_read is False
        assert msg.created_at is not None

        # Add attachment
        att = MessageAttachment(
            message_id=msg.id,
            file_uri="storage/chats/sample_spec.pdf",
            file_name="specifications.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=1048576,
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        assert att.file_size_bytes == 1048576
        assert att.message_id == msg.id

    def test_reusable_conversation_multiple_messages(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """A conversation thread is reusable and holds multiple messages in order."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        msg1 = Message(conversation_id=conv.id, sender_id=sample_buyer.id, content="First message")
        msg2 = Message(conversation_id=conv.id, sender_id=sample_farmer.id, content="Second message")
        msg3 = Message(conversation_id=conv.id, sender_id=sample_buyer.id, content="Third message")
        db_session.add_all([msg1, msg2, msg3])
        db_session.commit()

        db_session.refresh(conv)
        assert len(conv.messages) == 3
        assert [m.content for m in conv.messages] == ["First message", "Second message", "Third message"]

    def test_bidirectional_navigation(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """Test full graph traversal through relationships."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        part = ConversationParticipant(conversation_id=conv.id, user_id=sample_farmer.id)
        msg = Message(conversation_id=conv.id, sender_id=sample_farmer.id, content="Test msg")
        db_session.add_all([part, msg])
        db_session.commit()

        att = MessageAttachment(
            message_id=msg.id,
            file_uri="storage/test.png",
            file_name="test.png",
            file_mime_type="image/png",
            file_size_bytes=5000,
        )
        db_session.add(att)
        db_session.commit()

        # Navigations
        db_session.refresh(sample_farmer)
        assert conv.id in [c.id for c in sample_farmer.conversations_as_farmer]
        assert part.id in [p.id for p in sample_farmer.conversation_participations]
        assert msg.id in [m.id for m in sample_farmer.sent_messages]

        db_session.refresh(sample_buyer)
        assert conv.id in [c.id for c in sample_buyer.conversations_as_buyer]

        db_session.refresh(conv)
        assert conv.farmer.id == sample_farmer.id
        assert conv.buyer.id == sample_buyer.id
        assert len(conv.participants) == 1
        assert len(conv.messages) == 1

        db_session.refresh(msg)
        assert len(msg.attachments) == 1
        assert msg.attachments[0].id == att.id
        assert att.message.id == msg.id


# ===========================================================================
# 3. Check Constraint & Integrity Enforcement Tests
# ===========================================================================


class TestChatConstraints:
    """Verify runtime check and unique constraint enforcement."""

    def test_counterparts_must_be_different_users(
        self, db_session: Session, sample_farmer: User
    ) -> None:
        """chk_conversations_counterparts rejects farmer_id == buyer_id."""
        conv = Conversation(
            farmer_id=sample_farmer.id,
            buyer_id=sample_farmer.id,  # Same user
        )
        db_session.add(conv)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_conversation_between_same_counterparts_fails(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """uq_conversations_counterparts rejects duplicate (farmer_id, buyer_id) pair."""
        conv1 = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv1)
        db_session.commit()

        conv2 = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_participant_fails(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """uq_conversation_participants rejects duplicate (conversation_id, user_id)."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        p1 = ConversationParticipant(conversation_id=conv.id, user_id=sample_farmer.id)
        db_session.add(p1)
        db_session.commit()

        p2 = ConversationParticipant(conversation_id=conv.id, user_id=sample_farmer.id)
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_attachment_file_size_must_be_positive(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """chk_msg_attachments_file_size rejects file_size_bytes <= 0."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        msg = Message(conversation_id=conv.id, sender_id=sample_farmer.id, content="Hi")
        db_session.add(msg)
        db_session.commit()

        att_zero = MessageAttachment(
            message_id=msg.id,
            file_uri="test.pdf",
            file_name="test.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=0,
        )
        db_session.add(att_zero)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_conversation_deletion_cascades_to_participants_messages_attachments(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """ON DELETE CASCADE removes participants, messages, and attachments on conversation deletion."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        part = ConversationParticipant(conversation_id=conv.id, user_id=sample_farmer.id)
        msg = Message(conversation_id=conv.id, sender_id=sample_farmer.id, content="Hi")
        db_session.add_all([part, msg])
        db_session.commit()

        att = MessageAttachment(
            message_id=msg.id,
            file_uri="file.pdf",
            file_name="file.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=100,
        )
        db_session.add(att)
        db_session.commit()

        part_id, msg_id, att_id = part.id, msg.id, att.id

        # Delete conversation
        db_session.delete(conv)
        db_session.commit()

        assert db_session.get(ConversationParticipant, part_id) is None
        assert db_session.get(Message, msg_id) is None
        assert db_session.get(MessageAttachment, att_id) is None

    def test_message_deletion_cascades_to_attachments(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """ON DELETE CASCADE removes message attachments on message deletion."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        msg = Message(conversation_id=conv.id, sender_id=sample_farmer.id, content="Hi")
        db_session.add(msg)
        db_session.commit()

        att = MessageAttachment(
            message_id=msg.id,
            file_uri="file.pdf",
            file_name="file.pdf",
            file_mime_type="application/pdf",
            file_size_bytes=100,
        )
        db_session.add(att)
        db_session.commit()
        att_id = att.id

        db_session.delete(msg)
        db_session.commit()

        assert db_session.get(MessageAttachment, att_id) is None

    def test_user_deletion_is_restricted_when_in_conversation(
        self, db_session: Session, sample_farmer: User, sample_buyer: User
    ) -> None:
        """ON DELETE RESTRICT prevents deleting User participating in a conversation."""
        conv = Conversation(farmer_id=sample_farmer.id, buyer_id=sample_buyer.id)
        db_session.add(conv)
        db_session.commit()

        db_session.delete(sample_farmer)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
