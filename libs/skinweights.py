from scipy.spatial import cKDTree
from dcc.json import psonobject
from dcc.python import stringutils
from dcc.dataclasses.vector import Vector

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SkinWeights(psonobject.PSONObject):
    """
    Overload of `PSONObject` that interfaces with skin weight data.
    """

    # region Dunderscores
    __slots__ = ('_name', '_influences', '_maxInfluences', '_weights', '_points')

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance is created.

        :key name: str
        :key influences: List[str]
        :key maxInfluences: int
        :key vertexWeights: Dict[int, Dict[int, float]]
        :key controlPoints: List[Vector]
        :rtype: None
        """

        # Declare private variables
        #
        self._name = kwargs.get('name', '')
        self._influences = kwargs.get('influences', {})
        self._maxInfluences = kwargs.get('maxInfluences', 4)
        self._weights = kwargs.get('weights', {})
        self._points = kwargs.get('points', [])

        # Call parent method
        #
        super(SkinWeights, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def name(self):
        """
        Getter method that returns the name of the skin.

        :rtype: str
        """

        return self._name

    @name.setter
    def name(self, name):
        """
        Setter method that updates the name of the skin.

        :type name: str
        :rtype: None
        """

        self._name = name

    @property
    def influences(self):
        """
        Getter method that returns the influence objects.

        :rtype: Dict[int, str]
        """

        return self._influences

    @influences.setter
    def influences(self, influences):
        """
        Setter method that updates the influence objects.

        :type influences: Dict[int, str]
        :rtype: None
        """

        self._influences.clear()
        self._influences.update({stringutils.eval(influenceId): influenceName for (influenceId, influenceName) in influences.items()})

    @property
    def maxInfluences(self):
        """
        Getter method that returns the max number of influences per-vert.

        :rtype: int
        """

        return self._maxInfluences

    @maxInfluences.setter
    def maxInfluences(self, maxInfluences):
        """
        Setter method that updates the max number of influences per-vert.

        :type maxInfluences: int
        :rtype: None
        """

        self._maxInfluences = maxInfluences

    @property
    def weights(self):
        """
        Getter method that returns the skin weights.

        :rtype: Dict[int, Dict[int, float]]
        """

        return self._weights

    @weights.setter
    def weights(self, weights):
        """
        Setter method that updates the skin weight.

        :type weights: Dict[int, Dict[int, float]]
        :rtype: None
        """

        self._weights.clear()
        self._weights.update({stringutils.eval(vertexIndex): {stringutils.eval(influenceId): weight for (influenceId, weight) in vertexWeights.items()} for (vertexIndex, vertexWeights) in weights.items()})

    @property
    def points(self):
        """
        Getter method that returns the control points.

        :rtype: List[Vector]
        """

        return self._points

    @points.setter
    def points(self, points):
        """
        Setter method that updates the control points.

        :type points: List[Vector]
        :rtype: None
        """

        self._points.clear()
        self._points.extend(points)
    # endregion

    # region Methods
    def remapInfluences(self, skin):
        """
        Returns an influence map for the supplied skin.

        :type skin: fnskin.FnSkin
        :rtype: Dict[int, int]
        """

        influenceNames = {influenceName: influenceId for (influenceId, influenceName) in skin.influenceNames()}
        influenceMap = {influenceId: influenceNames.get(influenceName, influenceId) for (influenceId, influenceName) in self.influences.items()}

        return influenceMap

    def applyWeights(self, skin, influenceMap=None):
        """
        Applies the vertex weights to the supplied skin.

        :type skin: fnskin.FnSkin
        :type influenceMap: Dict[int, int]
        :rtype: None
        """

        # Check if an influence map was supplied
        #
        if influenceMap is None:

            influenceMap = self.remapInfluences(skin)

        # Remap and apply weights
        #
        vertexWeights = skin.remapVertexWeights(self.weights, influenceMap)
        skin.applyVertexWeights(vertexWeights)

    def applyClosestWeights(self, skin, influenceMap=None):
        """
        Applies the closest vertex weights to the supplied skin.

        :type skin: fnskin.FnSkin
        :type influenceMap: Dict[int, int]
        :rtype: None
        """

        # Check if an influence map was supplied
        #
        if influenceMap is None:

            influenceMap = self.remapInfluences(skin)

        # Initialize point tree
        #
        tree = cKDTree(self.points)
        distances, closestIndices = tree.query(skin.controlPoints())

        # Apply weights
        #
        vertexWeights = {vertexIndex + skin.arrayIndexType: self.weights[closestIndex + skin.arrayIndexType] for (vertexIndex, closestIndex) in enumerate(closestIndices)}
        vertexWeights = skin.remapVertexWeights(vertexWeights, influenceMap)

        skin.applyVertexWeights(vertexWeights)

    @classmethod
    def create(cls, skin):
        """
        Returns a new skin weights instance from the supplied skin.

        :type skin: fnskin.FnSkin
        :rtype: SkinWeights
        """

        return cls(
            name=skin.name(),
            influences=skin.influenceNames(),
            maxInfluences=skin.maxInfluences(),
            weights=skin.vertexWeights(),
            points=skin.controlPoints()
        )
    # endregion
