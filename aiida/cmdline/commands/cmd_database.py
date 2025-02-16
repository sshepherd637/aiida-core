# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""`verdi database` commands."""

import click

from aiida.common import exceptions
from aiida.cmdline.commands.cmd_verdi import verdi
from aiida.cmdline.params import options
from aiida.cmdline.utils import decorators, echo
from aiida.backends.general.migrations.duplicate_uuids import TABLES_UUID_DEDUPLICATION


@verdi.group('database')
def verdi_database():
    """Inspect and manage the database."""


@verdi_database.command('version')
def database_version():
    """Show the version of the database.

    The database version is defined by the tuple of the schema generation and schema revision.
    """
    from aiida.manage.manager import get_manager

    manager = get_manager()
    manager._load_backend(schema_check=False)  # pylint: disable=protected-access
    backend_manager = manager.get_backend_manager()

    echo.echo('Generation: ', bold=True, nl=False)
    echo.echo(backend_manager.get_schema_generation_database())
    echo.echo('Revision:   ', bold=True, nl=False)
    echo.echo(backend_manager.get_schema_version_database())


@verdi_database.command('migrate')
@options.FORCE()
def database_migrate(force):
    """Migrate the database to the latest schema version."""
    from aiida.manage.manager import get_manager
    from aiida.engine.daemon.client import get_daemon_client

    client = get_daemon_client()
    if client.is_daemon_running:
        echo.echo_critical('Migration aborted, the daemon for the profile is still running.')

    manager = get_manager()
    profile = manager.get_profile()
    backend = manager._load_backend(schema_check=False)  # pylint: disable=protected-access

    if force:
        try:
            backend.migrate()
        except (exceptions.ConfigurationError, exceptions.DatabaseMigrationError) as exception:
            echo.echo_critical(str(exception))
        return

    echo.echo_warning('Migrating your database might take a while and is not reversible.')
    echo.echo_warning('Before continuing, make sure you have completed the following steps:')
    echo.echo_warning('')
    echo.echo_warning(' 1. Make sure you have no active calculations and workflows.')
    echo.echo_warning(' 2. If you do, revert the code to the previous version and finish running them first.')
    echo.echo_warning(' 3. Stop the daemon using `verdi daemon stop`')
    echo.echo_warning(' 4. Make a backup of your database and repository')
    echo.echo_warning('')
    echo.echo_warning('', nl=False)

    expected_answer = 'MIGRATE NOW'
    confirm_message = 'If you have completed the steps above and want to migrate profile "{}", type {}'.format(
        profile.name, expected_answer
    )

    try:
        response = click.prompt(confirm_message)
        while response != expected_answer:
            response = click.prompt(confirm_message)
    except click.Abort:
        echo.echo('\n')
        echo.echo_critical('Migration aborted, the data has not been affected.')
    else:
        try:
            backend.migrate()
        except (exceptions.ConfigurationError, exceptions.DatabaseMigrationError) as exception:
            echo.echo_critical(str(exception))
        else:
            echo.echo_success('migration completed')


@verdi_database.group('integrity')
def verdi_database_integrity():
    """Check the integrity of the database and fix potential issues."""


@verdi_database_integrity.command('detect-duplicate-uuid')
@click.option(
    '-t',
    '--table',
    type=click.Choice(TABLES_UUID_DEDUPLICATION),
    default='db_dbnode',
    help='The database table to operate on.'
)
@click.option(
    '-a', '--apply-patch', is_flag=True, help='Actually apply the proposed changes instead of performing a dry run.'
)
def detect_duplicate_uuid(table, apply_patch):
    """Detect and fix entities with duplicate UUIDs.

    Before aiida-core v1.0.0, there was no uniqueness constraint on the UUID column of the node table in the database
    and a few other tables as well. This made it possible to store multiple entities with identical UUIDs in the same
    table without the database complaining. This bug was fixed in aiida-core=1.0.0 by putting an explicit uniqueness
    constraint on UUIDs on the database level. However, this would leave databases created before this patch with
    duplicate UUIDs in an inconsistent state. This command will run an analysis to detect duplicate UUIDs in a given
    table and solve it by generating new UUIDs. Note that it will not delete or merge any rows.
    """
    from aiida.backends.general.migrations.duplicate_uuids import deduplicate_uuids
    from aiida.manage.manager import get_manager

    manager = get_manager()
    manager._load_backend(schema_check=False)  # pylint: disable=protected-access

    try:
        messages = deduplicate_uuids(table=table, dry_run=not apply_patch)
    except Exception as exception:  # pylint: disable=broad-except
        echo.echo_critical(f'integrity check failed: {str(exception)}')
    else:
        for message in messages:
            echo.echo_report(message)

        if apply_patch:
            echo.echo_success('integrity patch completed')
        else:
            echo.echo_success('dry-run of integrity patch completed')


