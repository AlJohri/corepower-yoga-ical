import requests

import os
import arrow
import requests
from io import BytesIO
from icalendar import Calendar, Event
from flask import Flask, send_file

app = Flask(__name__)

SCHEDULE_API = "https://d2x1g6t1ad4mvo.cloudfront.net/locations/{site_id}/{location_id}/classes/{start_date}/{end_date}"

# https://d2x1g6t1ad4mvo.cloudfront.net/locations/31731/29/classes/2017-05-17/2017-05-29
# https://d2x1g6t1ad4mvo.cloudfront.net/locations/31731/29/classes/2017-06-12/2017-06-16
# https://d7mth1zoj92fj.cloudfront.net/data/all-locations

def date_to_ical_date(date):
    return date.format('YYYYMMDD') + 'T' + date.format('HHmmss') + 'Z'

def parse(event):

    # date times come in as local even though they end in "Z" which signifies UTC
    # tz is most likely local to location

    return {
        "id": event['mbo_id'],
        "is_canceled": event['is_canceled'],
        "start_date": arrow.get(event['start_date_time']).replace(tzinfo='US/Eastern').to('utc'),
        "end_date": arrow.get(event['end_date_time']).replace(tzinfo='US/Eastern').to('utc'),
        "name": event['name'].strip(),
        "instructor": event['staff']['name']
    }

# https://d2x1g6t1ad4mvo.cloudfront.net/locations/31731/29/classes/2017-05-23/2017-05-27

def get_events(site_id, location_id, start_date):
    url_params = {
        "site_id": site_id,
        "location_id": location_id,
        "start_date": start_date.format("YYYY-MM-DD"),
        "end_date": start_date.replace(days=+4).format("YYYY-MM-DD")
    }
    response = requests.get(SCHEDULE_API.format(**url_params))

    return response.json()

@app.route("/<location>.ics")
def schedule(location):

    if location == 'pentagon-city':
        site_id = 31731
        location_id = 29
    else:
        return f"location {location} is unknown", 500

    today = arrow.get(arrow.utcnow().date())

    dates = [
        today.replace(days=-5),
        today,
        today.replace(days=5),
        today.replace(days=10)
    ]

    events = [parse(event) for date in dates for event in get_events(site_id, location_id, date)]

    cal = Calendar()
    for event in events:
        cal_event = Event()
        cal_event['uid'] = event['id']
        cal_event['dtstart'] = date_to_ical_date(event['start_date'])
        cal_event['dtend'] = date_to_ical_date(event['end_date'])
        cal_event['summary'] = event['name']
        cal_event['description'] = event['instructor']
        cal_event['status'] = "CANCELLED" if event['is_canceled'] else "CONFIRMED"
        cal.add_component(cal_event)

    return send_file(BytesIO(cal.to_ical()),
        attachment_filename=f'{location}.ics',
        mimetype='text/calendar')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
