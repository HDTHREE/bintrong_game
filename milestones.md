# Milestones
Since I wrote the tasklisk I have decided to not host grok.

1. Self host llm - **19/11/2025**
2. Implement API user authenication and session - **21/11/2025**
3. Database for table above - **22/11/2025**
4. Implement API routes for file storage and retrieval. - **22/11/2025**
5. Database for table above - **22/11/2025**
6. Implement API routes to generate flash card questions to anki packages. - **22/11/2025**
7. Develop frontend to implement the user session from task 2. - **23/11/2025**
8. Develop frontend to complete the actions from tasks 4 and 6. - **23/11/2025**
9. Develop threejs game loop to live render multiple players. - **28/11/2025**
10. Compose or acquire player model. - **29/11/2025**
11. Develop basic player actions, move, jump, ect. - **30/11/2025**
12. Generate assets ad hoc to create first game. - **30/11/2025**
13. Script and program game loop so the game is playable. - **12/1/2026**
14. Implement API routes to generate game sessions. - **7/12/2025**
15. Develop frontend to create and join game sessions. - **7/12/2025**
16. Develop and integrate frontend to serve the game client embedded in the frontend. - **15/1/2026**
17. Integrate backend API to spawn game servers - **1/2/2026**
    - kubernetes(helm)
    - docker(dind)
18. Figure out production deployment and proxy. - **1/3/2026**

# Tables

### Timeline

```mermaid
gantt
  dateFormat DD/MM/YYYY
  title LiveTrivia - Milestones Timeline
  excludes weekends

  section Infrastructure
  Self host llm                :a1, 19/11/2025, 2d

  section API
  Implement API user authentication and session :a2, 21/11/2025, 3d
  Database for table above    :a3, 22/11/2025, 2d
  Implement API routes for file storage and retrieval :a4, 22/11/2025, 4d
  Database for file storage   :a5, 22/11/2025, 2d
  API to generate flashcard/anki packages :a6, 22/11/2025, 5d

  section Frontend
  Frontend: user session (task 2) :a7, 23/11/2025, 5d
  Frontend: file storage & flashcards (tasks 4 & 6) :a8, 23/11/2025, 7d
  Frontend: create/join game sessions :a15, 07/12/2025, 7d
  Frontend: embed game client    :a16, 15/01/2026, 10d

  section Game
  threejs game loop (multiplayer render) :a9, 28/11/2025, 7d
  Compose/acquire player model    :a10, 29/11/2025, 3d
  Basic player actions (move/jump/etc) :a11, 30/11/2025, 5d
  Generate assets ad hoc          :a12, 30/11/2025, 7d
  Script & program playable game loop :a13, 12/01/2026, 14d

  section Backend Ops
  Implement API routes to generate game sessions :a14, 07/12/2025, 5d
  Integrate backend API to spawn game servers (k8s / docker) :a17, 02/01/2026, 10d
  Production deployment & proxy  :a18, 03/01/2026, 7d

```

### Effort Matrix

| Number | Task | Effort | Assignee |
|-------:|------|:------:|:--------|
| 1 | Self host llm | High | Hayden |
| 2 | Implement API user authentication and session | Medium | Hayden |
| 3 | Database for table above | Medium | Hayden |
| 4 | Implement API routes for file storage and retrieval | Medium | Hayden |
| 5 | Database for file storage | Medium | Hayden |
| 6 | Implement API routes to generate flash card questions to anki packages | Medium | Hayden |
| 7 | Develop frontend to implement the user session from task 2 | Low | Hayden |
| 8 | Develop frontend to complete the actions from tasks 4 and 6 | Low | Hayden |
| 9 | Develop threejs game loop to live render multiple players | High | Hayden |
| 10 | Compose or acquire player model | Low | Hayden |
| 11 | Develop basic player actions (move, jump, etc.) | Medium | Hayden |
| 12 | Generate assets ad hoc to create first game | Medium | Hayden |
| 13 | Script and program game loop so the game is playable | High | Hayden |
| 14 | Implement API routes to generate game sessions | Medium | Hayden |
| 15 | Develop frontend to create and join game sessions | Low | Hayden |
| 16 | Develop and integrate frontend to serve the game client embedded | Medium | Hayden |
| 17 | Integrate backend API to spawn game servers (kubernetes / docker) | High | Hayden |
| 18 | Figure out production deployment and proxy | High | Hayden |
