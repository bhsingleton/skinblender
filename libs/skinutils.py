import json

from dcc.json import psonparser
from .skinweights import SkinWeights

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def cacheSkin(skin):
    """
    Returns a skin cache using the supplied skin.

    :type skin: fnskin.FnSkin
    :rtype: Skin
    """

    return SkinWeights.create(skin)


def exportSkin(filePath, skin):
    """
    Exports the supplied skin to the specified path.

    :type filePath: str
    :type skin: fnskin.FnSkin
    :rtype: None
    """

    skinWeights = cacheSkin(skin)

    with open(filePath, 'w') as jsonFile:

        log.info('Exporting skin weights to: %s' % filePath)
        json.dump(skinWeights, jsonFile, cls=psonparser.PSONEncoder, indent=4)


def importSkin(filePath):
    """
    Imports a skin from the specified path.

    :type filePath: str
    :rtype: SkinWeights
    """

    with open(filePath, 'r') as jsonFile:

        return json.load(jsonFile, cls=psonparser.PSONDecoder)
