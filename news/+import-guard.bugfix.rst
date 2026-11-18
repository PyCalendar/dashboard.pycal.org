Pages served at the same time cannot stop each other in a deadlock while they import the packages that the site loads only when needed: every lazy import goes through an import guard.
