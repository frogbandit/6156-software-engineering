from google.appengine.ext import vendor
from google.appengine.api import namespace_manager

# Add any libraries installed in the "lib" folder.
vendor.add('lib')

# Called only if the current namespace is not set.
def namespace_manager_default_namespace_for_request():
    # The returned string will be used as the Google Apps domain.
    return namespace_manager.google_apps_namespace()