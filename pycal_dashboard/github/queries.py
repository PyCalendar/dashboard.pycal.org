"""The queries of GraphQL that the site asks GitHub.

``PULL_REQUESTS`` reads the open pull requests of a repository, ``first`` a page; ``FIELDS`` is
replaced by the fragments of the data specs of the conditions (``DataSpec.graphql``), so that
one query reads all they need: merging, auto-merge and the checks of the last commit.
"""

PULL_REQUESTS = """
query ($owner: String!, $name: String!, $after: String, $first: Int!) {
  rateLimit { cost remaining resetAt }
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: $first, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { number FIELDS }
    }
  }
}
"""
