
"""Open a URL in the user's default browser.

The URL is opened in a background thread.

History:
2004-10-05 ROwen
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
"""
__all__ = ["browseURL"]

import threading
import six.moves.urllib.parse as parse
import webbrowser

class _BrowseURLThread(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url
        self.setDaemon(True)

    def run(self):
        url = self.url
        try:
            webbrowser.open(url)
            return
        except Exception as e:
            pass

        # failed! if this is a file URL with an anchor,
        # try again without the anchor
        urlTuple = parse.urlparse(url)
        if urlTuple[0] == "file" and urlTuple[-1] != '':
            urlTuple = urlTuple[0:-1] + ('',)
            url = parse.urlunparse(urlTuple)
            if not url:
                return
            try:
                webbrowser.open(url)
                return
            except Exception as e:
                pass

        # failed!
        print("could not open URL %r: %s %r" % (url, e, e))

def browseURL(url):
    newThread = _BrowseURLThread(url)
    newThread.start()
