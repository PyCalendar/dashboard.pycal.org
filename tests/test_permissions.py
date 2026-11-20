def test_every_data_of_github_has_events_with_their_permissions():
    """The data follows GitHub by webhooks: the app subscribes to them and may receive them."""
    from django.apps import apps

    from pycal_dashboard.github.permissions import (
        DATA_EVENTS,
        EVENT_PERMISSIONS,
        EVENTS,
        REQUIRED,
    )
    from pycal_dashboard.privacy import MODELS

    of_github = {
        "Repository",
        "Issue",
        "GitHubUser",
        "Installation",
        "Label",
        "PullRequestState",
        "Review",
    }
    assert set(DATA_EVENTS) == of_github
    for model in of_github:
        assert f"pycal_dashboard.{model}" in MODELS and apps.get_model("pycal_dashboard", model)
    unsubscribed = {"installation", "installation_repositories"}  # come without a subscription
    for events in DATA_EVENTS.values():
        for event in events:
            assert event in EVENTS or event in unsubscribed, event
            if event in EVENTS:
                assert EVENT_PERMISSIONS[event] in REQUIRED, event
    assert set(EVENT_PERMISSIONS) == set(EVENTS)
