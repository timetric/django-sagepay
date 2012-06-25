from __future__ import absolute_import

from django.test import TestCase

from ..utils import format_money_value, encode_basket

class UtilsTest(TestCase):

    def test_format_money_value(self):
        self.assertEqual('1.00', format_money_value(1))
        self.assertEqual('6.23', format_money_value(6.2342))

    def test_encode_basket(self):
        basket = [
            {
                'description': 'Pens',
                'quantity': '5',
                'unit_value_net': '10.00',
                'unit_tax': '2.00',
                'unit_value': '12.00',
                'line_total': '60.00'
            },
            {
                'description': 'Pencils',
                'quantity': '4',
                'line_total': '50.00'
            },
        ]
        correct_output = '2:Pens:5:10.00:2.00:12.00:60.00:Pencils:4::::50.00'
        self.assertEqual(encode_basket(basket), correct_output)
        # Add colons and control characters to input
        basket[0]['description'] = 'Test: control characters\n:and colons'
        # Check we didn't add any colons or control characters to the output
        output = encode_basket(basket)
        self.assertEqual(output.count(':'), correct_output.count(':'))
        self.assertNotIn("\n", output)

