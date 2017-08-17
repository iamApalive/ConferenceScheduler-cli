"""Functions which translate the human readable, nested definition data from
the input yaml files into the flattened structures required by the conference
scheduler computation engine."""

from datetime import datetime
from datetime import timedelta

from conference_scheduler.resources import Event
from conference_scheduler.resources import Slot


def types_and_slots(venues):
    return [{
        'event_type': slot['event_type'],
        'slot': Slot(
            venue=venue,
            starts_at=(
                datetime.combine(day, datetime.min.time()) +
                timedelta(seconds=slot['starts_at'])
            ).strftime('%d-%b-%Y %H:%M'),
            duration=slot['duration'],
            session=f'{day} {session}',
            capacity=slot['capacity'])
        }
        for venue, days in venues.items()
        for day, sessions in days.items()
        for session, slots in sessions.items()
        for slot in slots]


def types_and_events(events_definition):
    """
    Parameters
    ----------
    events_definition : list
        of dicts of the form
            {'title': Event title,
            'duration': <integer in minutes>,
            'tags': <list of strings>,
            'person': <string>}
    Returns
    -------
    list
        of Event instances
    """
    return [{
        'event_type': event['event_type'],
        'event': Event(
            event['title'], event['duration'], demand=None,
            tags=event['tags'])}
    for event in events_definition]


def unavailability(events_definition, slots, unavailability_definition):
    """
    Parameters
    ----------
    events_definition : list
        of dicts of the form
            {'title': Event title,
            'duration': <integer in minutes>,
            'tags': <list of strings>,
            'person': <string>,
            'event_type': <string>}
    slots : list
        of Slot instances
    unavailablity_definition : dict
        mapping a person to a list of time periods. e.g.
            {'owen-campbell': [{
                'unavailable_from': datetime(2017, 10, 26, 0, 0),
                'unavailable_until': datetime(2017, 10, 26, 23, 59)}]
            }

    Returns
    -------
    dict
        mapping the index of an event in the events list to a list of slots
        for which it must not scheduled. The slots are represented by their
        index in the slots list.
    """
    def to_datetime(datetime_as_string):
        return datetime.strptime(datetime_as_string, '%d-%b-%Y %H:%M')

    return {
        events_definition.index(event): [
            slots.index(slot)
            for period in periods
            for slot in slots
            if period['unavailable_from'] <= to_datetime(slot.starts_at) and
            period['unavailable_until'] >= (
                to_datetime(slot.starts_at) + timedelta(0, slot.duration * 60))
        ]
        for person, periods in unavailability_definition.items()
        for event in events_definition if event['person'] == person
    }


def clashes(events_definition, clashes_definition):
    """
     Parameters
    ----------
    events_definition : list
        of dicts of the form
            {'title': Event title,
            'duration': <integer in minutes>,
            'tags': <list of strings>,
            'person': <string>,
            'event_type': <string>}
    clashes_definition : dict
        mapping a person to a list of people whose events they must not not be
        scheduled against.

    Returns
    -------
    dict
        mapping the index of an event in the events list to a list of event
        indexes against which it must not be scheduled.
    """
    # Add everyone who is missing to the clashes definition so that they cannot
    # clash with themselves
    for person in [event['person'] for event in events_definition]:
        if person not in clashes_definition:
            clashes_definition[person] = [person]

    # Add the self-clashing constraint to any existing entries where it is
    # missing
    count = 0
    for person, clashing_people in clashes_definition.items():
        if person not in clashing_people:
            clashing_people.append(person)
            count += 1

    clashes = {
        events_definition.index(event): [
            events_definition.index(t) for c in clashing_people
            for t in events_definition
            if t['person'] == c and
            events_definition.index(event) != events_definition.index(t)]
        for person, clashing_people in clashes_definition.items()
        for event in events_definition if event['person'] == person
    }
    return clashes, count


def unsuitability(types_and_slots, events_definition):
    """
    Parameters
    ----------
    venues : dict
        mapping a venue name to a dict of further parameters
    events_definition : list
        of dicts of the form
            {'title': Event title,
            'duration': <integer in minutes>,
            'tags': <list of strings>,
            'person': <string>,
            'event_type': <string>}
    Returns
    -------
    dict
        mapping the index of an event in the events list to a list of slots
        for which it must not scheduled. The slots are represented by their
        index in the slots list.
    """
    output = {}
    for event in events_definition:
        unsuitable_slots = [
            i for i, dictionary in enumerate(types_and_slots)
            if dictionary['event_type'] != event['event_type']]
        output[events_definition.index(event)] = unsuitable_slots
    return output
