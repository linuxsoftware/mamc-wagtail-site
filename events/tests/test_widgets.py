import sys
from datetime import datetime
from dateutil.rrule import YEARLY, MONTHLY, WEEKLY, DAILY
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU

from django.test import TestCase
from events.recurrence import Recurrence, RecurrenceWidget

class TestRecurrenceWidget(TestCase):
    def test_decompress_null(self):
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(None),
                         [None, None, 1, [], None, None,      #5
                          101, 200, None])

    def test_decompress_weekdays(self):
        rr = Recurrence(dtstart=datetime(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,TU,WE,TH,FR])
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(rr),
                         [datetime(2009, 1, 1), WEEKLY, 1,
                          [0,1,2,3,4], 9, None,      #5
                          101, 200, None])

    def test_decompress_everyday_in_january(self):
        rr = Recurrence(dtstart=datetime(2014, 12, 1),
                        freq=YEARLY,
                        byweekday=[MO,TU,WE,TH,FR,SA,SU],
                        bymonth=[1])
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(rr),
                         [datetime(2014, 12, 1), YEARLY, 1,
                          [], None, None,  #5
                          100, 200, 1])

    def test_null_value(self):
        widget = RecurrenceWidget()
        self.assertEqual(widget.value_from_datadict({}, {}, 'repeat'), None)

    def test_weekdays_value(self):
        widget = RecurrenceWidget()
        data = {'repeat_0': '2009-01-01',
                'repeat_1': '2',
                'repeat_2': '1',
                'repeat_3': ['0','1','2','3','4'],
                'repeat_5': '2012-01-31',
                'repeat_6': '101',
                'repeat_7': '200',
                'repeat_8': '1'}
        rr = Recurrence(dtstart=datetime(2009, 1, 1),
                        freq=WEEKLY,
                        byweekday=[MO,TU,WE,TH,FR],
                        until=datetime(2012,1,31))
        self.assertEqual(str(widget.value_from_datadict(data, {}, 'repeat')),
                         str(rr))

    def test_everyday_in_january_value(self):
        widget = RecurrenceWidget()
        data = {'repeat_0': '2014-12-1',
                'repeat_1': '0',
                'repeat_2': '1',
                'repeat_5': '',
                'repeat_6': '100',
                'repeat_7': '200',
                'repeat_8': '1'}
        rr = Recurrence(dtstart=datetime(2014, 12, 1),
                        freq=YEARLY,
                        byweekday=[MO,TU,WE,TH,FR,SA,SU],
                        bymonth=[1])
        self.assertEqual(str(widget.value_from_datadict(data, {}, 'repeat')),
                         str(rr))
