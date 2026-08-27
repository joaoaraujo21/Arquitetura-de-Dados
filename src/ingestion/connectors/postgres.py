"""PostgreSQL connector with SQLAlchemy."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Iterator

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PostgresConnector:
    """PostgreSQL database connector using SQLAlchemy.

    Provides connection pooling, context manager support, and
    convenience methods for querying data.
    """

    def __init__(
        self,
        connection_string: str | None = None,
        pool_size: int = 5,
        max_overflow: int = 5,
    ) -> None:
        """Initialize PostgreSQL connector.

        Args:
            connection_string: Full SQLAlchemy connection URL.
                               Defaults to settings.database_url.
            pool_size: Number of connections in pool.
            max_overflow: Max connections beyond pool_size.
        """
        self.connection_string = connection_string or settings.database_url
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self.pool_size = pool_size
        self.max_overflow = max_overflow

    @property
    def engine(self) -> Engine:
        """Lazily create and return SQLAlchemy engine."""
        if self._engine is None:
            logger.info("Creating database engine", url=self.connection_string.split("@")[-1])
            self._engine = create_engine(
                self.connection_string,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,
                echo=settings.app_debug,
            )
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Lazily create and return session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager providing a database session.

        Yields:
            SQLAlchemy Session. Commits on success, rolls back on error.

        Example:
            with connector.session() as session:
                result = session.execute(text("SELECT 1"))
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """Context manager providing a raw DBAPI connection.

        Yields:
            DBAPI connection object.
        """
        with self.engine.connect() as conn:
            yield conn

    def execute(self, query: str, params: dict[str, Any] | None = None) -> Iterator[Any]:
        """Execute a SQL query and yield results.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Yields:
            Query result rows.
        """
        with self.connect() as conn:
            result = conn.execute(text(query), params or {})
            for row in result:
                yield row

    def to_dataframe(
        self, query: str, params: dict[str, Any] | None = None
    ) -> pd.DataFrame:
        """Execute query and return results as a pandas DataFrame.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            DataFrame with query results.
        """
        logger.info("Executing query", query_length=len(query))
        with self.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params or {})
        logger.info("Query returned rows", row_count=len(df))
        return df

    def execute_script(self, script: str) -> None:
        """Execute a multi-statement SQL script.

        Args:
            script: SQL script with multiple statements separated by semicolons.
        """
        logger.info("Executing SQL script", size=len(script))
        with self.connect() as conn:
            for statement in script.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
            conn.commit()
        logger.info("Script executed successfully")

    def table_exists(self, schema: str, table: str) -> bool:
        """Check if a table exists in the given schema.

        Args:
            schema: Schema name.
            table: Table name.

        Returns:
            True if table exists, False otherwise.
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = :schema
                AND table_name = :table
            )
        """
        with self.connect() as conn:
            result = conn.execute(text(query), {"schema": schema, "table": table})
            return result.scalar() is True

    def truncate_table(self, schema: str, table: str) -> None:
        """Truncate a table (removes all rows).

        Args:
            schema: Schema name.
            table: Table name.
        """
        logger.warning("Truncating table", schema=schema, table=table)
        with self.session() as session:
            session.execute(text(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE'))

    def close(self) -> None:
        """Close the engine and release all connections."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database engine closed")

    def __enter__(self) -> "PostgresConnector":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
