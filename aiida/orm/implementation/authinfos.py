# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""Module for the backend implementation of the `AuthInfo` ORM class."""

import abc

from .entities import BackendEntity, BackendCollection

__all__ = ('BackendAuthInfo', 'BackendAuthInfoCollection')


class BackendAuthInfo(BackendEntity):
    """Backend implementation for the `AuthInfo` ORM class."""

    METADATA_WORKDIR = 'workdir'

    @property
    @abc.abstractmethod
    def enabled(self):
        """Return whether this instance is enabled.

        :return: boolean, True if enabled, False otherwise
        """

    @enabled.setter
    @abc.abstractmethod
    def enabled(self, value):
        """Set the enabled state

        :param enabled: boolean, True to enable the instance, False to disable it
        """

    @property
    @abc.abstractmethod
    def computer(self):
        """Return the computer associated with this instance.

        :return: :class:`aiida.orm.implementation.computers.BackendComputer`
        """

    @property
    @abc.abstractmethod
    def user(self):
        """Return the user associated with this instance.

        :return: :class:`aiida.orm.implementation.users.BackendUser`
        """

    @abc.abstractmethod
    def get_auth_params(self):
        """Return the dictionary of authentication parameters

        :return: a dictionary with authentication parameters
        """

    @abc.abstractmethod
    def set_auth_params(self, auth_params):
        """Set the dictionary of authentication parameters

        :param auth_params: a dictionary with authentication parameters
        """

    @abc.abstractmethod
    def get_metadata(self):
        """Return the dictionary of metadata

        :return: a dictionary with metadata
        """

    @abc.abstractmethod
    def set_metadata(self, metadata):
        """Set the dictionary of metadata

        :param metadata: a dictionary with metadata
        """


class BackendAuthInfoCollection(BackendCollection[BackendAuthInfo]):
    """The collection of backend `AuthInfo` entries."""

    ENTITY_CLASS = BackendAuthInfo

    @abc.abstractmethod
    def delete(self, pk):
        """Delete an entry from the collection.

        :param pk: the pk of the entry to delete
        """

    @abc.abstractmethod
    def get(self, computer, user):
        """Return an entry from the collection that is configured for the given computer and user

        :param computer: a :class:`aiida.orm.implementation.computers.BackendComputer` instance
        :param user: a :class:`aiida.orm.implementation.users.BackendUser` instance
        :return: :class:`aiida.orm.implementation.authinfos.BackendAuthInfo`
        :raise aiida.common.exceptions.NotExistent: if no entry exists for the computer/user pair
        :raise aiida.common.exceptions.MultipleObjectsError: if multiple entries exist for the computer/user pair
        """
