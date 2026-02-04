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
- 6.3 Ensures that a session refresh token is expired cannot be refreshed.
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

### 12.1 API-Generate 1
- 12.2 Test Anki generation from YouTube URL.
- 12.3 Ensures that a YouTube transcript is fetched, stored, and Anki cards are generated and saved to S3.
- 12.4 Inputs: YouTube video URL, cloze flag, authenticated user session.
- 12.5 Outputs: FileDataResponse with generated file metadata, transcript and generated file stored in S3.
- 12.6 Normal
- 12.7 Whitebox
- 12.8 Functional
- 12.9 Integration

### 13.1 API-Generate 2
- 13.2 Test Anki generation from existing file.
- 13.3 Ensures that text is extracted from an uploaded file (PDF, DOCX, TXT) and Anki cards are generated and saved to S3.
- 13.4 Inputs: File ID of existing file, cloze flag, authenticated user session.
- 13.5 Outputs: FileDataResponse with generated file metadata, generated file stored in S3.
- 13.6 Normal
- 13.7 Whitebox
- 13.8 Functional
- 13.9 Integration

### 14.1 API-Generate 3
- 14.2 Test cloze-deletion card generation.
- 14.3 Ensures that when cloze flag is true, the cloze prompt is used and output file is named accordingly.
- 14.4 Inputs: YouTube video URL or file ID, cloze=true, authenticated user session.
- 14.5 Outputs: FileDataResponse with cloze-type filename, generated content uses cloze format.
- 14.6 Normal
- 14.7 Blackbox
- 14.8 Functional
- 14.9 Unit

### 15.1 API-Generate 4
- 15.2 Test cached YouTube transcript retrieval.
- 15.3 Ensures that a previously fetched transcript is retrieved from S3 instead of re-fetching from YouTube API.
- 15.4 Inputs: YouTube video URL for previously processed video, authenticated user session.
- 15.5 Outputs: FileDataResponse, no new transcript file created, existing transcript reused.
- 15.6 Normal
- 15.7 Whitebox
- 15.8 Performance
- 15.9 Unit

### 16.1 API-Generate 5
- 16.2 Test generation with invalid file ID.
- 16.3 Ensures that an error is returned when the specified file ID does not exist in the database.
- 16.4 Inputs: Non-existent file ID, authenticated user session.
- 16.5 Outputs: Error response indicating the requested file does not exist (404).
- 16.6 Abnormal
- 16.7 Blackbox
- 16.8 Functional
- 16.9 Unit

### 17.1 API-Generate 6
- 17.2 Test generation with unauthorized file access.
- 17.3 Ensures that an error is returned when a user attempts to generate from a file they do not own.
- 17.4 Inputs: File ID belonging to different user, authenticated user session.
- 17.5 Outputs: Error response indicating the user provided a file they do not own.
- 17.6 Abnormal
- 17.7 Whitebox
- 17.8 Functional
- 17.9 Unit

### 18.1 API-Generate 7
- 18.2 Test generation with unsupported file type.
- 18.3 Ensures that an error is returned when the file extension is not supported for text extraction.
- 18.4 Inputs: File ID of unsupported file type (.anki or other non-text formats), authenticated user session.
- 18.5 Outputs: Error response indicating the provided file type cannot be used for generation.
- 18.6 Abnormal
- 18.7 Blackbox
- 18.8 Functional
- 18.9 Unit

### 19.1 API-Generate 8
- 19.2 Test generation API failure handling.
- 19.3 Ensures that an error is returned when the external generation API (SGLang) is unavailable or returns an error.
- 19.4 Inputs: Valid YouTube URL or file ID, generation API returns error status.
- 19.5 Outputs: Error response indicating the sglang service failed.
- 19.6 Abnormal
- 19.7 Whitebox
- 19.8 Functional/Performance
- 19.9 Integration/Unit (there be 1 or more states where this occurs, healthcheck & token-based fault tolerance)

### 20.1 API-Game 1
- 20.2 Test game creation.
- 20.3 Ensures that a new game is created with the authenticated user's session as host, status set to STARTING, and a unique game code generated.
- 20.4 Inputs: Valid access token, state of database before query.
- 20.5 Outputs: GameResponse with game ID, host_session_id, game_code, status=STARTING, created_at timestamp; database entry created.
- 20.6 Normal
- 20.7 Whitebox
- 20.8 Functional
- 20.9 Unit

