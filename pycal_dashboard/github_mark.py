"""The mark of GitHub, from Primer Octicons (``mark-github``, 16 px), under the MIT license.

https://github.com/primer/octicons; the license is in ``LICENSES/MIT.txt`` and REUSE.toml.
"""

# the path of the SVG of the mark, in a box of 16 by 16
PATH = (
    "M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 "
    "0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 "
    "0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27"
    "-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 "
    "1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66"
    "-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 "
    "0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"
)

# the hosts of GitHub, whose links show the mark: people see that they leave the site
GITHUB_HOSTS = {"github.com", "www.github.com", "gist.github.com", "docs.github.com"}


def svg() -> str:
    """The mark of GitHub as inline SVG, in the color of the text.

    Returns:
        The HTML, hidden from screen readers: the link has the label.
    """
    return (
        '<svg class="icon github-mark" viewBox="0 0 16 16" width="16" height="16" '
        f'aria-hidden="true" focusable="false"><path fill="currentColor" d="{PATH}"/></svg>'
    )


def leads_to_github(url: str) -> bool:
    """Whether an address leads to GitHub, where a link shows the mark of GitHub.

    Parameters:
        url: The address, such as ``https://github.com/PyCalendar``.

    Returns:
        True for the hosts of GitHub, also below ``github.com``.

    Examples:
        >>> leads_to_github("https://github.com/PyCalendar"), leads_to_github("/projects/")
        (True, False)
        >>> leads_to_github("https://docs.github.com/x"), leads_to_github("https://github.com.evil")
        (True, False)
    """
    if "//" not in url:
        return False
    host = url.split("//", 1)[1].split("/", 1)[0].split("?", 1)[0].lower()
    return host in GITHUB_HOSTS or host.endswith(".github.com")
