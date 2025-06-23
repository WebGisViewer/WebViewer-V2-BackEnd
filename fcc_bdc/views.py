from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import connection
from django.contrib.gis.geos import Polygon

class FCCQueryViewSet(ViewSet):

    @action(detail=False, methods=['post'])
    
    def bounding_box_query(self, request):
        """
        Accepts: {
          "state": "VA",
          "bbox": [-79.5, 37.9, -78.7, 38.3]
        }
        """
        state = request.data.get("state")
        bbox = request.data.get("bbox")

        if not state or not bbox or len(bbox) != 4:
            return Response({"error": "Missing or invalid state/bbox"}, status=400)

        table = f"fcc_{state.lower()}"
        envelope = f"ST_MakeEnvelope({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}, 4326)"
        query = f"SELECT * FROM {table} WHERE geom && {envelope}"

        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response({"results": data})