from datetime import date, timedelta, time
from django import template
from django.conf import settings


from events.models import SimpleEventPage
from events.models import getAllEventsByDay

register = template.Library()


# Events feed for home page
@register.inclusion_tag('events/tags/event_listing_homepage.html',
                        takes_context=True)
def event_listing_homepage(context, count=2):
    events = SimpleEventPage.objects.filter(live=True)
    events = events.filter(date__gte=date.today()).order_by('date')
    return {
        'events': events[:count],
        # required by the pageurl tag that we want to use within this template
        'request': context['request'],
    }

@register.inclusion_tag('events/tags/events_this_week.html',
                        takes_context=True)
def events_this_week(context):
    today = date.today()
    begin_ord = today.toordinal()
    if today.weekday() != 6:
        # Start week with Monday, unless today is Sunday
        begin_ord -= today.weekday()
    end_ord = begin_ord + 6
    date_from = date.fromordinal(begin_ord)
    date_to   = date.fromordinal(end_ord)
    events = getAllEventsByDay(date_from, date_to)
    #import pdb; pdb.set_trace()
    return {'events': events, 'today':  today }

# Format times e.g. on event page
@register.filter
def time_display(time):
    # Get hour and minute from time object
    hour = time.hour
    minute = time.minute

    # Convert to 12 hour format
    if hour >= 12:
        pm = True
        hour -= 12
    else:
        pm = False
    if hour == 0:
        hour = 12

    # Hour string
    hour_string = str(hour)

    # Minute string
    if minute != 0:
        minute_string = "." + str(minute)
    else:
        minute_string = ""

    # PM string
    if pm:
        pm_string = "pm"
    else:
        pm_string = "am"

    # Join and return
    return "".join([hour_string, minute_string, pm_string])



