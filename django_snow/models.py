from django.core.validators import MaxLengthValidator
from django.db import models


class ChangeRequest(models.Model):
    """
    SNow Change Request Model Class.
    """

    # TODO: Review the states to be included by default. Some are used only in legacy instances (Geneva and before),
    # and some are used only in later instances.
    # https://docs.servicenow.com/bundle/kingston-it-service-management/page/product/change-management/task/state-model-activate-tasks.html

    # The state of the Change Request
    TICKET_STATE_OPEN = '1'
    TICKET_STATE_IN_PROGRESS = '2'
    TICKET_STATE_COMPLETE = '3'
    TICKET_STATE_COMPLETE_WITH_ERRORS = '4'
    TICKET_STATE_CHOICES = (
        (TICKET_STATE_OPEN, 'Open'),
        (TICKET_STATE_IN_PROGRESS, 'In Progress'),
        (TICKET_STATE_COMPLETE, 'Complete'),
        (TICKET_STATE_COMPLETE_WITH_ERRORS, 'Complete With Errors'),
    )

    # The 32 character GUID for a SNow record
    sys_id = models.UUIDField(
        max_length=32,
        primary_key=True
    )

    number = models.CharField(
        max_length=32,
        help_text="The Change Order number"
    )

    title = models.CharField(
        max_length=160,  # From the Change Request Title field's maxlength
        help_text="Title of the ServiceNow Change Request"
    )

    description = models.TextField(
        # From the Change Request Description's data-length attribute
        validators=[MaxLengthValidator(4000)],
        help_text="Description of the ServiceNow Change Request"
    )

    # The GUID of the Group to which the Ticket was assigned to
    assignment_group_guid = models.UUIDField(
        max_length=32
    )

    state = models.CharField(
        max_length=3,  # TODO: Review this decision.
        choices=TICKET_STATE_CHOICES,
        help_text='The current state the change order is in.'
    )

    # The time at which the Change Request was created.
    created_time = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when the Change Request was created'
    )

    # The time at which the Change Request was closed.
    closed_time = models.DateTimeField(
        null=True,
        help_text='Timestamp when the Change Request was closed'
    )

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = 'service-now change request'
        verbose_name_plural = 'service-now change requests'
