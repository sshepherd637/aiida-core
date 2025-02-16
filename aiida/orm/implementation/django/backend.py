# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""Django implementation of `aiida.orm.implementation.backends.Backend`."""
from contextlib import contextmanager

# pylint: disable=import-error,no-name-in-module
from django.db import models, transaction

from aiida.backends.djsite.manager import DjangoBackendManager

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

__all__ = ('DjangoBackend',)


class DjangoBackend(SqlBackend[models.Model]):
    """Django implementation of `aiida.orm.implementation.backends.Backend`."""

    def __init__(self):
        """Construct the backend instance by initializing all the collections."""
        self._authinfos = authinfos.DjangoAuthInfoCollection(self)
        self._comments = comments.DjangoCommentCollection(self)
        self._computers = computers.DjangoComputerCollection(self)
        self._groups = groups.DjangoGroupCollection(self)
        self._logs = logs.DjangoLogCollection(self)
        self._nodes = nodes.DjangoNodeCollection(self)
        self._backend_manager = DjangoBackendManager()
        self._users = users.DjangoUserCollection(self)

    def migrate(self):
        self._backend_manager.migrate()

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
        return querybuilder.DjangoQueryBuilder(self)

    @property
    def users(self):
        return self._users

    @staticmethod
    def transaction():
        """Open a transaction to be used as a context manager."""
        return transaction.atomic()

    @staticmethod
    def get_session():
        """Return a database session that can be used by the `QueryBuilder` to perform its query.

        If there is an exception within the context then the changes will be rolled back and the state will
        be as before entering.  Transactions can be nested.

        :return: an instance of :class:`sqlalchemy.orm.session.Session`
        """
        from aiida.backends.djsite import get_scoped_session
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
        try:
            yield self.get_connection().cursor()
        finally:
            pass

    def execute_raw(self, query):
        """Execute a raw SQL statement and return the result.

        :param query: a string containing a raw SQL statement
        :return: the result of the query
        """
        with self.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()

        return results

    @staticmethod
    def get_connection():
        """
        Get the Django connection

        :return: the django connection
        """
        # pylint: disable=import-error,no-name-in-module
        from django.db import connection
        # For now we just return the global but if we ever support multiple Django backends
        # being loaded this should be specific to this backend
        return connection
