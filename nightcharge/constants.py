from logging import getLogger

from yarl import URL

_LOGGER = getLogger("nightcharge")

DISCOVERY_API = URL("https://discovery.chargepoint.com/discovery/v3/globalconfig")