@verdi_database_integrity.command('detect-invalid-links')
@decorators.with_dbenv()
def detect_invalid_links():
    """Scan the database for invalid links."""
    from tabulate import tabulate

    from aiida.manage.database.integrity.sql.links import INVALID_LINK_SELECT_STATEMENTS
    from aiida.manage.manager import get_manager

    integrity_violated = False

    backend = get_manager().get_backend()

    for check in INVALID_LINK_SELECT_STATEMENTS:

        result = backend.execute_prepared_statement(check.sql, check.parameters)

        if result:
            integrity_violated = True
            echo.echo_warning(f'{check.message}:\n')
            echo.echo(tabulate(result, headers=check.headers))

    if not integrity_violated:
        echo.echo_success('no integrity violations detected')
    else:
        echo.echo_critical('one or more integrity violations detected')


@verdi_database_integrity.command('detect-invalid-nodes')
@decorators.with_dbenv()
def detect_invalid_nodes():
    """Scan the database for invalid nodes."""
    from tabulate import tabulate

    from aiida.manage.database.integrity.sql.nodes import INVALID_NODE_SELECT_STATEMENTS
    from aiida.manage.manager import get_manager

    integrity_violated = False

    backend = get_manager().get_backend()

    for check in INVALID_NODE_SELECT_STATEMENTS:

        result = backend.execute_prepared_statement(check.sql, check.parameters)

        if result:
            integrity_violated = True
            echo.echo_warning(f'{check.message}:\n')
            echo.echo(tabulate(result, headers=check.headers))

    if not integrity_violated:
        echo.echo_success('no integrity violations detected')
    else:
        echo.echo_critical('one or more integrity violations detected')


@verdi_database.command('summary')
def database_summary():
    """Summarise the entities in the database."""
    from aiida.cmdline import is_verbose
    from aiida.orm import QueryBuilder, Node, Group, Computer, Comment, Log, User
    data = {}

    # User
    query_user = QueryBuilder().append(User, project=['email'])
    data['Users'] = {'count': query_user.count()}
    if is_verbose():
        data['Users']['emails'] = query_user.distinct().all(flat=True)

    # Computer
    query_comp = QueryBuilder().append(Computer, project=['label'])
    data['Computers'] = {'count': query_comp.count()}
    if is_verbose():
        data['Computers']['labels'] = query_comp.distinct().all(flat=True)

    # Node
    count = QueryBuilder().append(Node).count()
    data['Nodes'] = {'count': count}
    if is_verbose():
        node_types = QueryBuilder().append(Node, project=['node_type']).distinct().all(flat=True)
        data['Nodes']['node_types'] = node_types
        process_types = QueryBuilder().append(Node, project=['process_type']).distinct().all(flat=True)
        data['Nodes']['process_types'] = [p for p in process_types if p]

    # Group
    query_group = QueryBuilder().append(Group, project=['type_string'])
    data['Groups'] = {'count': query_group.count()}
    if is_verbose():
        data['Groups']['type_strings'] = query_group.distinct().all(flat=True)

    # Comment
    count = QueryBuilder().append(Comment).count()
    data['Comments'] = {'count': count}

    # Log
    count = QueryBuilder().append(Log).count()
    data['Logs'] = {'count': count}

    echo.echo_dictionary(data, sort_keys=False, fmt='yaml')
