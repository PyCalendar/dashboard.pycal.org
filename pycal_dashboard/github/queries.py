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

# a person on GitHub, as the site keeps them (GitHubUser): users and bots have a databaseId
ACTOR = "__typename login avatarUrl ... on User { databaseId } ... on Bot { databaseId }"

# ``REVIEWS`` reads all pull requests of a repository, the last changed first, with their
# reviews and who closed them: ReviewsData stops at those it read before.
REVIEWS = """
query ($owner: String!, $name: String!, $after: String, $first: Int!) {
  rateLimit { cost remaining resetAt }
  repository(owner: $owner, name: $name) {
    pullRequests(first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        updatedAt
        reviews(first: 100) { nodes { databaseId state submittedAt author { ACTOR } } }
        timelineItems(itemTypes: [CLOSED_EVENT], last: 1) {
          nodes { ... on ClosedEvent { actor { ACTOR } } }
        }
      }
    }
  }
}
""".replace("ACTOR", ACTOR)
