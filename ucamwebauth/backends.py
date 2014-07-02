import logging
import traceback
from django.contrib.auth.models import User, UserManager
from ucamwebauth import (MalformedResponseError, InvalidResponseError, RavenResponse,
                         PublicKeyNotFoundError, UserNotAuthorised)
from ucamwebauth.utils import setting

logger = logging.getLogger(__name__)

class RavenAuthBackend(object):
    """An authentication backend for django that uses Raven.  To use, add
    'ucamwebauth.backends.RavenAuthBackend' to AUTHENTICATION_BACKENDS
    in your django settings.py."""

    def authenticate(self, response_str=None):
        """Checks a response from the Raven server and sees if it is valid.  If
        it is, returns the User with the same username as the Raven username.
        @return User object, or None if authentication failed"""

        if response_str is None:
            return None

        response = RavenResponse(response_str)

        # Check that everything is correct, and return
        try:
            response.validate()
        except MalformedResponseError:
            logger.error("Got a malformed response from the Raven server")
            return None
        except InvalidResponseError:
            logger.error("Got an invalid response from the Raven server")
            return None
        except PublicKeyNotFoundError:
            logger.error("Cannot find a public key for the server's response")
            return None
        except Exception as e:
            logger.error(e)
            return None

        if (setting('UCAMWEBAUTH_NOT_CURRENT', default=False) is False) and ('current' not in response.ptags):
            raise UserNotAuthorised

        username = response.principal
 
        if username is None:
            return None

        user = self.get_user_by_name(username)
        return user

    def get_user_by_name(self, username):
        """Gets a user with the specified username from the DB."""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.debug("Successfully authenticated as %s in Raven, but that user does not exist in Django" % username)

            if setting('UCAMWEBAUTH_CREATE_USER', default=False) is True:
                logger.debug("Creating user for %s" % username)
                return User.objects.create_user(username=username)
            else:
                logger.debug("User %s not created" % username)

            return None
        else:
            logger.debug("%s successfully authenticated via Raven" % username)
            return user

    def get_user(self, user_id):
        """Gets a user with the specified user ID from the DB.  For some
        reason, this is required by django for an auth backend."""
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.debug("No such user: %s" % user_id)
            return None
        else:
            return user