from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import connection
from django.contrib.gis.geos import Polygon
from .serializers import BoundingBoxRequestSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class FCCQueryViewSet(ViewSet):


    @swagger_auto_schema(
        method='post',
        request_body=BoundingBoxRequestSerializer,
        operation_description="Returns FCC features filtered by state and bounding box",
        responses={200: openapi.Response(description="Filtered results")}
    )
    @action(detail=False, methods=['post'])
    @action(detail=False, methods=['post'])
    
    def bounding_box_query(self, request):
        """
        Accepts: {
          "state": "VA",
          "bbox": [-79.5, 37.9, -78.7, 38.3]
        }
        """
         
        serializer = BoundingBoxRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
       
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