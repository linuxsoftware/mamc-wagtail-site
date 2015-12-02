# ------------------------------------------------------------------------------
# Recurrence
# ------------------------------------------------------------------------------
# Somewhat based upon RFC5545 RRules, implemented using dateutil.rrule
# Does not support timezones ... and probably never will
import sys
from operator import attrgetter
import calendar
import json
import datetime as dt
from django.db.models import Field
from django.forms.fields import CharField
from django.forms.widgets import MultiWidget, NumberInput, Select, \
        CheckboxSelectMultiple
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from wagtail.utils.widgets import WidgetWithScript
from wagtail.wagtailadmin.widgets import AdminDateInput
from wagtail.wagtailadmin.edit_handlers import BaseFieldPanel
from dateutil.rrule import rrule, rrulestr, rrulebase
from dateutil.rrule import WEEKLY, MONTHLY, YEARLY
from dateutil.rrule import weekday as rrweekday
from dateutil.parser import parse as dt_parse

# ------------------------------------------------------------------------------
# Use Sunday as the first day of the week following Jewish tradition
# This differs from ISO 8601
#     https://en.wikipedia.org/wiki/Week#Week_numbering
#     http://www.cjvlang.com/Dow/SunMon.html
# Keep this the same as the JQueryDatePicker to avoid confusion
# see  http://xdsoft.net/jqplugins/datetimepicker
# TODO: make firstweekday a dashboard admin option?
calendar.setfirstweekday(6)

# ------------------------------------------------------------------------------
class Weekday(rrweekday):
    def __str__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "{:+d}{}".format(self.n, s)

# ------------------------------------------------------------------------------
class Recurrence(rrulebase):
    def __init__(self, *args, **kwargs):
        super().__init__()
        arg0 = args[0] if len(args) else None
        if isinstance(arg0, str):
            self.rule = rrulestr(arg0)
            if not isinstance(self.rule, rrule):
                raise ValueError("Only support simple RRules for now")
        elif isinstance(arg0, Recurrence):
            self.rule = arg0.rule
        elif isinstance(arg0, rrule):
            self.rule = arg0
        else:
            self.rule = rrule(*args, **kwargs)

    # expose all
    dtstart     = property(attrgetter("rule._dtstart"))
    freq        = property(attrgetter("rule._freq"))
    interval    = property(attrgetter("rule._interval"))
    wkst        = property(attrgetter("rule._wkst"))
    until       = property(attrgetter("rule._until"))
    count       = property(attrgetter("rule._count"))
    bymonth     = property(attrgetter("rule._bymonth"))
    byweekno    = property(attrgetter("rule._byweekno"))
    byyearday   = property(attrgetter("rule._byyearday"))
    byeaster    = property(attrgetter("rule._byeaster"))
    bysetpos    = property(attrgetter("rule._bysetpos"))
    byhour      = property(attrgetter("rule._byhour"))
    byminute    = property(attrgetter("rule._byminute"))
    bysecond    = property(attrgetter("rule._bysecond"))

    @property
    def byweekday(self):
        retval = []
        if self.rule._byweekday:
            retval += [Weekday(day) for day in self.rule._byweekday]
        if self.rule._bynweekday:
            retval += [Weekday(day, n) for day, n in self.rule._bynweekday]
        return retval

    @property
    def bymonthday(self):
        retval = []
        if self.rule._bymonthday:
            retval += self.rule._bymonthday
        if self.rule._bynmonthday:
            retval += self.rule._bynmonthday
        return retval

    def _iter(self):
        return self.rule._iter()

    def getCount(self):
        return self.rule.count()

    def __str__(self):
        freqChoices = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY")
        parts = ["FREQ={}".format(freqChoices[self.freq])]
        if self.interval and self.interval != 1:
            parts.append("INTERVAL={}".format(self.interval))
        if self.wkst:
            parts.append("WKST={}".format(Weekday(self.wkst)))
        if self.count:
            parts.append("COUNT={}".format(self.count))
        if self.until:
            parts.append("UNTIL={:%Y%m%d}".format(self.until))

        for name, value in [('BYSETPOS',   self.bysetpos),
                            ('BYDAY',      self.byweekday),
                            ('BYMONTH',    self.bymonth),
                            ('BYMONTHDAY', self.bymonthday),
                            ('BYYEARDAY',  self.byyearday),
                            ('BYWEEKNO',   self.byweekno)]:
            if value:
                parts.append("{}={}".format(name,
                                            ",".join(str(v) for v in value)))

        for name, value in [('BYHOUR',     self.byhour),
                            ('BYMINUTE',   self.byminute),
                            ('BYSECOND',   self.bysecond)]:
            if len(value) > 1 or next(iter(value), 0) != 0:
                parts.append("{}={}".format(name,
                                            ",".join(str(v) for v in value)))
        rrule = "RRULE:{}".format(";".join(parts))

        dtstart = ""
        if self.dtstart:
            dtstart = "DTSTART:{:%Y%m%d}\n".format(self.dtstart)

        retval = dtstart + rrule
        return retval

