README.md

#Supporting Clever Instant Login 
By:Matt Auerbach 

##Background

Clever’s Single Sign-on (SSO) solution, Instant Login, alleviates many pain-points with password management for students and teachers. Using Instant Login, users can create one identity within Clever and access all of their applications in the classroom. School districts share data from their Student Information Systems (SIS) with Clever. 

By integrating with Clever, developers can securely and easily access district data via an API. This allows developers to spend more time building their own product, rather than worrying about SIS integrations. 

In this post, we’ll discuss the different components of Instant Login and provide a walk-through of a working example, Birthday Reminder. By the end of this demo, developers should have the tools to start implementing SSO in web applications and access district data with Clever.

## How Does Instant Login Work?

Applications use Instant Login to verify a user’s identity, authenticate users, and make API calls on a user’s behalf with their access_token. Here’s a typical flow that is initiated when a user requests to Login with Clever:

![Diagram](https://s3-us-west-2.amazonaws.com/mauerbac-web-images/sso-pilot-oauth2-flow.png)

[Additonal Info](https://dev.clever.com/instant-login/bearer-tokens)

## Entity Types 

Before getting started, it’s important to understand Clever’s entities -- let’s start with developer and district. Application developer accounts are used to create and edit applications settings, as well as view the district data from approved districts. District admins can control what applications teachers and students have available, but most importantly, they control what data is shared within these applications. District admins can also control what district data Clever has access to. It’s important to note that district admins are viewed as a central authority (not students and teachers). This means only district admins can control what apps are available and the scope of their data access. 

Students and Teachers are also entities in the Clever ecosystem and should be thought of as end users -- they will have their own credentials and will be consumers of your application. 


## Tokens and Scope
