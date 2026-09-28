# Architecture Decision Records

Five entries, added on the day each decision is made.

## [1]. Backend framework
Date: 2026-09-28
Status: Decided
Context: Edgebook is one Python process with SQLite and JSON routes. It needs a web framework, and the database connection cannot be shared across requests.
Decision: I chose FastAPI. It checks request data and serves /docs on its own, and Depends fits get_db: one SQLite connection per request, opened and closed for me.
Alternatives considered: Django. It pushes an ORM, and this project uses plain sqlite3 on purpose. It is also a lot of framework for one small app.
Consequences: Routes can use Depends(get_db), and /docs is free. The cost is that I have to be able to explain a FastAPI dependency, and routes stay plain def rather than async.

<!--
Format (copy for each entry):

## [N]. <Title>
Date: YYYY-MM-DD
Status: Decided
Context: 1-3 sentences, what forced this decision
Decision: 1-2 sentences, what you chose
Alternatives considered: at least one real alternative, and why you rejected it
Consequences: 1-2 sentences, what this costs or enables later

Planned entries:
1. Backend framework (Mon Sep 28)
2. Intel / Book domain split (Tue Sep 29)
3. SQLite schema decision (Wed Sep 30)
4. Testing approach (Fri Oct 2)
5. Deliberately not built (Sat Oct 3)
-->
