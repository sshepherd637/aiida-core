# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
# pylint: disable=invalid-name,protected-access
"""Tests for `verdi database`."""
import enum

from click.testing import CliRunner
import pytest

from aiida.backends.testbase import AiidaTestCase
from aiida.cmdline.commands import cmd_database
from aiida.common.links import LinkType
from aiida.orm import Data, CalculationNode, WorkflowNode


class TestVerdiDatabasaIntegrity(AiidaTestCase):
    """Tests for `verdi database integrity`."""

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        """Create a basic valid graph that should help detect false positives."""
        super().setUpClass(*args, **kwargs)
        data_input = Data().store()
        data_output = Data().store()
        calculation = CalculationNode()
        workflow_parent = WorkflowNode()
        workflow_child = WorkflowNode()

        workflow_parent.add_incoming(data_input, link_label='input', link_type=LinkType.INPUT_WORK)
        workflow_parent.store()

        workflow_child.add_incoming(data_input, link_label='input', link_type=LinkType.INPUT_WORK)
        workflow_child.add_incoming(workflow_parent, link_label='call', link_type=LinkType.CALL_WORK)
        workflow_child.store()

        calculation.add_incoming(data_input, link_label='input', link_type=LinkType.INPUT_CALC)
        calculation.add_incoming(workflow_child, link_label='input', link_type=LinkType.CALL_CALC)
        calculation.store()

        data_output.add_incoming(calculation, link_label='output', link_type=LinkType.CREATE)
        data_output.add_incoming(workflow_child, link_label='output', link_type=LinkType.RETURN)
        data_output.add_incoming(workflow_parent, link_label='output', link_type=LinkType.RETURN)

    def setUp(self):
        self.refurbish_db()
        self.cli_runner = CliRunner()

    def test_detect_invalid_links_workflow_create(self):
        """Test `verdi database integrity detect-invalid-links` outgoing `create` from `workflow`."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        # Create an invalid link: outgoing `create` from a workflow
        data = Data().store().backend_entity
        workflow = WorkflowNode().store().backend_entity

        data.add_incoming(workflow, link_type=LinkType.CREATE, link_label='create')

        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)

    def test_detect_invalid_links_calculation_return(self):
        """Test `verdi database integrity detect-invalid-links` outgoing `return` from `calculation`."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        # Create an invalid link: outgoing `return` from a calculation
        data = Data().store().backend_entity
        calculation = CalculationNode().store().backend_entity

        data.add_incoming(calculation, link_type=LinkType.RETURN, link_label='return')

        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)

    def test_detect_invalid_links_calculation_call(self):
        """Test `verdi database integrity detect-invalid-links` outgoing `call` from `calculation`."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        # Create an invalid link: outgoing `call` from a calculation
        worklow = WorkflowNode().store().backend_entity
        calculation = CalculationNode().store().backend_entity

        worklow.add_incoming(calculation, link_type=LinkType.CALL_WORK, link_label='call')

        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)

    def test_detect_invalid_links_create_links(self):
        """Test `verdi database integrity detect-invalid-links` when there are multiple incoming `create` links."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        # Create an invalid link: two `create` links
        data = Data().store().backend_entity
        calculation = CalculationNode().store().backend_entity

        data.add_incoming(calculation, link_type=LinkType.CREATE, link_label='create')
        data.add_incoming(calculation, link_type=LinkType.CREATE, link_label='create')

        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)

    def test_detect_invalid_links_call_links(self):
        """Test `verdi database integrity detect-invalid-links` when there are multiple incoming `call` links."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        # Create an invalid link: two `call` links
        workflow = WorkflowNode().store().backend_entity
        calculation = CalculationNode().store().backend_entity

        calculation.add_incoming(workflow, link_type=LinkType.CALL_CALC, link_label='call')
        calculation.add_incoming(workflow, link_type=LinkType.CALL_CALC, link_label='call')

        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)

    def test_detect_invalid_links_unknown_link_type(self):
        """Test `verdi database integrity detect-invalid-links` when link type is invalid."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        class WrongLinkType(enum.Enum):

            WRONG_CREATE = 'wrong_create'

        # Create an invalid link: invalid link type
        data = Data().store().backend_entity
        calculation = CalculationNode().store().backend_entity

        data.add_incoming(calculation, link_type=WrongLinkType.WRONG_CREATE, link_label='create')

        result = self.cli_runner.invoke(cmd_database.detect_invalid_links, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)

    def test_detect_invalid_nodes_unknown_node_type(self):
        """Test `verdi database integrity detect-invalid-nodes` when node type is invalid."""
        result = self.cli_runner.invoke(cmd_database.detect_invalid_nodes, [])
        self.assertEqual(result.exit_code, 0)
        self.assertClickResultNoException(result)

        # Create a node with invalid type: since there are a lot of validation rules that prevent us from creating an
        # invalid node type normally, we have to do it manually on the database model instance before storing
        node = Data()
        node.backend_entity.dbmodel.node_type = '__main__.SubClass.'
        node.store()

        result = self.cli_runner.invoke(cmd_database.detect_invalid_nodes, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIsNotNone(result.exception)


@pytest.mark.usefixtures('aiida_profile')
def tests_database_version(run_cli_command, manager):
    """Test the ``verdi database version`` command."""
    backend_manager = manager.get_backend_manager()
    result = run_cli_command(cmd_database.database_version)
    assert result.output_lines[0].endswith(backend_manager.get_schema_generation_database())
    assert result.output_lines[1].endswith(backend_manager.get_schema_version_database())


@pytest.mark.usefixtures('clear_database_before_test')
def tests_database_summary(aiida_localhost, run_cli_command):
    """Test the ``verdi database summary`` command with the ``-verbosity`` option."""
    from aiida import orm
    node = orm.Dict().store()
    result = run_cli_command(cmd_database.database_summary, ['--verbosity', 'info'])
    assert aiida_localhost.label in result.output
    assert node.node_type in result.output
