import logging

import pysnow
from django.conf import settings
from django.utils import timezone
from requests.exceptions import HTTPError

from ..models import ChangeRequest
from .exceptions import ChangeRequestException


logger = logging.getLogger('django_snow')


class ChangeRequestHandler:
    """
    SNow Change Request Handler.
    """

    group_guid_dict = {}

    # Service Now table REST endpoints
    CHANGE_REQUEST_TABLE_PATH = '/table/change_request'
    USER_GROUP_TABLE_PATH = '/table/sys_user_group'

    def __init__(self):
        self._client = None
        self.snow_instance = settings.SNOW_INSTANCE
        self.snow_api_user = settings.SNOW_API_USER
        self.snow_api_pass = settings.SNOW_API_PASS
        self.snow_assignment_group = getattr(settings, 'SNOW_ASSIGNMENT_GROUP', None)
        self.snow_default_cr_type = getattr(settings, 'SNOW_DEFAULT_CHANGE_TYPE', 'standard')

    def create_change_request(self, title, description, assignment_group=None, payload=None):
        """
        Create a change request with the given payload.
        """
        client = self._get_client()
        change_requests = client.resource(api_path=self.CHANGE_REQUEST_TABLE_PATH)
        payload = payload or {}
        payload['short_description'] = title
        payload['description'] = description

        if 'type' not in payload:
            payload['type'] = self.snow_default_cr_type
        if 'assignment_group' not in payload:
            payload['assignment_group'] = self.get_snow_group_guid(assignment_group or self.snow_assignment_group)

        try:
            result = change_requests.create(payload=payload)
        except HTTPError as e:
            logger.error('Could not create change request due to %s', e.response.text)
            raise ChangeRequestException('Could not create change request due to %s.' % e.response.text)

        # This piece of code is for legacy SNow instances. (probably Geneva and before it)
        if 'error' in result:
            logger.error('Could not create change request due to %s', result['error'])
            raise ChangeRequestException('Could not create change request due to %s' % result['error'])

        change_request = ChangeRequest.objects.create(
            sys_id=result['sys_id'],
            number=result['number'],
            title=result['short_description'],
            description=result['description'],
            assignment_group_guid=result['assignment_group']['value'],
            state=result['state']
        )

        return change_request

    def close_change_request(self, change_request):
        """Mark the change request as completed."""

        payload = {'state': ChangeRequest.TICKET_STATE_COMPLETE}
        change_request.closed_time = timezone.now()
        self.update_change_request(change_request, payload)

    def close_change_request_with_error(self, change_request, payload):
        """Mark the change request as completed with error.

        The possible keys for the payload are:
            * `title`
            * `description`

        :param change_request: The change request to be closed
        :type change_request: :class:`django_snow.models.ChangeRequest`
        :param payload: A dict of data to be updated while closing change request
        :type payload: dict
        """
        payload['state'] = ChangeRequest.TICKET_STATE_COMPLETE_WITH_ERRORS
        change_request.closed_time = timezone.now()
        self.update_change_request(change_request, payload)

    def update_change_request(self, change_request, payload):
        """Update the change request with the data from the kwargs.

        The possible keys for the payload are:
            * `title`
            * `description`
            * `state`

        :param change_request: The change request to be updated
        :type change_request: :class:`django_snow.models.ChangeRequest`
        :param payload: A dict of data to be updated while updating the change request
        :type payload: dict
        """
        client = self._get_client()

        # Get the record and update it
        change_requests = client.resource(api_path=self.CHANGE_REQUEST_TABLE_PATH)

        try:
            result = change_requests.update(query={'sys_id': change_request.sys_id.hex}, payload=payload)
        except HTTPError as e:
            logger.error('Could not update change request due to %s', e.response.text)
            raise ChangeRequestException('Could not update change request due to %s' % e.response.text)

        # This piece of code is for legacy SNow instances. (probably Geneva and before it)
        if 'error' in result:
            logger.error('Could not update change request due to %s', result['error'])
            raise ChangeRequestException('Could not update change request due to %s' % result['error'])

        change_request.state = result['state']
        change_request.title = result['short_description']
        change_request.description = result['description']
        change_request.assignment_group_guid = result['assignment_group']['value']
        change_request.save()

        return result

    def _get_client(self):
        if self._client is None:
            self._client = pysnow.Client(
                instance=self.snow_instance, user=self.snow_api_user, password=self.snow_api_pass
            )
        return self._client

    def get_snow_group_guid(self, group_name):
        """
        Get the SNow Group's GUID from the Group Name
        """

        if group_name not in self.group_guid_dict:
            client = self._get_client()
            user_groups = client.resource(api_path=self.USER_GROUP_TABLE_PATH)
            response = user_groups.get(query={'name': group_name})
            result = response.one()
            self.group_guid_dict[group_name] = result['sys_id']

        return self.group_guid_dict[group_name]

    def clear_group_guid_cache(self):
        """
        Clear the SNow Group Name - GUID cache.
        """
        self.group_guid_dict.clear()
