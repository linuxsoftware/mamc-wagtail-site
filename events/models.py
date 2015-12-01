# ------------------------------------------------------------------------------
# Events
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from contextlib import suppress
from collections import namedtuple
from itertools import groupby
from django.db import models
from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailadmin.edit_handlers import FieldPanel, MultiFieldPanel, \
    InlinePanel, PageChooserPanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailsearch import index
from wagtail.wagtailadmin.signals import init_new_page
from wagtail.wagtailcore.url_routing import RouteResult
from django.shortcuts import render
from django.http.response import Http404
from django.dispatch import receiver
from modelcluster.fields import ParentalKey
import holidays
from events.recurrence import RecurrenceField, RecurrencePanel
from events.recurrence import ExceptionDatePanel
from website.models import RelatedLink


# ------------------------------------------------------------------------------
# Event Pages
# ------------------------------------------------------------------------------
class EventBase(models.Model):
    class Meta:
        abstract = True
    time_from = models.TimeField("Start time", null=True, blank=True)
    time_to = models.TimeField("End time", null=True, blank=True)
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    group_page  = models.ForeignKey('wagtailcore.Page',
                                    null=True,
                                    blank=True,
                                    on_delete=models.SET_NULL,
                                    related_name='+')
    location = models.CharField(max_length=255, blank=True)
    details  = RichTextField(blank=True)

    search_fields = Page.search_fields + (
        index.SearchField('location'),
        index.SearchField('details'),
    )

    @property
    def event_index(self):
        # Find closest ancestor which is an event index
        return self.get_ancestors().type(EventIndexPage).last()

class EventsOnDay(namedtuple("EODBase", "date days_events continuing_events")):
    aukHols = holidays.NZ(prov="Auckland")
    @property
    def weekday(self):
        return calendar.day_abbr[self.date.weekday()].lower()
    @property
    def holiday(self):
        return self.aukHols.get(self.date)

def getAllEventsByDay(date_from, date_to):
    allEvents       = []
    simpleEvents    = SimpleEventPage.getEventsByDay(date_from, date_to)
    multidayEvents  = MultidayEventPage.getEventsByDay(date_from, date_to)
    recurringEvents = RecurringEventPage.getEventsByDay(date_from, date_to)
    day = date_from
    for srcs in zip(simpleEvents, multidayEvents, recurringEvents):
        days_events       = []
        continuing_events = []
        for src in srcs:
            days_events.extend(src.days_events)
            continuing_events.extend(src.continuing_events)
        days_events.sort(key=lambda page:page.time_from or dt.time.max)
        allEvents.append(EventsOnDay(day, days_events, continuing_events))
        day += dt.timedelta(days=1)
    return allEvents

def getAllEventsByWeek(year, month):
    weeks = []
    firstDay = dt.date(year, month, 1)
    lastDay  = dt.date(year, month, calendar.monthrange(year, month)[1])
    firstWday = (firstDay.weekday() + 1) % 7
    def calcWeekNum(evod):
        return (evod.date.day + firstWday - 1) // 7
    events = getAllEventsByDay(firstDay, lastDay)
    for weekNum, group in groupby(events, calcWeekNum):
        week = list(group)
        if len(week) < 7:
            padding = [None] * (7 - len(week))
            if weekNum == 0:
                week = padding + week
            else:
                week += padding
        weeks.append(week)
    return weeks

