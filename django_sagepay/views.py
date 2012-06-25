from __future__ import absolute_import

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.utils import timezone

from .models import SagePayTransaction
from .utils import encode_notification_acknowledgement

class BaseNotificationView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        # We only override this method so we can apply the CSRF decorator
        return super(BaseNotificationView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = self.notification_response(request)
        return HttpResponse(encode_notification_acknowledgement(response),
            content_type='text/plain')

    def notification_response(self, request):
        data = request.POST
        # Check we can find associated transaction
        try:
            transaction = SagePayTransaction.objects.select_for_update().get(
                vendor_tx_id=data.get('VendorTxCode', ''))
        except SagePayTransaction.DoesNotExist:
            return self.transaction_not_found_response()
        # Check the signature is valid
        if not transaction.is_valid_signature(data):
            return self.invalid_signature_response(transaction)
        # Check that we haven't already processed a response to this
        # transaction
        if transaction.notification_date is not None:
            return self.transaction_already_complete_response(transaction)
        # Add notification data to transaction object
        transaction.notification_date = timezone.now()
        transaction.notification_data = data
        # Handle the notification appropriately
        if data['Status'] == 'OK':
            self.handle_transaction_success(transaction)
            redirect_url = self.get_success_url(transaction)
        else:
            self.handle_transaction_failure(transaction)
            redirect_url = self.get_failure_url(transaction)
        # Get the response to send back
        response = self.acknowledge_transaction_response(transaction, redirect_url)
        # Save the transaction back to the db
        transaction.acknowledgement_data = response
        transaction.save()
        return response

    def transaction_not_found_response(self):
        return {
            'Status': 'ERROR',
            'StatusDetail': 'VendorTxCode did not match any transaction',
            'RedirectURL': self.get_default_redirect_url()
        }

    def invalid_signature_response(self, transaction):
        return {
            'Status': 'INVALID',
            'StatusDetail': 'VPSSignature did not match',
            'RedirectURL': self.get_failure_url(transaction)
        }

    def transaction_already_complete_response(self, transaction):
        return {
            'Status': 'ERROR',
            'StatusDetail': 'Transaction already processed',
            'RedirectURL': self.get_failure_url(transaction)
        }

    def acknowledge_transaction_response(self, transaction, redirect_url):
        # We should respond 'OK', even to failed transactions, to acknowledge
        # that we have understood and processed the notification. The only
        # exception is the (very rare) notification status of 'ERROR' to which
        # we should respond 'INVALID' (according to SagePay docs).
        status = transaction.notification_data['Status']
        return {
            'Status': 'OK' if status != 'ERROR' else 'INVALID',
            'RedirectURL': redirect_url,
            'StatusDetail': ''
        }

    def handle_transaction_success(self, transaction):
        # You must implement this method in your subclass
        raise NotImplementedError()

    def handle_transaction_failure(self, transaction):
        # Very often there's nothing to do in response to a failed transaction
        # so you don't necessarily have to implement this
        pass

    def get_success_url(self, transaction):
        """
        URL to which to redirect the user after a successful transaction
        """
        try:
            return transaction.extra_data['success_url']
        except KeyError:
            return self.get_default_redirect_url()

    def get_failure_url(self, transaction):
        """
        URL to which to redirect the user after a failed transaction
        """
        try:
            return transaction.extra_data['failure_url']
        except KeyError:
            return self.get_default_redirect_url()

    def get_default_redirect_url(self):
        """
        URL to which to redirect the user if we can't find the corresponding
        transaction, or if the transaction fails to specify a return URL.

        This will only be used in very exceptional circumstances, not as part
        of the normal workflow.
        """
        # By default, we just send the user to the homepage
        return self.request.build_absolute_uri('/')
