# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""Serialization tests"""

import types

import numpy as np

from aiida import orm
from aiida.orm.utils import serialize
from aiida.backends.testbase import AiidaTestCase


class TestSerialize(AiidaTestCase):
    """Tests for the YAML serializer and deserializer."""

    def test_serialize_round_trip(self):
        """
        Test the serialization of a dictionary with Nodes in various data structure
        Also make sure that the serialized data is json-serializable
        """
        node_a = orm.Data().store()
        node_b = orm.Data().store()

        data = {'test': 1, 'list': [1, 2, 3, node_a], 'dict': {('Si',): node_b, 'foo': 'bar'}, 'baz': 'aar'}

        serialized_data = serialize.serialize(data)
        deserialized_data = serialize.deserialize_unsafe(serialized_data)

        # For now manual element-for-element comparison until we come up with general
        # purpose function that can equate two node instances properly
        self.assertEqual(data['test'], deserialized_data['test'])
        self.assertEqual(data['baz'], deserialized_data['baz'])
        self.assertEqual(data['list'][:3], deserialized_data['list'][:3])
        self.assertEqual(data['list'][3].uuid, deserialized_data['list'][3].uuid)
        self.assertEqual(data['dict'][('Si',)].uuid, deserialized_data['dict'][('Si',)].uuid)

    def test_serialize_group(self):
        """
        Test that serialization and deserialization of Groups works.
        Also make sure that the serialized data is json-serializable
        """
        group_name = 'groupie'
        group_a = orm.Group(label=group_name).store()

        data = {'group': group_a}

        serialized_data = serialize.serialize(data)
        deserialized_data = serialize.deserialize_unsafe(serialized_data)

        self.assertEqual(data['group'].uuid, deserialized_data['group'].uuid)
        self.assertEqual(data['group'].label, deserialized_data['group'].label)

    def test_serialize_node_round_trip(self):
        """Test you can serialize and deserialize a node"""
        node = orm.Data().store()
        deserialized = serialize.deserialize_unsafe(serialize.serialize(node))
        self.assertEqual(node.uuid, deserialized.uuid)

    def test_serialize_group_round_trip(self):
        """Test you can serialize and deserialize a group"""
        group = orm.Group(label='test_serialize_group_round_trip').store()
        deserialized = serialize.deserialize_unsafe(serialize.serialize(group))

        self.assertEqual(group.uuid, deserialized.uuid)
        self.assertEqual(group.label, deserialized.label)

    def test_serialize_computer_round_trip(self):
        """Test you can serialize and deserialize a computer"""
        computer = self.computer
        deserialized = serialize.deserialize_unsafe(serialize.serialize(computer))

        # pylint: disable=no-member
        self.assertEqual(computer.uuid, deserialized.uuid)
        self.assertEqual(computer.label, deserialized.label)

    def test_serialize_unstored_node(self):
        """Test that you can't serialize an unstored node"""
        node = orm.Data()

        with self.assertRaises(ValueError):
            serialize.serialize(node)

    def test_serialize_unstored_group(self):
        """Test that you can't serialize an unstored group"""
        group = orm.Group(label='test_serialize_unstored_group')

        with self.assertRaises(ValueError):
            serialize.serialize(group)

    def test_serialize_unstored_computer(self):
        """Test that you can't serialize an unstored node"""
        computer = orm.Computer('test_computer', 'test_host')

        with self.assertRaises(ValueError):
            serialize.serialize(computer)

    def test_mixed_attribute_normal_dict(self):
        """Regression test for #3092.

        The yaml mapping constructor in `aiida.orm.utils.serialize` was not properly "deeply" reconstructing nested
        mappings, causing a mix of attribute dictionaries and normal dictionaries to lose information in a round-trip.

        If a nested `AttributeDict` contained a normal dictionary, the content of the latter would be lost during the
        deserialization, despite the information being present in the serialized yaml dump.
        """
        from aiida.common.extendeddicts import AttributeDict

        # Construct a nested `AttributeDict`, which should make all nested dictionaries `AttributeDicts` recursively
        dictionary = {'nested': AttributeDict({'dict': 'string', 'value': 1})}
        attribute_dict = AttributeDict(dictionary)

        # Now add a normal dictionary in the attribute dictionary
        attribute_dict['nested']['normal'] = {'a': 2}

        serialized = serialize.serialize(attribute_dict)
        deserialized = serialize.deserialize_unsafe(serialized)

        self.assertEqual(attribute_dict, deserialized)

    def test_serialize_numpy(self):  # pylint: disable=no-self-use
        """Regression test for #3709

        Check that numpy arrays can be serialized.
        """
        data = np.array([1, 2, 3])

        serialized = serialize.serialize(data)
        deserialized = serialize.deserialize_unsafe(serialized)
        assert np.all(data == deserialized)

    def test_serialize_simplenamespace(self):  # pylint: disable=no-self-use
        """Regression test for #3709

        Check that `types.SimpleNamespace` can be serialized.
        """
        data = types.SimpleNamespace(a=1, b=2.1)

        serialized = serialize.serialize(data)
        deserialized = serialize.deserialize_unsafe(serialized)
        assert data == deserialized
