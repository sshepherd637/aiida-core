# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""SqlAlchemy implementation of `aiida.orm.implementation.backends.Backend`."""
from contextlib import contextmanager

from aiida.backends.sqlalchemy.models import base
from aiida.backends.sqlalchemy.manager import SqlaBackendManager

from ..sql.backends import SqlBackend
from . import authinfos
from . import comments
from . import computers
from . import convert
from . import groups
from . import logs
from . import nodes
from . import querybuilder
from . import users

__all__ = ('SqlaBackend',)


class SqlaBackend(SqlBackend[base.Base]):
    """SqlAlchemy implementation of `aiida.orm.implementation.backends.Backend`."""

    def __init__(self):
        """Construct the backend instance by initializing all the collections."""
        self._authinfos = authinfos.SqlaAuthInfoCollection(self)
        self._comments = comments.SqlaCommentCollection(self)
        self._computers = computers.SqlaComputerCollection(self)
        self._groups = groups.SqlaGroupCollection(self)
        self._logs = logs.SqlaLogCollection(self)
        self._nodes = nodes.SqlaNodeCollection(self)
        self._schema_manager = SqlaBackendManager()
        self._users = users.SqlaUserCollection(self)

    def migrate(self):
        self._schema_manager.migrate()

    @property
    def authinfos(self):
        return self._authinfos

    @property
    def comments(self):
        return self._comments

    @property
    def computers(self):
        return self._computers

    @property
    def groups(self):
        return self._groups

    @property
    def logs(self):
        return self._logs

    @property
    def nodes(self):
        return self._nodes

    def query(self):
        return querybuilder.SqlaQueryBuilder(self)

    @property
    def users(self):
        return self._users

    @contextmanager
    def transaction(self):
        """Open a transaction to be used as a context manager.

        If there is an exception within the context then the changes will be rolled back and the state will be as before
        entering. Transactions can be nested.
        """
        session = self.get_session()
        nested = session.transaction.nested
        try:
            session.begin_nested()
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if not nested:
                # Make sure to commit the outermost session
                session.commit()

    @staticmethod
    def get_session():
        """Return a database session that can be used by the `QueryBuilder` to perform its query.

        :return: an instance of :class:`sqlalchemy.orm.session.Session`
        """
        from aiida.backends.sqlalchemy import get_scoped_session
        return get_scoped_session()

    # Below are abstract methods inherited from `aiida.orm.implementation.sql.backends.SqlBackend`

    def get_backend_entity(self, model):
        """Return a `BackendEntity` instance from a `DbModel` instance."""
        return convert.get_backend_entity(model, self)

    @contextmanager
    def cursor(self):
        """Return a psycopg cursor to be used in a context manager.

        :return: a psycopg cursor
        :rtype: :class:`psycopg2.extensions.cursor`
        """
        from aiida.backends import sqlalchemy as sa
        try:
            connection = sa.ENGINE.raw_connection()
            yield connection.cursor()
        finally:
            self.get_connection().close()

    def execute_raw(self, query):
        """Execute a raw SQL statement and return the result.

        :param query: a string containing a raw SQL statement
        :return: the result of the query
        """
        from sqlalchemy.exc import ResourceClosedError  # pylint: disable=import-error,no-name-in-module

        with self.transaction() as session:
            queryset = session.execute(query)

            try:
                results = queryset.fetchall()
            except ResourceClosedError:
                return None

        return results

    @staticmethod
    def get_connection():
        """Get the SQLA database connection

        :return: the SQLA database connection
        """
        from aiida.backends import sqlalchemy as sa
        return sa.ENGINE.raw_connection()
