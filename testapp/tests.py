import uuid

import six
from django.test import TestCase, override_settings
from requests.exceptions import HTTPError

from django_snow.helpers import ChangeRequestHandler
from django_snow.helpers.exceptions import ChangeRequestException
from django_snow.models import ChangeRequest


try:
    from unittest import mock
except ImportError:
    import mock


@override_settings(
    SNOW_INSTANCE='devgodaddy',
    SNOW_API_USER='snow_user',
    SNOW_API_PASS='snow_pass',
    SNOW_ASSIGNMENT_GROUP='assignment_group'
)
@mock.patch('django_snow.helpers.snow_request_handler.pysnow')
class TestChangeRequestHandler(TestCase):

    def setUp(self):
        self.mock_pysnow_client = mock.MagicMock()
        self.change_request_handler = ChangeRequestHandler()

    def tearDown(self):
        self.change_request_handler.clear_group_guid_cache()

    def test__get_client(self, mock_pysnow):
        mock_pysnow.Client.return_value = self.mock_pysnow_client
        self.assertIs(
            self.mock_pysnow_client,
            self.change_request_handler._get_client()
        )

    def test__get_client_once_initialized_returns_same_instance(self, mock_pysnow):
        mock_pysnow.Client.return_value = self.mock_pysnow_client
        self.change_request_handler._get_client()
        self.assertIs(
            self.mock_pysnow_client,
            self.change_request_handler._get_client()
        )

    def test_settings_and_table_name(self, mock_pysnow):
        self.assertEqual(self.change_request_handler._client, None)
        self.assertEqual(self.change_request_handler.snow_instance, 'devgodaddy')
        self.assertEqual(self.change_request_handler.snow_api_user, 'snow_user')
        self.assertEqual(self.change_request_handler.snow_api_pass, 'snow_pass')
        self.assertEqual(self.change_request_handler.snow_assignment_group, 'assignment_group')
        self.assertEqual(self.change_request_handler.snow_default_cr_type, 'standard')
        self.assertEqual(self.change_request_handler.CHANGE_REQUEST_TABLE_PATH, '/table/change_request')
        self.assertEqual(self.change_request_handler.USER_GROUP_TABLE_PATH, '/table/sys_user_group')

    def test_create_change_request(self, mock_pysnow):
        fake_insert_retval = {
            'sys_id': uuid.uuid4(),
            'number': 'CHG0000001',
            'short_description': 'bar',
            'description': 'herp',
            'assignment_group': {'value': uuid.uuid4()},
            'state': '2'
        }

        fake_resource = mock.MagicMock()
        fake_resource.create.return_value = fake_insert_retval

        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        co = self.change_request_handler.create_change_request('Title', 'Description', payload={})
        last_co = ChangeRequest.objects.last()

        self.assertEqual(co.pk, last_co.pk)
        self.assertEqual(co.sys_id, fake_insert_retval['sys_id'])
        self.assertEqual(co.number, fake_insert_retval['number'])
        self.assertEqual(co.title, fake_insert_retval['short_description'])
        self.assertEqual(co.description, fake_insert_retval['description'])
        self.assertEqual(co.assignment_group_guid, fake_insert_retval['assignment_group']['value'])

    def test_create_change_request_parameters(self, mock_pysnow):
        expected_payload = {
            'type': 'normal',
            'assignment_group': 'bar',
            'short_description': 'Title',
            'description': 'Description'
        }

        fake_insert_retval = {
            'sys_id': uuid.uuid4(),
            'number': 'CHG0000001',
            'short_description': 'Title',
            'description': 'Description',
            'assignment_group': {'value': uuid.uuid4()},
            'state': '2'
        }

        fake_resource = mock.MagicMock()
        fake_resource.create.return_value = fake_insert_retval
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        payload = {
            'type': 'normal',
            'assignment_group': 'bar'
        }
        self.change_request_handler.create_change_request('Title', 'Description', None, payload=payload)
        fake_resource.create.assert_called_with(payload=expected_payload)

    def test_create_change_request_default_parameters(self, mock_pysnow):
        expected_payload = {
            'short_description': 'Title',
            'description': 'Description',
            'type': 'standard',
            'assignment_group': 'bar'
        }

        fake_insert_retval = {
            'sys_id': uuid.uuid4(),
            'number': 'CHG0000001',
            'short_description': 'Title',
            'description': 'Description',
            'assignment_group': {'value': uuid.uuid4()},
            'state': '2'
        }

        fake_resource = mock.MagicMock()

        # For Assignment Group GUID
        fake_asgn_group_guid_response = mock.MagicMock()
        fake_asgn_group_guid_response.one.return_value = {'sys_id': 'bar'}
        fake_resource.get.return_value = fake_asgn_group_guid_response

        fake_resource.create.return_value = fake_insert_retval
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        self.change_request_handler.create_change_request('Title', 'Description', None, payload={})
        fake_resource.create.assert_called_with(payload=expected_payload)

    def test_create_change_request_raises_exception_for_http_error(self, mock_pysnow):
        fake_resource = mock.MagicMock()

        fake_exception = HTTPError()
        fake_exception.response = mock.MagicMock()
        fake_exception.response.text.return_value = 'Foobar'

        fake_resource.create.side_effect = fake_exception

        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        with six.assertRaisesRegex(self, ChangeRequestException, 'Could not create change request due to.*'):
            self.change_request_handler.create_change_request('Title', 'Description', None, payload={})

    def test_create_change_request_raises_exception_when_error_in_result(self, mock_pysnow):
        fake_insert_retval = {
            'error': 'some error message'
        }

        fake_resource = mock.MagicMock()
        fake_resource.create.return_value = fake_insert_retval

        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        with six.assertRaisesRegex(self, ChangeRequestException, 'Could not create change request due to.*'):
            self.change_request_handler.create_change_request('Title', 'Description', None, payload={})

    @mock.patch('django_snow.helpers.snow_request_handler.ChangeRequestHandler.update_change_request')
    def test_close_change_request(self, mock_update_request, mock_pysnow):
        fake_change_order = mock.MagicMock()

        mock_update_request.return_value = 'foo'
        change_request_handler = ChangeRequestHandler()

        change_request_handler.close_change_request(fake_change_order)

        mock_update_request.assert_called_with(fake_change_order, {'state': ChangeRequest.TICKET_STATE_COMPLETE})

    @mock.patch('django_snow.helpers.snow_request_handler.ChangeRequestHandler.update_change_request')
    def test_close_change_request_with_error(self, mock_update_request, mock_pysnow):
        fake_change_order = mock.MagicMock()
        mock_update_request.return_value = 'foo'
        change_request_handler = ChangeRequestHandler()
        payload = {'description': 'foo'}
        change_request_handler.close_change_request_with_error(fake_change_order, payload)

        mock_update_request.assert_called_with(
            fake_change_order, {'state': ChangeRequest.TICKET_STATE_COMPLETE_WITH_ERRORS, 'description': 'foo'}
        )

    def test_update_change_request(self, mock_pysnow):
        fake_resource = mock.MagicMock()
        fake_change_order = mock.MagicMock()

        retval = {
            'state': ChangeRequest.TICKET_STATE_COMPLETE,
            'short_description': 'Short Description',
            'description': 'Long Description',
            'assignment_group': {'value': uuid.uuid4()}
        }

        fake_resource.update.return_value = retval
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        ret_val = self.change_request_handler.update_change_request(fake_change_order, payload='{"foo": "bar"}')
        self.assertEqual(fake_change_order.state, ChangeRequest.TICKET_STATE_COMPLETE)
        self.assertEqual(fake_change_order.title, retval['short_description'])
        self.assertEqual(fake_change_order.description, retval['description'])
        self.assertEqual(fake_change_order.assignment_group_guid, retval['assignment_group']['value'])
        self.assertEqual(ret_val, retval)

    def test_update_change_request_raises_exception_for_http_error(self, mock_pysnow):
        fake_resource = mock.MagicMock()
        fake_change_order = mock.MagicMock()

        fake_exception = HTTPError()
        fake_exception.response = mock.MagicMock()
        fake_exception.response.text.return_value = 'Foobar'

        fake_resource.update.side_effect = fake_exception

        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        with six.assertRaisesRegex(self, ChangeRequestException, 'Could not update change request due to '):
            self.change_request_handler.update_change_request(fake_change_order, payload='{"foo": "bar"}')

    def test_update_change_request_raises_exception_for_error_in_result(self, mock_pysnow):
        fake_resource = mock.MagicMock()
        fake_change_order = mock.MagicMock()

        fake_resource.update.return_value = {'error': '3'}
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        with six.assertRaisesRegex(self, ChangeRequestException, 'Could not update change request due to '):
            self.change_request_handler.update_change_request(fake_change_order, payload='{"foo": "bar"}')

    def test_get_snow_group_guid_cached_result(self, mock_pysnow):
        fake_resource = mock.MagicMock()
        fake_response = mock.MagicMock()
        fake_response.one.return_value = {'sys_id': 'bar'}
        fake_resource.get.return_value = fake_response
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        self.change_request_handler.get_snow_group_guid('foo')
        cached_guid = self.change_request_handler.get_snow_group_guid('foo')

        # resource.get() should be called only once, since the value from previous call should have been cached.
        fake_resource.get.assert_called_once_with(query={'name': 'foo'})
        self.assertEqual(cached_guid, 'bar')

    def test_get_snow_group_guid(self, mock_pysnow):
        fake_resource = mock.MagicMock()
        fake_response = mock.MagicMock()
        fake_response.one.return_value = {'sys_id': 'yo'}
        fake_resource.get.return_value = fake_response
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        self.assertEqual(self.change_request_handler.get_snow_group_guid('hello'), 'yo')

    def test_clear_snow_group_guid_cache(self, mock_pysnow):
        fake_resource = mock.MagicMock()
        fake_response = mock.MagicMock()
        fake_response.one.return_value = {'sys_id': 'some_id'}
        fake_resource.get.return_value = fake_response
        self.mock_pysnow_client.resource.return_value = fake_resource
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        self.change_request_handler.get_snow_group_guid('hello')
        self.change_request_handler.get_snow_group_guid('hello')
        self.assertEqual(fake_resource.get.call_count, 1)

        self.change_request_handler.clear_group_guid_cache()
        self.change_request_handler.get_snow_group_guid('hello')
        self.change_request_handler.get_snow_group_guid('hello')
        self.assertEqual(fake_resource.get.call_count, 2)
