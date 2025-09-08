from scipy.spatial import cKDTree
from dcc import fnskin
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
        :key vertexWeights: List[Dict[int, float]]
        :key controlPoints: List[Vector]
        :rtype: None
        """

        # Call parent method
        #
        super(SkinWeights, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._name = ''
        self._influences = {}
        self._maxInfluences = 4
        self._weights = []
        self._points = []
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

        :rtype: List[Dict[int, float]]
        """

        return self._weights

    @weights.setter
    def weights(self, weights):
        """
        Setter method that updates the skin weights.

        :type weights: List[Dict[int, float]]
        :rtype: None
        """

        self._weights.clear()
        self._weights.extend([{stringutils.eval(influenceId): influenceWeight for (influenceId, influenceWeight) in influenceWeights.items()} for influenceWeights in weights])

    @property
    def points(self):
        """
        Getter method that returns the vertex points.

        :rtype: List[Vector]
        """

        return self._points

    @points.setter
    def points(self, points):
        """
        Setter method that updates the vertex points.

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

        influenceNames = {influenceName: influenceId for (influenceId, influenceName) in skin.influenceNames().items()}
        influenceMap = {influenceId: influenceNames.get(influenceName, influenceId) for (influenceId, influenceName) in self.influences.items()}

        return influenceMap

    def applyWeights(self, skin, influenceMap=None):
        """
        Applies the skin weights to the supplied skin.

        :type skin: fnskin.FnSkin
        :type influenceMap: Dict[int, int]
        :rtype: None
        """

        # Check if an influence map was supplied
        #
        if influenceMap is None:

            influenceMap = self.remapInfluences(skin)

        # Check if vertex counts are identical
        #
        pointCount = len(self.points)
        incomingCount = skin.numControlPoints()

        if pointCount != incomingCount:

            raise TypeError(f'applyWeights() expects {pointCount} vertices ({incomingCount} given)!')

        # Remap and apply weights
        #
        vertexWeights = {vertexIndex: weights for (vertexIndex, weights) in enumerate(self.weights, start=skin.arrayIndexType)}
        remappedWeights = skin.remapVertexWeights(vertexWeights, influenceMap)

        skin.applyVertexWeights(remappedWeights)

    def applyClosestWeights(self, skin, influenceMap=None):
        """
        Applies the closest skin weights to the supplied skin.

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
        vertexWeights = {vertexIndex + skin.arrayIndexType: self.weights[closestIndex] for (vertexIndex, closestIndex) in enumerate(closestIndices)}
        remappedWeights = skin.remapVertexWeights(vertexWeights, influenceMap)

        skin.applyVertexWeights(remappedWeights)

    def applySkin(self, mesh):
        """
        Applies the closest skin weights to the supplied skin.

        :type mesh: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: None
        """

        skin = fnskin.FnSkin.create(mesh)
        skin.setMaxInfluences(self.maxInfluences)
        skin.addInfluence(*list(self.influences.values()))

        self.applyClosestWeights(skin)

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
            weights=list(skin.vertexWeights().values()),
            points=skin.controlPoints()
        )
    # endregion
