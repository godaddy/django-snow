import uuid

from django.test import TestCase, override_settings

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
    SNOW_ASSIGNMENT_GROUP='dev-networking'
)
@mock.patch('django_snow.helpers.snow_request_handler.pysnow')
class TestChangeRequestHandler(TestCase):

    def setUp(self):
        self.mock_pysnow_client = mock.MagicMock()
        self.change_request_handler = ChangeRequestHandler()

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
        self.assertEqual(self.change_request_handler.CHANGE_REQUEST_TABLE_NAME, 'change_request')
        self.assertEqual(self.change_request_handler.USER_GROUP_TABLE_NAME, 'sys_user_group')
        self.assertEqual(self.change_request_handler.snow_assignment_group, 'dev-networking')

    @mock.patch('django_snow.helpers.snow_request_handler.ChangeRequestHandler._get_snow_group_guid')
    def test_create_change_request(self, mock_get_snow_group_guid, mock_pysnow):
        fake_insert_retval = {
            'sys_id': uuid.uuid4(),
            'number': 'CHG0000001',
            'short_description': 'bar',
            'description': 'herp',
            'assignment_group': {'value': uuid.uuid4()},
            'state': '2'
        }
        self.mock_pysnow_client.insert.return_value = fake_insert_retval
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        co = self.change_request_handler.create_change_request(
            'title', 'description', assignment_group='assignment_group'
        )
        last_co = ChangeRequest.objects.last()

        mock_get_snow_group_guid.assert_called_with('assignment_group')
        self.assertEqual(co.pk, last_co.pk)
        self.assertEqual(co.sys_id, fake_insert_retval['sys_id'])
        self.assertEqual(co.number, fake_insert_retval['number'])
        self.assertEqual(co.title, fake_insert_retval['short_description'])
        self.assertEqual(co.description, fake_insert_retval['description'])
        self.assertEqual(co.assignment_group_guid, fake_insert_retval['assignment_group']['value'])

    @mock.patch('django_snow.helpers.snow_request_handler.ChangeRequestHandler._get_snow_group_guid')
    def test_create_change_request_raises_exception_when_error_in_result(self, mock_get_snow_group_guid, mock_pysnow):
        fake_insert_retval = {
            'error': 'some error message'
        }
        self.mock_pysnow_client.insert.return_value = fake_insert_retval
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        with self.assertRaises(ChangeRequestException):
            self.change_request_handler.create_change_request(
                'title', 'description', assignment_group='assignment_group'
            )

    @mock.patch('django_snow.helpers.snow_request_handler.ChangeRequestHandler.update_change_request')
    def test_close_change_request(self, mock_update_request, mock_pysnow):
        mock_update_request.return_value = 'foo'
        change_request_handler = ChangeRequestHandler()

        change_request_handler.close_change_request('some change order')

        mock_update_request.assert_called_with('some change order', {'state': ChangeRequest.TICKET_STATE_COMPLETE})

    @mock.patch('django_snow.helpers.snow_request_handler.ChangeRequestHandler.update_change_request')
    def test_close_change_request_with_error(self, mock_update_request, mock_pysnow):
        mock_update_request.return_value = 'foo'
        change_request_handler = ChangeRequestHandler()
        payload = {'description': 'foo'}
        change_request_handler.close_change_request_with_error('some change order', payload)

        mock_update_request.assert_called_with(
            'some change order', {'state': ChangeRequest.TICKET_STATE_COMPLETE_WITH_ERRORS, 'description': 'foo'}
        )

    def test_update_change_request(self, mock_pysnow):
        fake_query = mock.MagicMock()
        fake_change_order = mock.MagicMock()

        fake_query.update.return_value = {'state': ChangeRequest.TICKET_STATE_COMPLETE}
        self.mock_pysnow_client.query.return_value = fake_query
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        ret_val = self.change_request_handler.update_change_request(fake_change_order, payload='{"foo": "bar"}')
        self.assertEqual(fake_change_order.state, ChangeRequest.TICKET_STATE_COMPLETE)
        self.assertEqual(ret_val, {'state': ChangeRequest.TICKET_STATE_COMPLETE})

    def test_update_change_request_raises_exception(self, mock_pysnow):
        fake_query = mock.MagicMock()
        fake_change_order = mock.MagicMock()

        fake_query.update.return_value = {'error': '3'}
        self.mock_pysnow_client.query.return_value = fake_query
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        with self.assertRaises(ChangeRequestException):
            self.change_request_handler.update_change_request(fake_change_order, payload='{"foo": "bar"}')

    def test__get_snow_group_guid_cached_result(self, mock_pysnow):
        self.change_request_handler.group_guid_dict['foo'] = 'bar'
        self.assertEqual(self.change_request_handler._get_snow_group_guid('foo'), 'bar')

    def test__get_snow_group_guid(self, mock_pysnow):
        fake_query = mock.MagicMock()
        fake_query.get_one.return_value = {'sys_id': 'yo'}
        self.mock_pysnow_client.query.return_value = fake_query
        mock_pysnow.Client.return_value = self.mock_pysnow_client

        self.assertEqual(self.change_request_handler._get_snow_group_guid('hello'), 'yo')
