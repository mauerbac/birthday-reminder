# Sample app demonstrating Clever's Instant Login
# Written in Python 2.7 with the Flask Framework
# Author: Matt Auerbach

from flask import Flask, request, render_template, session, redirect, url_for
import os
import urllib
import base64
import requests
import json
import datetime

# Fill in with your CLIENT_ID, CLIENT_SECRET, DISTRICT_TOKEN & REDIRECT_URI
CLIENT_ID = ''
CLIENT_SECRET = ''
DISTRICT_TOKEN = '' # Note: This app is only compatible with this district

CLEVER_API_BASE = 'https://api.clever.com'
CLEVER_OAUTH_URL = 'https://clever.com/oauth/tokens'
API_VERSION = '/v1.1'

REDIRECT_URI = '' # http://example.com/oauth

application = Flask(__name__)
application.secret_key = os.urandom(24)


@application.route('/')
def index():
    encoded_string = urllib.urlencode({
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'scope': 'read:user_id read:sis'
    })

    error = ''

    if 'error' in request.args:
        error = request.args.get('error')

    instant_login_url = 'https://clever.com/oauth/authorize?' + encoded_string

    return render_template('index.html', url=instant_login_url, error=error)


@application.route('/oauth')
def oauth():
    # Retrieve code from Clever
    code = request.args.get('code')

    payload = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }

    headers = {
        'Authorization': 'Basic {0}'.format(
            base64.b64encode(CLIENT_ID + ':' + CLIENT_SECRET)),
        'Content-Type': 'application/json',
    }

    # Request a user's access token using the short-lived code
    response = requests.post(CLEVER_OAUTH_URL, data=json.dumps(payload), headers=headers)

    if response.status_code >= 400:
        return redirect(url_for('index', error='There was an error with Instant Login.'))
    else:
        response = response.json()

    # Initate a session
    session['login'] = True

    # Save token in session object
    session['token'] = response['access_token']

    return redirect(url_for('process_birthdays'))


@application.route('/app')
def process_birthdays():
    # Only allow logged in users to view this page
    if not session.get('login'):
        return redirect(url_for('index', error='Please sign-in first.'))

    # Retrieve the user's token from session data
    token = session['token']

    # Use access token to retrieve /me data
    user_data = get_basic_info(token)

    # Store teacher or student id
    entity_id = user_data['id']

    # Store user's name in session
    session['name'] = user_data['name']['first'] + ' ' + user_data['name']['last']

    # This application is intended for Teachers. If Student, display their birthday
    if user_data['type'] == 'student':
        birthday_raw = user_data['dob']
        birthday_object = datetime.datetime.strptime(birthday_raw, '%Y-%m-%dT%X.%fZ')
        birthday_formatted = str(birthday_object.month) + '/' + str(birthday_object.day)

        return render_template('student.html', birthday=birthday_formatted)

    elif user_data['type'] == 'teacher':

        # Call '/teachers/{teacher_id}/students' endpoint
        students_data = requests.get(
            CLEVER_API_BASE + API_VERSION + '/teachers/{0}/students?limit=200'.format(entity_id),
            headers={'Authorization': 'Bearer {0}'.format(DISTRICT_TOKEN)})

        if students_data.status_code >= 400:
            return redirect(url_for('index', error='There was an error retrieving student data.'))
        else:
            students_data = students_data.json()

        # Error check : Ensure the teacher actually has students
        if students_data['data'] == []:
            return redirect(url_for('index', error="You don't have any students."))

        # Parse data returned by Clever and create a dictionary of student birthdays
        students = parse_birthdays(students_data)

        # Sort students dictionary by month, then by day
        sorted_students = sorted(
            students.keys(),
            key=lambda x: datetime.datetime.strptime(x, '%m/%d'))

        # Get today's date
        today_date = datetime.datetime.today().strftime('%m/%d')
        # For testing: uncomment to change today's date
        # today_date ='12/31'

        # Find students with birthdays today
        current_birthdays = find_student_birthday(students, today_date)

        # Find students who have the next birthday
        next_birthday_date = sorted_students[0]

        # Datetime object for today's date
        today_date_obj = datetime.datetime.strptime(today_date, '%m/%d')

        # Search for next birthdate
        for student_dob in sorted_students:
            if datetime.datetime.strptime(student_dob, '%m/%d') > today_date_obj:
                next_birthday_date = student_dob
                break

        # Given the birthday find students with birthday
        next_birthday = find_student_birthday(students, next_birthday_date) + ' on ' + next_birthday_date

        return render_template(
            'app.html',
            ordered_students=sorted_students,
            students_data=students,
            current_birthdays=current_birthdays,
            next_birthday=next_birthday)
    else:
        return redirect(url_for('index', error='Only teachers and students can login.'))


@application.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Processes student data from Clever
def parse_birthdays(student_data):
    # Create dictionary of birthdays and students who share that birthday

    students = {}

    for student in student_data['data']:
        student = student['data']
        student_id = student['id']
        birthday = student['dob']
        full_name = student['name']['first'] + ' ' + student['name']['last']

        # dob formatting: i.e '6/18/1998' -> 6/18
        birthday = str(birthday).split('/')
        birthday = birthday[0] + '/' + birthday[1]

        if birthday in students:
            students[birthday].append((student_id, full_name))
        else:
            students[birthday] = [(student_id, full_name)]

    return students

# Given a birthdate return the students who share that birthday
def find_student_birthday(data, birthdate):
    students = []

    if birthdate in data:
        for student in data[birthdate]:
            students.append(student[1])
    students = ', '.join(students)

    return students

# Wrapper for /me endpoint.
def get_basic_info(token):
    bearer_headers = {
        'Authorization': 'Bearer {token}'.format(token=token)
    }
    result = requests.get(CLEVER_API_BASE + '/me', headers=bearer_headers)

    if result.status_code >= 400:
        return redirect(url_for('index', error='There was an error retrieving your personal data.'))
    else:
        result = result.json()
    return result['data']

if __name__ == '__main__':
    # Toggle to debug
    application.debug = False
    application.run()
