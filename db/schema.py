from sqlalchemy import (
    Table, Column, MetaData,
    Integer, String, Text, Numeric, Date, DateTime,
    ForeignKey, CheckConstraint, PrimaryKeyConstraint,
    func
)

metadata = MetaData()

# -----------------------
# Users table
# -----------------------
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(255), nullable=True),
    Column("first_name", String(255), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

# -----------------------
# Groups table
# -----------------------
groups = Table(
    "groups",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("created_by", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

# -----------------------
# Group Members table (many-to-many)
# -----------------------
group_members = Table(
    "group_members",
    metadata,
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("joined_at", DateTime(timezone=True), server_default=func.now()),
    PrimaryKeyConstraint("group_id", "user_id")  # composite primary key
)

# -----------------------
# Expenses table
# -----------------------
expenses = Table(
    "expenses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("description", Text, nullable=False),
    Column("amount", Numeric(10, 2), nullable=False),
    Column("currency", String(3), server_default="USD"),
    Column("paid_by", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
    Column("date", Date, server_default=func.current_date()),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

# -----------------------
# Expense Participants table (many-to-many)
# -----------------------
expense_participants = Table(
    "expense_participants",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("expense_id", Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("share_type", String(20), CheckConstraint("share_type IN ('equal', 'custom')"), nullable=False),
    Column("amount_owed", Numeric(10, 2), nullable=False),
    Column("share_value", Numeric(10, 2), nullable=True)
)