# ------------------------------------------------------------------------------
class SimpleEventPage(Page, EventBase):
    parent_page_types = ["events.EventIndexPage"]
    subpage_types = []
    class Meta:
        verbose_name = "Event Page"
    date    = models.DateField("Date", default=dt.date.today)
    speaker = models.CharField(max_length=255, blank=True)

    content_panels = Page.content_panels + [
        ImageChooserPanel('image'),
        FieldPanel('date'),
        FieldPanel('time_from'),
        FieldPanel('time_to'),
        FieldPanel('details', classname="full"),
        FieldPanel('speaker'),
        FieldPanel('location'),
        PageChooserPanel('group_page'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        ord_from =  date_from.toordinal()
        ord_to   =  date_to.toordinal()
        events = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                  for ord in range(ord_from, ord_to+1)]
        pages = SimpleEventPage.objects.live()                          \
                               .filter(date__range=(date_from, date_to))
        for page in pages:
            dayNum = page.date.toordinal() - ord_from
            events[dayNum].days_events.append(page)
        return events

    def occursOn(self, when):
        return self.date == when

# ------------------------------------------------------------------------------
class MultidayEventPage(Page, EventBase):
    parent_page_types = ["events.EventIndexPage"]
    subpage_types = []
    date_from = models.DateField("Start date", default=dt.date.today)
    date_to = models.DateField("End date", default=dt.date.today)

    content_panels = Page.content_panels + [
        ImageChooserPanel('image'),
        FieldPanel('date_from'),
        FieldPanel('time_from'),
        FieldPanel('date_to'),
        FieldPanel('time_to'),
        FieldPanel('details', classname="full"),
        FieldPanel('location'),
        PageChooserPanel('group_page'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        events = []
        ord_from =  date_from.toordinal()
        ord_to   =  date_to.toordinal()
        days = [dt.date.fromordinal(ord)
                for ord in range(ord_from, ord_to+1)]
        pages = MultidayEventPage.objects.live()                       \
                                 .filter(date_to__gte   = date_from)   \
                                 .filter(date_from__lte = date_to)
        for day in days:
            days_events = []
            continuing_events = []
            for page in pages:
                if page.date_from == day:
                    days_events.append(page)
                elif page.date_from < day <= page.date_to:
                    continuing_events.append(page)
            events.append(EventsOnDay(day, days_events, continuing_events))
        return events

    def occursOn(self, when):
        return self.date_from <= when <= self.date_to

# ------------------------------------------------------------------------------
class RecurringEventPage(Page, EventBase):
    parent_page_types = ["events.EventIndexPage"]
    subpage_types = ['events.RecurringEventExceptionPage']
    repeat  = RecurrenceField()

    content_panels = Page.content_panels + [
        ImageChooserPanel('image'),
        RecurrencePanel('repeat'),
        FieldPanel('time_from'),
        FieldPanel('time_to'),
        FieldPanel('details', classname="full"),
        FieldPanel('location'),
        PageChooserPanel('group_page'),
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        ord_from =  date_from.toordinal()
        ord_to   =  date_to.toordinal()
        dt_from  = dt.datetime.combine(date_from, dt.time.min)
        dt_to    = dt.datetime.combine(date_to,   dt.time.min)
        events = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                  for ord in range(ord_from, ord_to+1)]
        pages = RecurringEventPage.objects.live()
        for page in pages:
            exceptions = {exception.date: exception
                          for exception in RecurringEventExceptionPage.objects\
                                   .live().child_of(page)                     \
                                   .filter(date__range=(date_from, date_to)) }
            for occurence in page.repeat.between(dt_from, dt_to, True):
                dayNum = occurence.toordinal() - ord_from
                exception = exceptions.get(occurence.date())
                if exception:
                    if not exception.hide:
                        events[dayNum].days_events.append(exception)
                else:
                    events[dayNum].days_events.append(page)
        return events

    def occursOn(self, when):
        return when in self.repeat

# ------------------------------------------------------------------------------
class RecurringEventExceptionPage(Page, EventBase):
    parent_page_types = ["events.RecurringEventPage"]
    subpage_types = []
    class Meta:
        verbose_name = "Event Exception Page"

    # overrides is also the parent, but parent is not set until the
    # child is saved and added.  (NB: is published version of parent)
    overrides = models.ForeignKey('events.RecurringEventPage',
                                  null=True, blank=True,
                                  on_delete=models.SET_NULL,
                                  related_name='+')
    overrides.help_text = "This is the event (published) that we are overriding."
    date    = models.DateField("Exception Date", default=dt.date.today)
    date.help_text = "The exception applies for this date"
    hide    = models.BooleanField("Hide for this date", default=False)
    hide.help_text = "Hide the event for this date"

    @property
    def overrides_repeat(self):
        return getattr(self.overrides, 'repeat', None)

    content_panels = Page.content_panels + [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('date'),
        FieldPanel('hide'),
        ImageChooserPanel('image'),
        FieldPanel('time_from'),
        FieldPanel('time_to'),
        FieldPanel('details'),
        FieldPanel('location'),
        PageChooserPanel('group_page'),
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]

# ------------------------------------------------------------------------------
# Recieve Signals
# ------------------------------------------------------------------------------
@receiver(init_new_page)
def identifyExpectantParent(sender, **kwargs):
    page = kwargs.get('page')
    parent = kwargs.get('parent')
    if (isinstance(page, RecurringEventExceptionPage) and
        isinstance(parent, RecurringEventPage) and
        not page.overrides):
        page.overrides = parent

# ------------------------------------------------------------------------------
# Event index page
# ------------------------------------------------------------------------------
class EventIndexPageRelatedLink(Orderable, RelatedLink):
    page = ParentalKey('events.EventIndexPage', related_name='related_links')


class EventIndexPage(Page):
    subpage_types = ['events.SimpleEventPage',
                     'events.MultidayEventPage',
                     'events.RecurringEventPage',
                     'events.CalendarPage']

    intro = RichTextField(blank=True)

    search_fields = Page.search_fields + (
        index.SearchField('intro'),
    )

    @property
    def recurringEvents(self):
        events = RecurringEventPage.objects.live()
        return events

    @property
    def old_events(self):
        # Get list of live event pages that are descendants of this page
        events = Page.objects.live().descendant_of(self)

        # Filter events list to get ones that are either
        # running now or start in the future
        #events = events.filter(date_from__gte=dt.date.today())

        # Order by date
        #events = events.order_by('date_from')

        return events


    content_panels = Page.content_panels + [
        FieldPanel('intro', classname="full"),
        InlinePanel('related_links', label="Related links"),
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]


# ------------------------------------------------------------------------------
# Calendar
# ------------------------------------------------------------------------------
class CalendarPage(Page):
    subpage_types = []
    intro = RichTextField(blank=True)
    search_fields = Page.search_fields

    @property
    def events(self):
        return []

    def route(self, request, components):
        # see http://docs.wagtail.io/en/latest/reference/pages/model_recipes.html
        if components:
            # tell Wagtail to call self.serve() with an additional kwargs
            return RouteResult(self, kwargs=self._parsePath(components))
        else:
            if self.live:
                # tell Wagtail to call self.serve() with no further args
                return RouteResult(self)
            else:
                raise Http404

    def _parsePath(self, components):
        kwargs = {}
        with suppress(ValueError, TypeError):
            value = int(components[0])
            if 1900 <= value <= 2115:
                kwargs['year'] = value
        if len(components) > 1:
            try:
                kwargs['month'] = calendar.month_abbr.index(components[1])
            except (ValueError, TypeError):
                with suppress(ValueError, TypeError):
                    value = int(components[1])
                    if 1 <= value <= 12:
                        kwargs['month'] = value
        if len(components) > 2:
            with suppress(ValueError, TypeError):
                value = int(components[2])
                if 1 <= value <= 31:
                    kwargs['day'] = value
        return kwargs

    def serve(self, request, year=None, month=None, day=None):
        today = dt.date.today()
        yesterday = today - dt.timedelta(1)
        lastWeek  = today - dt.timedelta(7)
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        eventsByWeek = getAllEventsByWeek(year, month)
        prevMonth = month - 1
        prevMonthYear = year
        if prevMonth == 0:
            prevMonth = 12
            prevMonthYear = year - 1
        nextMonth = month + 1
        nextMonthYear = year
        if nextMonth == 13:
            nextMonth = 1
            nextMonthYear = year + 1
        return render(request, self.template,
                      {'self':         self,
                       'year':         year,
                       'month':        month,
                       'today':        today,
                       'yesterday':    yesterday,
                       'lastweek':     lastWeek,
                       'prevMonthUrl': "{}{}/{}/".format(self.url, prevMonthYear, prevMonth),
                       'nextMonthUrl': "{}{}/{}/".format(self.url, nextMonthYear, nextMonth),
                       'prevYearUrl':  "{}{}/{}/".format(self.url, year - 1, month),
                       'nextYearUrl':  "{}{}/{}/".format(self.url, year + 1, month),
                       'monthName':    calendar.month_name[month],
                       'events':       eventsByWeek})

    content_panels = Page.content_panels + [
        FieldPanel('intro', classname="full"),
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]


