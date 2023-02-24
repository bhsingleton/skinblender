import json

from dcc.json import psonparser
from .skinweights import SkinWeights

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def exportWeights(filePath, skin):
    """
    Exports the skin weights from the supplied skin to the specified path.

    :type filePath: str
    :type skin: fnskin.FnSkin
    :rtype: None
    """

    skinWeights = SkinWeights.create(skin)

    with open(filePath, 'w') as jsonFile:

        log.info('Exporting pose to: %s' % filePath)
        json.dump(skinWeights, jsonFile, cls=psonparser.PSONEncoder, indent=4)


def importWeights(filePath):
    """
    Exports the skin weights from the specified path.

    :type filePath: str
    :rtype: SkinWeights
    """

    with open(filePath, 'r') as jsonFile:

        return json.load(jsonFile, cls=psonparser.PSONDecoder)