### 21.1 API-Game 2
- 21.2 Test game creation with invalid token.
- 21.3 Ensures that game creation fails when an invalid or expired access token is provided.
- 21.4 Inputs: Invalid/expired access token.
- 21.5 Outputs: Unauthorized error response indicating the access token is invalid or expired.
- 21.6 Abnormal
- 21.7 Blackbox
- 21.8 Functional
- 21.9 Unit

### 22.1 API-Game 3
- 22.2 Test joining a game.
- 22.3 Ensures that a player can join an existing game in STARTING status using a valid game code, creating a GamePlayer entry.
- 22.4 Inputs: Valid game code, valid access token, state of database before query.
- 22.5 Outputs: GamePlayerResponse with player ID, game_id, session_id, score=0, joined_at timestamp, is_active=true.
- 22.6 Normal
- 22.7 Whitebox
- 22.8 Functional
- 22.9 Unit

### 23.1 API-Game 4
- 23.2 Test joining a game with invalid game code.
- 23.3 Ensures that joining fails when the provided game code does not exist.
- 23.4 Inputs: Non-existent game code, valid access token.
- 23.5 Outputs: Not found error response indicating the game does not exist.
- 23.6 Abnormal
- 23.7 Blackbox
- 23.8 Functional
- 23.9 Unit

### 24.1 API-Game 5
- 24.2 Test joining a game not in STARTING status.
- 24.3 Ensures that a player cannot join a game that has already started (RUNNING) or ended (ENDED).
- 24.4 Inputs: Valid game code for game with status != STARTING, valid access token.
- 24.5 Outputs: Bad request error response indicating the game is not in a joinable state.
- 24.6 Abnormal
- 24.7 Whitebox
- 24.8 Functional
- 24.9 Unit

### 25.1 API-Game 6
- 25.2 Test rejoining a game.
- 25.3 Ensures that if a player already exists in the game and is active, they receive their existing GamePlayer entry instead of creating a duplicate.
- 25.4 Inputs: Valid game code, valid access token for user already in game, state of database before query.
- 25.5 Outputs: Existing GamePlayerResponse returned; no duplicate entry created.
- 25.6 Boundary
- 25.7 Whitebox
- 25.8 Functional
- 25.9 Unit

# Test Case Matrix
| Test ID | Test Name | Case Type | Box Type | Test Type | Level |
|---------|-----------|-----------|----------|-----------|-------|
| 1.1 | API-Auth 1 | Normal | Whitebox | Functional | Unit |
| 2.1 | API-Auth 2 | Normal | Whitebox | Functional | Unit |
| 3.1 | API-Auth 3 | Normal | Whitebox | Functional | Unit |
| 4.1 | API-Auth 4 | Normal | Whitebox | Functional | Unit |
| 5.1 | API-Auth 5 | Normal | Whitebox | Functional | Unit |
| 6.1 | API-Auth 6 | Abnormal | Whitebox | Functional | Unit |
| 7.1 | API-Auth 7 | Normal | Whitebox | Functional | Unit |
| 8.1 | API-Files 1 | Normal | Whitebox | Functional | Unit |
| 9.1 | API-Files 2 | Normal | Blackbox | Functional | Unit |
| 10.1 | API-Files 3 | Abnormal | Blackbox | Functional | Unit |
| 11.1 | API-Files 4 | Normal | Blackbox | Functional | Unit |
| 12.1 | API-Generate 1 | Normal | Whitebox | Functional | Integration |
| 13.1 | API-Generate 2 | Normal | Whitebox | Functional | Integration |
| 14.1 | API-Generate 3 | Normal | Blackbox | Functional | Unit |
| 15.1 | API-Generate 4 | Normal | Whitebox | Performance | Unit |
| 16.1 | API-Generate 5 | Abnormal | Blackbox | Functional | Unit |
| 17.1 | API-Generate 6 | Abnormal | Whitebox | Functional | Unit |
| 18.1 | API-Generate 7 | Abnormal | Blackbox | Functional | Unit |
| 19.1 | API-Generate 8 | Abnormal | Whitebox | Functional/Performance | Integration/Unit |
| 20.1 | API-Game 1 | Normal | Whitebox | Functional | Unit |
| 21.1 | API-Game 2 | Abnormal | Blackbox | Functional | Unit |
| 22.1 | API-Game 3 | Normal | Whitebox | Functional | Unit |
| 23.1 | API-Game 4 | Abnormal | Blackbox | Functional | Unit |
| 24.1 | API-Game 5 | Abnormal | Whitebox | Functional | Unit |
| 25.1 | API-Game 6 | Boundary | Whitebox | Functional | Unit |