# ------------------------------------------------------------------------------
class RecurrenceField(Field):
    description = "The rule for recurring events"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, Recurrence):
            return value
        try:
            return Recurrence(value)
        except (TypeError, ValueError, UnboundLocalError) as err:
            #raise ValidationError("Invalid input for recurrence {}".format(err))
            return None

    def get_prep_value(self, rule):
        return str(rule)

    def get_prep_lookup(self, lookup_type, value):
        raise TypeError('Lookup type %r not supported.' % lookup_type)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'form_class': RecurrenceFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_internal_type(self):
        return "CharField"

# ------------------------------------------------------------------------------
(_EveryDay, _SameDay, _DayOfMonth) = (100, 101, 200)

class RecurrenceWidget(WidgetWithScript, MultiWidget):
    def __init__(self, attrs=None):
        freqChoices = [(3, "Daily"),
                       (2, "Weekly"),
                       (1, "Monthly"),
                       (0, "Yearly")]
        ordChoices  = [(1, "The First"),
                       (2, "The Second"),
                       (3, "The Third"),
                       (4, "The Fourth"),
                       (5, "The Fifth"),
                       (-1, "The Last"),
                       (_EveryDay, "Every"),
                       (_SameDay, "The Same")]
        dayChoices1  = enumerate(calendar.day_abbr)
        dayChoices2  = list(enumerate(calendar.day_name)) +\
                       [(_DayOfMonth, "Day of the month")]
        monthChoices = enumerate(calendar.month_name[1:], 1)

        numAttrs = {'min': 1, 'max': 366}
        if attrs:
            numAttrs.update(attrs)
        widgets = [AdminDateInput(attrs=attrs),
                   Select(attrs=attrs, choices=freqChoices), #1
                   NumberInput(attrs=numAttrs),
                   CheckboxSelectMultiple(attrs=attrs, choices=dayChoices1),
                   NumberInput(attrs=numAttrs),
                   AdminDateInput(attrs=attrs),              #5
                   Select(attrs=attrs, choices=ordChoices),
                   Select(attrs=attrs, choices=dayChoices2),
                   Select(attrs=attrs, choices=monthChoices) ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        wdayChoices = []
        ordChoice   = _SameDay
        dayChoice   = _DayOfMonth
        monChoice   = None
        if isinstance(value, Recurrence):
            if value.freq == WEEKLY:
                if value.byweekday:
                    wdayChoices = [day.weekday for day in value.byweekday]
            elif value.freq in (MONTHLY, YEARLY):
                if value.byweekday:
                    day = value.byweekday[0]
                    dayChoice = day.weekday
                    ordChoice = day.n or 0
                elif value.bymonthday:
                    ordChoice = value.bymonthday[0]
                    if value.dtstart.day == ordChoice:
                        ordChoice = _SameDay
                    dayChoice = _DayOfMonth
                if value.bymonth:
                    monChoice = value.bymonth[0]
                else:
                    value.dtstart.month
            return [value.dtstart,
                    value.freq,      #1
                    value.interval,
                    wdayChoices,
                    value.count,
                    value.until,     #5
                    ordChoice,
                    dayChoice,
                    monChoice ]
        else:
            return [None,
                    None,      #1
                    1,
                    wdayChoices,
                    None,
                    None,      #5
                    ordChoice,
                    dayChoice,
                    monChoice ]

    def render_html(self, name, value, attrs=None):
        if isinstance(value, list):
            values = value
        else:
            values = self.decompress(value)

        rendered_widgets = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = values[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            rendered_widgets.append(widget.render(name + '_%s' % i, widget_value, final_attrs))

        return render_to_string("events/widgets/recurrence_widget.html", {
            'widget':           self,
            'attrs':            attrs,
            'value':            value,
            'widgets':          self.widgets,
            'rendered_widgets': rendered_widgets,
        })

    def render_js_init(self, id_, name, value):
        return 'initRecurrenceWidget({0});'.format(json.dumps(id_))

    def value_from_datadict(self, data, files, name):
        values = [widget.value_from_datadict(data, files, "{}_{}".format(name, i))
                  for i, widget in enumerate(self.widgets)]
        try:
            def toIntOrNone(value):
                return int(value) if value else None
            dtstart     = dt_parse(values[0]) if values[0] else None
            frequency   = toIntOrNone(values[1])
            interval    = toIntOrNone(values[2])
            if interval is not None and interval <= 0:
                interval = None
            #count     = toIntOrNone(values[4]) or None
            dtuntil     = dt_parse(values[5]) if values[5] else None
            ordChoice   = toIntOrNone(values[6])
            dayChoice   = toIntOrNone(values[7])
            wdayChoices = None
            mdayChoices = None
            monChoices  = None
            if frequency == WEEKLY:
                if values[3]:
                    wdayChoices = [int(day) for day in values[3]]
            elif frequency in (MONTHLY, YEARLY):
                if dayChoice == _DayOfMonth:    # day of the month
                    if ordChoice == _EveryDay:      # every day, == daily
                        wdayChoices = range(7)
                    elif ordChoice == _SameDay:     # the same day of the month
                        mdayChoices = None
                    else:
                        mdayChoices = [ordChoice]
                else:                         # a day of the week
                    if ordChoice == _EveryDay:      # every of this weekday
                        wdayChoices = [Weekday(dayChoice)]
                    elif ordChoice == _SameDay:     # the same weekday of the month
                        wdayNum = (dtstart.day - 1) // 7 + 1
                        wdayChoices = [Weekday(dayChoice, wdayNum)]
                    else:
                        wdayChoices = [Weekday(dayChoice, ordChoice)]
                if frequency == YEARLY:
                    monChoices = [int(values[8])]

            retval = Recurrence(dtstart    = dtstart,
                                freq       = frequency,
                                interval   = interval,
                                byweekday  = wdayChoices,
                                #count      = count,
                                until      = dtuntil,
                                bymonthday = mdayChoices,
                                bymonth    = monChoices)
        except (TypeError, ValueError):
            retval = None
        return retval

# ------------------------------------------------------------------------------
class RecurrenceFormField(CharField):
    widget = RecurrenceWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return value

    def validate(self, value):
        return super().validate(value)

# ------------------------------------------------------------------------------
class BaseRecurrencePanel(BaseFieldPanel):
    # TODO customise this?
    object_template = "events/edit_handlers/recurrence_object.html"

    @classmethod
    def html_declarations(cls):
        html = ['<link rel="stylesheet" href="/static/events/css/recurrence_admin.css">',
                '<script src="/static/events/js/recurrence_admin.js"></script>',
               ]
        return mark_safe('\n'.join(html))

    def render_as_object(self):
        return mark_safe(render_to_string(self.object_template, {
            'self': self,
            self.TEMPLATE_VAR: self,
            'field': self.bound_field,
        }))

    @classmethod
    def required_fields(self):
        return [self.field_name]

# ------------------------------------------------------------------------------
class RecurrencePanel(object):
    def __init__(self, field_name, classname=""):
        self.field_name = field_name
        self.classname = classname

    def bind_to_model(self, model):
        members = {
            'model':      model,
            'field_name': self.field_name,
            'classname':  self.classname,
            'widget':     RecurrenceWidget,
        }
        return type(str('_RecurrencePanel'), (BaseRecurrencePanel,), members)

# ------------------------------------------------------------------------------
class ExceptionDateInput(AdminDateInput):
    def __init__(self, attrs=None, format='%Y-%m-%d'):
        super().__init__(attrs=attrs, format=format)
        self.overrides_repeat = None

    def render_js_init(self, id_, name, value):
        return "initExceptionDateChooser({0}, {1});"\
               .format(json.dumps(id_), json.dumps(self.valid_dates()))

    def valid_dates(self):
        valid_dates = -1
        if self.overrides_repeat:
            now = dt.datetime.now()
            future = (now + dt.timedelta(days=157)).replace(day=1)
            valid_dates = ["{:%Y%m%d}".format(occurence) for occurence in
                           self.overrides_repeat.between(now, future)]
        return valid_dates

# TODO Should probably also do validation on the returned date?
# that would require ExceptionDateField and ExceptionDateFormField :(
# or else wait for custom form for page validation?
# https://github.com/torchbox/wagtail/pull/1867

# ------------------------------------------------------------------------------
class BaseExceptionDatePanel(BaseFieldPanel):
    def __init__(self, instance=None, form=None):
        super().__init__(instance=instance, form=form)
        widget = self.bound_field.field.widget
        widget.overrides_repeat = self.instance.overrides_repeat

    @classmethod
    def html_declarations(cls):
        html = ['<link rel="stylesheet" href="/static/events/css/recurrence_admin.css">',
                '<script src="/static/events/js/recurrence_admin.js"></script>' ]
        return mark_safe('\n'.join(html))

# ------------------------------------------------------------------------------
class ExceptionDatePanel(object):
    def __init__(self, field_name, classname=""):
        self.field_name = field_name
        self.classname = classname

    def bind_to_model(self, model):
        members = {
            'model':      model,
            'field_name': self.field_name,
            'classname':  self.classname,
            'widget':     ExceptionDateInput,
        }
        return type(str('_ExceptionDatePanel'), (BaseExceptionDatePanel,), members)

# ------------------------------------------------------------------------------
