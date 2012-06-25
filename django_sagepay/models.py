from __future__ import absolute_import

from base64 import b32encode
import hashlib
import uuid
import sys

from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings

import requests
from requests.exceptions import RequestException
from jsonfield import JSONField

from .utils import (format_money_value, encode_transaction_request,
    decode_transaction_response, truncate_overlong_fields)


VPS_PROTOCOL = '2.23'

# SagePay uses the MD5 hash of these fields to create the request signature
HASH_FIELDS = ('VPSTxId', 'VendorTxCode', 'Status', 'TxAuthNo', 'Vendor',
    'AVSCV2', 'SecurityKey', 'AddressResult', 'PostCodeResult', 'CV2Result',
    'GiftAid', '3DSecureStatus', 'CAVV', 'AddressStatus', 'PayerStatus',
    'CardType', 'Last4Digits')


class SagePayError(Exception):
    status = None


class SagePayTransaction(models.Model):
    # This is the unique string (supplied by us) which SagePay will use to
    # identify our transaction
    vendor_tx_id = models.CharField(unique=True, max_length=40)

    date_created = models.DateTimeField(auto_now_add=True)

    # The data sent to SagePay in order to create the transaction
    request = JSONField()
    # SagePay's response
    response = JSONField()
    # Any additional data which you would like to store on the transaction but
    # doesn't form part of the data to be sent to SagePay
    extra_data = JSONField()

    # The time at which we received notification from SagePay that the
    # transaction has completed
    notification_date = models.DateTimeField(null=True)
    # The transaction status data
    notification_data = JSONField(null=True)
    # The data we sent back to SagePay to acknowledge reciept of the
    # transaction
    acknowledgement_data = JSONField(null=True)

    def is_valid_signature(self, notification_data):
        md5 = hashlib.md5()
        for f in HASH_FIELDS:
            if f == 'Vendor':
                value = self.request.get(f, '')
            elif f == 'SecurityKey':
                value = self.response.get(f, '')
            else:
                value = notification_data.get(f, '')
            md5.update(value)
        signature = md5.hexdigest().upper()
        return signature == notification_data.get('VPSSignature')


def start_transaction(transaction_data, extra_data={}, request=None,
                       url_base=None):
    # Default transaction parameters
    data = {
        'VPSProtocol': VPS_PROTOCOL,
        'TxType': 'PAYMENT',
        # Generate a new transaction ID
        'VendorTxCode': b32encode(uuid.uuid4().bytes).strip('=').lower()
    }
    # Add defaults from settings, if defined
    data.update(getattr(settings, 'SAGEPAY_DEFAULTS', {}))
    # Add user supplied data
    data.update(transaction_data)
    # Ensure all URLs are absolute
    data['NotificationURL'] = ensure_absolute_url(data['NotificationURL'],
            request=request, url_base=url_base)
    for key in ['success_url', 'failure_url']:
        if key in extra_data:
            extra_data[key] = ensure_absolute_url(extra_data[key],
                 request=request, url_base=url_base)

    # Truncate any (non-essential) fields that exceed SagePay's limits; it's
    # better to lose a bit of descriptive data than bork the whole transaction
    data = truncate_overlong_fields(data)
    request_body = encode_transaction_request(data)

    try:
        # Fire request to SagePay which creates the transaction
        response = requests.post(settings.SAGEPAY_URL, data=request_body,
                                 prefetch=True, verify=True)
        # Does nothing on 200, but raises exceptions for other statuses
        response.raise_for_status()
    # RequestException covers network/DNS related problems as well as non-200
    # responses
    except RequestException as e:
        raise SagePayError(repr(e)), None, sys.exc_info()[2]

    response_data = decode_transaction_response(response.text)

    # Anything other than a status of OK throws an exception (Note that SagePay
    # can return the status 'OK REPEATED' if the VendorTxCode refers to an in-
    # progress transaction, but because we generate unique IDs every time we
    # hit SagePay we should never get this -- if we do, it's an error)
    if response_data['Status'] != 'OK':
        exc = SagePayError(response_data['StatusDetail'])
        exc.status = response_data['Status']
        raise exc

    # If all went well, save the transaction object and return the URL to
    # redirect the user to
    SagePayTransaction.objects.create(
        vendor_tx_id=data['VendorTxCode'],
        request=data,
        response=response_data,
        extra_data=extra_data
    )
    # Return the URL to which to redirect the user
    return response_data['NextURL']


def ensure_absolute_url(url, request=None, url_base=None):
    if not url.startswith('http://') and not url.startswith('https://'):
        if not url_base:
            if not request:
                raise SagePayError('No url_base or request supplied: cannot '
                                   'construct absolute URL')
            url = request.build_absolute_uri(url)
        else:
            url = '{0}{1}'.format(url_base.rstrip('/'), url)
    # Cast to string in case we've been supplied with a lazily reversed
    # URL object
    return unicode(url)
