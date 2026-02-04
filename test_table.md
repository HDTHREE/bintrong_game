# Test Strategies
Multiple strategies are employed in order to ensure the correctness of the application state and a quality user experience. The game has 3 main
components the backend, frontend and game server.
The frontend and backend each implement a python framework so pytest will be used.
Each provides a respective testing library that can be used in order to test the application.
A unit test design pattern can be used here in order to perform blackbox testing to test respective endpoints.
This can be done by using polar or pandas to quickly mock database state snapshots to set the state of the database.
Since dash (frontend framework) uses exclusively callbacks the state of the application is able to be mocked.

Additionally, the game client will need to be tested to ensure the correctness and repeatability (i.e. can be snapshotted) of the game state.
This will require the integration of the entire game environment to test features that span the entire application.

# Test Cases

### 1.1 API-Auth 1
- 1.2 Test user creation.
- 1.3 Ensures that a both a user account entry and session (access token) entry are created.
- 1.4 Inputs: State of database before query.
- 1.5 Outputs: State of database after query & response.
- 1.6 Normal
- 1.7 Whitebox
- 1.8 Functional
- 1.9 Unit

### 2.1 API-Auth 2
- 2.2 Test user login.
- 2.3 Ensures that a session (access token) entry is created.
- 2.4 Inputs: State of database before query.
- 2.5 Outputs: State of database after query & response.
- 2.6 Normal
- 2.7 Whitebox
- 2.8 Functional
- 2.9 Unit

### 3.1 API-Auth 3
- 3.2 Test session refresh.
- 3.3 Ensures session (new access token) is expired and a new entry created (original refresh token).
- 3.4 Inputs: State of database before query.
- 3.5 Outputs: State of database after query & response.
- 3.6 Normal
- 3.7 Whitebox
- 3.8 Functional
- 3.9 Unit

### 4.1 API-Auth 4
- 4.2 Test user log off.
- 4.3 Ensures that a session (access token) entry is marked as innactive.
- 4.4 Inputs: State of database before query.
- 4.5 Outputs: State of database after  query & response.
- 4.6 Normal
- 4.7 Whitebox
- 4.8 Functional
- 4.9 Unit

### 5.1 API-Auth 5
- 5.2 Test session deletion.
- 5.3 Ensures that a session (access token) entry is delete.
- 5.4 Inputs: State of database before query.
- 5.5 Outputs: State of database after query & response.
- 5.6 Normal
- 5.7 Whitebox
- 5.8 Functional
- 5.9 Unit

### 6.1 API-Auth 6
- 6.2 Test session refresh (failure).
- 6.3 Ensures that a session whose refresh token is expired cannot be refreshed.
- 6.4 Inputs: State of database before query.
- 6.5 Outputs: State of database after query & response.
- 6.6 Abnormal
- 6.7 Whitebox
- 6.8 Functional
- 6.9 Unit

### 7.1 API-Auth 7
- 7.2 Test session for guest.
- 7.3 Ensures that a session is created with user_id as `None`.
- 7.4 Inputs: State of database before query.
- 7.5 Outputs: State of database after query & response.
- 7.6 Normal
- 7.7 Whitebox
- 7.8 Functional
- 7.9 Unit

### 8.1 API-Files 1
- 8.2 Tests file upload.
- 8.3 Ensures that a file is uploaded and a database entry is created and returned.
- 8.4 Inputs: State of database before query.
- 8.5 Outputs: State of database after query & response.
- 8.6 Normal
- 8.7 Whitebox
- 8.8 Functional
- 8.9 Unit

### 9.1 API-Files 2
- 9.2 Tests file download.
- 9.3 Ensures a file can be downloaded after it is uploaded. Uploads a file, then downloads that file and performs a comaparison.
- 9.4 Inputs: File bytes.
- 9.5 Outputs: File bytes.
- 9.6 Normal
- 9.7 Blackbox
- 9.8 Functional
- 9.9 Unit

### 10.1 API-Files 3
- 10.2 Tests file deletion.
- 10.3 Ensures a file cannot be downloaded after the delete endpoint is invoked.
- 10.4 Inputs: A file file object.
- 10.5 Outputs: Both response objects.
- 10.6 Abnormal
- 10.7 Blackbox
- 10.8 Functional
- 10.9 Unit

### 11.1 API-Files 4
- 11.2 Tests file options endpoint.
- 11.3 Ensures multiple files are returned after uploading it.
- 11.4 Inputs: A file file object.
- 11.5 Outputs: Both response objects.
- 11.6 Normal
- 11.7 Blackbox
- 11.8 Functional
- 11.9 Unit
