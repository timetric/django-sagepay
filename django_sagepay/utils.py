"""

"""
import re

from urllib import urlencode

# SagePay fail to specify what characters are acceptable in the basket
# description field. We can surmise that colons are invalid as they are used
# as field delimiters and no means is provided for escaping them. It also seems
# wise to remove any control characters.
INVALID_CHARS = re.compile("( [\x00-\x1f\x7f-\xff] | : )",
    re.UNICODE | re.VERBOSE)

FIELD_LENGTHS = (
    ('Description', 100),
    ('CustomerEMail', 255),
)

BASKET_FIELD_LENGTH = 7500

ADDRESS_FIELD_LENGTHS = (
    ('Surname', 20),
    ('Firstnames ', 20),
    ('Address1 ', 20),
    ('Address2 ', 20),
    ('City ', 40),
    ('Postcode ', 10),
    ('State ', 2),
    ('Country ', 2),
    ('Phone ', 20),
)

# Avoid having to specify address fields twice
for prefix in ('Billing', 'Delivery'):
    FIELD_LENGTHS = FIELD_LENGTHS + tuple(
        (prefix + field, length) for (field, length) in ADDRESS_FIELD_LENGTHS)

def truncate_overlong_fields(data):
    # SagePay has quite low length limits on fields, however for many of these
    # fields, particularly the description and basket contents fields where
    # it's quite easy to go over the limit, we're better off just truncating
    # the fields and letting the order go through: The consquences of a user
    # having a truncated order description on the payment page are far less
    # serious than them not being able to order at all. A similar argument
    # applies to address fields: truncating the address might mean that the
    # card verification fails, but at least it has a chance of succeeding.

    # Copy the data so we don't have side-effects
    data = data.copy()
    # Special treatment for the specially formatted Basket field as we can't
    # simply truncate it: we have to check its encoded length and if it's too
    # long we just throw it away rather than try to do anything clever. It's
    # not a required fields and users should already be clear what they're
    # buying at this stage.
    basket = data.pop('Basket', None)
    if basket and basket == utf8_truncate(basket, BASKET_FIELD_LENGTH):
        data['Basket'] = basket
    # Truncate fields
    for field, length in FIELD_LENGTHS:
        try:
            data[field] = utf8_truncate(data[field], length)
        except KeyError:
            pass
    return data

def utf8_truncate(s, max_length):
    """
    Truncate a unicode string so that its UTF-8 representation will not be longer
    than `max_length` bytes

    Hat tip: http://stackoverflow.com/questions/1809531/
    """
    encoded = s.encode('utf-8')
    # The 'ignore' flag ensures that if a multibyte char gets chopped halfway it
    # will just be dropped
    return encoded[:max_length].decode('utf-8', 'ignore')

def format_money_value(num):
    return u'{0:.2f}'.format(num)

def encode_basket(basket):
    fields = []
    fields.append(unicode(len(basket)))
    for item in basket:
        fields.extend([
            INVALID_CHARS.sub(' ', unicode(item.get(f, ''))) for f in [
                'description', 'quantity', 'unit_value_net', 'unit_tax',
                'unit_value', 'line_total'
        ]])
    output = u':'.join(fields)
    return output

def encode_transaction_request(data):
    # We're going to mutate this dict so make a copy
    data = data.copy()
    data['Amount'] = format_money_value(data['Amount'])
    basket = data.pop('Basket', None)
    if basket:
        data['Basket'] = encode_basket(basket)
    for key in data:
        if not isinstance(data[key], basestring):
            data[key] = unicode(data[key])
        data[key] = data[key].encode('utf8')
    return urlencode(data)

def decode_transaction_response(body):
    return dict(line.split('=', 1) for line in body.strip().split("\r\n"))

def encode_notification_acknowledgement(data):
    response = []
    for key in ('Status', 'RedirectURL', 'StatusDetail'):
        response.append('{key}={value}'.format(
            key=key, value=data.get(key, '').encode('utf8')))
    return "\r\n".join(response)
