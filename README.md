# Leveraging Clever Instant Login 

[Live Site](http://birthday-reminder-dev.elasticbeanstalk.com/)

## Clever's Platform

Clever’s Single Sign-on (SSO) solution, Instant Login, alleviates many pain points with password management for students and teachers. Using Instant Login, users can create one identity within Clever and access all of their applications in the classroom. School districts share data from their Student Information Systems (SIS) with Clever. 

By integrating with Clever, developers can securely and easily access district data via an API. This allows developers to spend more time building their own product, rather than worrying about SIS integrations. 

In this post, I’ll discuss the different components of Instant Login and provide a walk-through of a working example, Birthday Reminder. By the end of this demo, developers should have the tools to start implementing SSO in web application and access district data with Clever.

### How Does Instant Login Work?

Applications use Instant Login to verify a user’s identity, authenticate users, and make API calls on a user’s behalf with their access token. Here’s a typical flow that is initiated when a user requests to Log in with Clever:

![Diagram](https://s3-us-west-2.amazonaws.com/mauerbac-web-images/sso-pilot-oauth2-flow.png)

[Additional Info on Instant Login](https://dev.clever.com/instant-login/bearer-tokens)

### Entity Types 

Before getting started, it’s important to understand Clever’s entities -- let’s start with developer and district. Application developer accounts are used to create and edit applications settings, as well as view the district data from approved districts. District admins can control what applications teachers and students have available, but most importantly, they control what data is shared within these applications. District admins can also control what district data Clever has access to. It’s important to note that district admins are viewed as a central authority (not students and teachers). This means only district admins can control what apps are available and the scope of their data access. 

Students and teachers are also entities in the Clever ecosystem and should be thought of as end users -- they will have their own credentials and will be consumers of your application. 

### Tokens and Scope

Before diving into the code, let’s review the different types of tokens and application scopes. Scope controls what data your application has access to and therefore dictates what data the tokens can access. These are important to the below sample app:

- Student & teacher tokens: strictly used for accessing their **own** identities
    - Ex: `/me` endpoint
- District tokens: used for accessing rostering and additional district data
    - Ex: `teacher/{id}/students` endpoint
- `Read:sis` scope:  enables access to additional district data through the use of the district token. This is only available to [Secure Sync](https://dev.clever.com/sync) customers. 

Again, these relationships stem from the fact that district admins decide what students & teachers can access. 

[More on Data Access](https://dev.clever.com/data-api/scopes)

## Building Birthday Reminder

Note: This app uses Python 2.7 & the Flask framework 

We are going to build an app for teachers to view student birthdays. This app will leverage Instant Login to handle user authentication, as well as the Clever API to retrieve student date of birth data. The app will display a table displaying birthdays in sorted order, current birthdays and the next birthday. For simplicity, if a student accesses the app they will simply be shown their own birthday. 

### Usage 

![Screenshot](https://s3-us-west-2.amazonaws.com/mauerbac-web-images/homepage1.png)

Give it a try!  [http://birthday-reminder-dev.elasticbeanstalk.com/](http://birthday-reminder-dev.elasticbeanstalk.com/)

- My demo district is “Demo Chappaqua Schools”. Use this district_id to find it: 5629bc024ed39d0100000a6c
- Login as a teacher or student
    - Ms. Waelchi, Grade 11 Chemistry Teacher
        - U: waelchi_grant, P: ahS9thueth
    - Julie D, Grade 9 Student
        - U: julied89 , P: dohquooY6cah

### Housekeeping

- Create a Clever [Developer Account](https://clever.com/developers/signup)
- Create a [Sandbox District](https://dev.clever.com/guides/creating-district-sandboxes)
- Save one or two student & teacher logins so you can test Instant Login. You can get these from the .csv files you uploaded or from the District Admin dashboard
- Save your `Client_id` & `Client_secret`, from your [application settings](https://apps.clever.com/partner/applications)  
- Save your [district_token](https://dev.clever.com/images/token-dashboard.jpg)
- If you want to replicate this app, simply replace the constants in application.py 

### Code walk-through 

The main components of this app are: 

1. Authenticating users via Instant Login 
2. Identifying student account types and handling appropriately 
3. Querying the Clever API to retrieve all of a teacher's students and corresponding dates of birth  
4. Sorting student birthdays by month and day 
5. Identifying if a current birthday exists and the next birthday
6. Displaying the data 

Upon a user’s successful completion of the OAuth process, we initiate a Session to store a user’s access_token. 

```python
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
```

In `process_birthdays`, we ensure there’s a valid session. Remember, this app is designed for teachers to view their students’ birthdays, so we need to distinguish between students and teachers. This is achieved by checking account type from the data returned by `get_basic_info()`, which is a helper function that uses access token to query the `/me` endpoint. This endpoint will return information about a user, such as: name, id, account type, dob, etc. If the user is a student, we simply inform them the app is intended for teachers and provide them with their own birthday using data from `/me`. 

To make API calls against Clever endpoints, use Python’s [requests](http://docs.python-requests.org/en/latest/) module, an HTTP library that makes it easy to call APIs. As an alternative, you could also use one of Clever’s [API libraries](https://dev.clever.com/support/libraries). 

To retrieve all of a teacher’s students, we use the `/teacher/{id}/students` endpoint, which returns a record per student containing their DOB. Remember, we must use the `district token` for this endpoint. It’s worth noting that we have hard coded a district token, so this app will only be compatible with this one district. For production apps, developers must manage the district tokens on their own. [More on district tokens](https://dev.clever.com/sync/district-tokens)

By default, this endpoint is capped to 100 records, so it’s important to be aware of when to use API Paging. In this app, however, we made the assumption that a teacher will not have more than 200 students and set the limit parameter to 200. 

```python
        # Call '/teachers/{teacher_id}/students' endpoint
        students_data = requests.get(
            CLEVER_API_BASE + API_VERSION + '/teachers/{0}/students?limit=200'.format(entity_id),
            headers={'Authorization': 'Bearer {0}'.format(DISTRICT_TOKEN)})

        if students_data.status_code >= 400:
            return redirect(url_for('index', error='There was an error retrieving student data.'))
        else:
            students_data = students_data.json()
```

We then iterate and save each record in the `students` dictionary where their DOB acts as the key and value is a list of students who have that birthday. This dictionary is then sorted by month and day. The datetime module is leveraged to convert Clever’s DOB "5/23/2004" into an object so that it’s sortable by Python. 

Lastly, check if there’s a birthday today, as well as check when the next birthday is. 

### Additional Resources:
- [API Explorer](https://clever.com/developers/docs/explorer#api_data) - A great tool to become more familiar with the  Clever API.
- Questions? Reach out via twitter [@mauerbac](https://twitter.com/mauerbac) 

