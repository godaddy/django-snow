import logging

import pysnow
from django.conf import settings

from ..models import ChangeRequest
from .exceptions import ChangeRequestException


logger = logging.getLogger('django_snow')


class ChangeRequestHandler:
    """
    SNow Change Request Handler.
    """

    group_guid_dict = {}

    # Service Now table name
    CHANGE_REQUEST_TABLE_NAME = 'change_request'
    USER_GROUP_TABLE_NAME = 'sys_user_group'

    def __init__(self):
        self._client = None
        self.snow_instance = settings.SNOW_INSTANCE
        self.snow_api_user = settings.SNOW_API_USER
        self.snow_api_pass = settings.SNOW_API_PASS
        self.snow_assignment_group = settings.SNOW_ASSIGNMENT_GROUP

    def create_change_request(self, title, description, co_type='Automated', assignment_group=None):
        client = self._get_client()
        assignment_group_guid = self._get_snow_group_guid(assignment_group or self.snow_assignment_group)
        result = client.insert(
            table=self.CHANGE_REQUEST_TABLE_NAME,
            payload={
                'short_description': title,
                'state': ChangeRequest.TICKET_STATE_OPEN,
                'description': description,
                'type': co_type,
                'assignment_group': assignment_group_guid
            }
        )

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
        """
        Mark the change request as completed
        """
        payload = {'state': ChangeRequest.TICKET_STATE_COMPLETE}
        self.update_change_request(change_request, payload)

    def update_change_request(self, change_request, payload):
        """
        Update the change request with the data from the kwargs
        The possible values for the kwargs keys are :
            * `title`
            * `description`
            * `state`
        """
        client = self._get_client()

        # Get the record and update it
        record = client.query(table=self.CHANGE_REQUEST_TABLE_NAME, query={'sys_id': change_request.sys_id.hex})

        result = record.update(payload=payload)
        if 'error' in result:
            logger.error('Could not update change request due to %s', result['error'])
            raise ChangeRequestException('Could not update change request due to %s' % result['error'])

        change_request.state = result['state']
        change_request.save()

        return result

    def _get_client(self):
        if self._client is None:
            self._client = pysnow.Client(
                instance=self.snow_instance, user=self.snow_api_user, password=self.snow_api_pass
            )
        return self._client

    def _get_snow_group_guid(self, group_name):
        """
        Get the SNow Group's GUID from the Group Name
        """

        if group_name not in self.group_guid_dict:
            client = self._get_client()
            query = client.query(table=self.USER_GROUP_TABLE_NAME, query={'name': group_name})
            result = query.get_one()
            self.group_guid_dict[group_name] = result['sys_id']

        return self.group_guid_dict[group_name]
